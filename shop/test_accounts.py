import time, uuid
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch, Mock
from django.contrib.auth.models import User
from django.test import TestCase, override_settings, Client
from django.utils import timezone
from .models import UserProfile, PhoneChallenge, Product, Category, Order
from .verification import new_captcha,send_phone_code,validate_phone
from .tracking import tracking_for

@override_settings(DEBUG=True,SMS_BACKEND='demo')
class AccountFeaturesTests(TestCase):
    def setUp(self):
        self.user=User.objects.create_user('profile-owner','owner@example.com','Current-password-2026!')
    def captcha(self,client=None):
        client=client or self.client
        session=client.session;code=new_captcha(session);session.save();return code
    def registration(self,**extra):
        data={'username':'new-reader','email':'reader@example.com','password1':'Strong-fruit-2026!','password2':'Strong-fruit-2026!','captcha':self.captcha()};data.update(extra);return data
    def test_registration_requires_captcha_and_rejects_replay(self):
        data=self.registration(captcha='wrong')
        self.assertEqual(self.client.post('/accounts/register/',data).status_code,200)
        self.assertFalse(User.objects.filter(username='new-reader').exists())
        data=self.registration();self.assertEqual(self.client.post('/accounts/register/',data).status_code,302)
        self.assertFalse(self.client.session.get('captcha'))
    def test_expired_captcha_rejected(self):
        data=self.registration();session=self.client.session;row=session['captcha'];row['expires']=time.time()-1;session['captcha']=row;session.save()
        response=self.client.post('/accounts/register/',data);self.assertIn('captcha',response.context['form'].errors)
    def test_optional_phone_registration_without_binding(self):
        self.client.post('/accounts/register/',self.registration())
        profile=UserProfile.objects.get(user__username='new-reader');self.assertIsNone(profile.phone);self.assertFalse(profile.phone_verified)
    def test_demo_phone_binding_is_never_verified(self):
        captcha=self.captcha()
        result=self.client.post('/accounts/phone-code/',{'phone':'13800138001','captcha':captcha}).json()
        self.assertIn('demo_code',result)
        data=self.registration(phone='13800138001',sms_code=result['demo_code'])
        self.assertEqual(self.client.post('/accounts/register/',data).status_code,302)
        profile=UserProfile.objects.get(user__username='new-reader');self.assertEqual(profile.phone,'+8613800138001');self.assertTrue(profile.phone_demo);self.assertFalse(profile.phone_verified)
        row=PhoneChallenge.objects.get(phone=profile.phone);self.assertTrue(row.consumed);self.assertNotEqual(row.code_hash,result['demo_code'])
    def test_code_wrong_attempts_persist_and_lock(self):
        session=self.client.session;code=send_phone_code(session,'+8613800138002','127.0.0.9');session.save()
        for _ in range(5):
            with self.assertRaises(ValueError):validate_phone(session,'+8613800138002','bad')
        self.assertEqual(PhoneChallenge.objects.get(phone='+8613800138002').attempts,5)
        with self.assertRaises(ValueError):validate_phone(session,'+8613800138002',code)
    def test_code_is_scoped_to_session_and_expiry(self):
        session=self.client.session;code=send_phone_code(session,'+8613800138003','127.0.0.8');session.save()
        with self.assertRaises(ValueError):validate_phone(Client().session,'+8613800138003',code)
        PhoneChallenge.objects.update(expires_at=timezone.now()-timedelta(seconds=1))
        with self.assertRaises(ValueError):validate_phone(session,'+8613800138003',code)
    def test_sms_cooldown_and_captcha_guard(self):
        self.assertEqual(self.client.post('/accounts/phone-code/',{'phone':'13800138004'}).status_code,400)
        session=self.client.session;send_phone_code(session,'+8613800138004','127.0.0.7')
        with self.assertRaises(ValueError):send_phone_code(session,'+8613800138004','127.0.0.7')
    @override_settings(DEBUG=False,SMS_BACKEND='demo')
    def test_production_never_exposes_demo_code(self):
        response=self.client.post('/accounts/phone-code/',{'phone':'13800138005','captcha':self.captcha()})
        self.assertEqual(response.status_code,400);self.assertNotIn('demo_code',response.json())
    def test_profile_ownership_password_and_defaults(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.post('/accounts/profile/',{'display_name':'水果读者','email':'new@example.com','default_recipient':'收货人','default_address':'原始简体地址'}).status_code,302)
        profile=UserProfile.objects.get(user=self.user);self.assertEqual(profile.default_address,'原始简体地址')
        response=self.client.post('/accounts/profile/',{'email':'new@example.com','phone':'13800138006','current_password':'wrong'})
        self.assertIn('current_password',response.context['form'].errors);profile.refresh_from_db();self.assertIsNone(profile.phone)
        self.assertEqual(Client().get('/accounts/profile/').status_code,302)
    def test_language_cookie_search_and_user_input_preserved(self):
        category=Category.objects.create(name='热带果实');Product.objects.create(category=category,name='山野芭乐 · 1kg',origin='海南 · 河谷果园',fruit_key='guava',price='29.90',stock=1,season_months=[timezone.localdate().month])
        response=self.client.post('/i18n/setlang/',{'language':'en','next':'/?section=all'})
        self.assertEqual(response.cookies['django_language'].value,'en')
        self.assertContains(self.client.get('/?q=guava'),'Wild guava')
        self.assertContains(self.client.get('/?q=river-valley'),'Wild guava')
        self.client.force_login(self.user)
        UserProfile.objects.create(user=self.user,display_name='保留简体原文')
        self.assertContains(self.client.get('/accounts/profile/'),'保留简体原文')
        self.client.post('/i18n/setlang/',{'language':'zh-hant','next':'/'})
        self.assertContains(self.client.get('/'),'購物車');self.assertContains(self.client.get('/'),'lang="zh-HK"')
        response=self.client.post('/i18n/setlang/',{'language':'en','next':'https://evil.example/'})
        self.assertNotIn('evil.example',response.url)
    def order(self,paid=True):
        return Order.objects.create(user=self.user,checkout_token=uuid.uuid4(),recipient='测试收件人',email='test@example.com',address='测试地址',total=Decimal('10'),status='paid' if paid else 'pending',paid_at=timezone.now() if paid else None)
    def test_tracking_first_day_transit_and_arrival(self):
        order=self.order();start=order.paid_at
        self.assertEqual(tracking_for(order,start)['latest'],'商家已发货')
        self.assertEqual(tracking_for(order,start+timedelta(hours=2))['latest'],'快递已揽收')
        self.assertEqual(tracking_for(order,start+timedelta(days=2))['latest'],'干线运输中')
        self.assertTrue(tracking_for(order,start+timedelta(days=3))['arrived'])
        order.refresh_from_db();self.assertEqual(order.status,'paid');self.assertIsNone(order.shipped_at)
    def test_tracking_is_private_and_unpaid_has_no_events(self):
        order=self.order();self.client.force_login(self.user)
        self.assertContains(self.client.get(f'/orders/{order.pk}/tracking/'),'SIM')
        self.client.force_login(User.objects.create_user('outsider'))
        self.assertEqual(self.client.get(f'/orders/{order.pk}/tracking/').status_code,404)
        self.assertIsNone(tracking_for(self.order(False)))

    @override_settings(DEBUG=False,SMS_BACKEND='aliyun',ALIYUN_SMS_ACCESS_KEY_ID='test-only',ALIYUN_SMS_ACCESS_KEY_SECRET='test-only',ALIYUN_SMS_SIGN_NAME='test',ALIYUN_SMS_TEMPLATE_CODE='SMS_TEST')
    def test_provider_adapter_never_returns_real_code(self):
        import sys,types,json
        client_module=types.ModuleType('alibabacloud_dysmsapi20170525.client')
        model_module=types.ModuleType('alibabacloud_dysmsapi20170525.models')
        config_module=types.ModuleType('alibabacloud_tea_openapi.models')
        client_module.Client=Mock();client_module.Client.return_value.send_sms.return_value.body.code='OK'
        model_module.SendSmsRequest=lambda **kwargs:types.SimpleNamespace(**kwargs)
        config_module.Config=lambda **kwargs:types.SimpleNamespace(**kwargs)
        modules={'alibabacloud_dysmsapi20170525.client':client_module,'alibabacloud_dysmsapi20170525.models':model_module,'alibabacloud_tea_openapi.models':config_module}
        session=self.client.session
        with patch.dict(sys.modules,modules):
            self.assertIsNone(send_phone_code(session,'+8613800138099','127.0.0.99'))
        request=client_module.Client.return_value.send_sms.call_args.args[0]
        code=json.loads(request.template_param)['code']
        self.assertFalse(validate_phone(session,'+8613800138099',code,consume=True))
        self.assertFalse(PhoneChallenge.objects.get(phone='+8613800138099').demo)
    def test_profile_rebinding_and_unbinding_requires_password(self):
        self.client.force_login(self.user)
        session=self.client.session;code=send_phone_code(session,'+8613800138098','127.0.0.98');session.save()
        response=self.client.post('/accounts/profile/',{'email':'owner@example.com','phone':'13800138098','sms_code':code,'current_password':'Current-password-2026!'})
        self.assertEqual(response.status_code,302)
        profile=UserProfile.objects.get(user=self.user);self.assertTrue(profile.phone_demo);self.assertFalse(profile.phone_verified)
        response=self.client.post('/accounts/profile/',{'email':'owner@example.com','phone':'','current_password':'Current-password-2026!'})
        self.assertEqual(response.status_code,302);profile.refresh_from_db();self.assertIsNone(profile.phone)
