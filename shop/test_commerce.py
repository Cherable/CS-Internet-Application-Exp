from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch
from io import BytesIO
import uuid
from django.test import TestCase
from django.utils import timezone
from django.contrib.auth.models import User
from .models import Product, Category, Reservation, ExchangeSnapshot, CartItem
from .commerce_info import reserve, preorder_quote, fx_payload
from .order_services import checkout, cancel, OrderError
class CommerceTests(TestCase):
    def setUp(self):
        self.user=User.objects.create_user('earlybird')
        self.product=Product.objects.create(category=Category.objects.create(name='水果'),name='预约芒果',price=Decimal('100.00'),stock=5,fruit_key='mango',season_months=[timezone.localdate().month],available_on=timezone.localdate()+timedelta(days=21))
    def test_exponential_discount_bounded_and_monotonic(self):
        values=[]
        for days in [0,1,7,21,90,365]:
            self.product.available_on=timezone.localdate()+timedelta(days=days)
            price,discount=preorder_quote(self.product);values.append(discount)
            self.assertGreaterEqual(price,Decimal('80.00'));self.assertLessEqual(discount,20)
        self.assertEqual(values,sorted(values));self.assertEqual(values[0],0)
    def test_reserve_idempotent_and_owner_isolated(self):
        first=reserve(self.user,self.product.pk,2);again=reserve(self.user,self.product.pk,2)
        self.assertEqual(first.pk,again.pk);self.assertEqual(Reservation.objects.count(),1)
        other=User.objects.create_user('other');self.client.force_login(other)
        self.assertNotContains(self.client.get('/reservations/'),self.product.name)
    def test_upcoming_not_cart_or_direct_checkout(self):
        self.client.force_login(self.user)
        self.client.post(f'/cart/add/{self.product.pk}/',{'quantity':1})
        self.assertFalse(CartItem.objects.exists())
        CartItem.objects.create(user=self.user,product=self.product)
        with self.assertRaises(OrderError):checkout(self.user,uuid.uuid4(),'同学','test@example.com','测试地址')
    def test_release_redeems_quote_and_cancel_restores_entitlement(self):
        row=reserve(self.user,self.product.pk,2)
        self.product.available_on=timezone.localdate();self.product.save()
        item=CartItem.objects.create(user=self.user,product=self.product,quantity=2)
        expected=min(self.product.current_price,row.price)
        self.assertEqual(item.subtotal,expected*2)
        order=checkout(self.user,uuid.uuid4(),'同学','test@example.com','测试地址')
        self.assertEqual(order.total,expected*2);row.refresh_from_db();self.assertEqual(row.order_id,order.pk)
        cancel(self.user,order.pk);row.refresh_from_db();self.assertIsNone(row.order_id)
    def test_no_reservation_quantity_overrun(self):
        reserve(self.user,self.product.pk,1);self.product.available_on=timezone.localdate();self.product.save()
        CartItem.objects.create(user=self.user,product=self.product,quantity=2)
        with self.assertRaises(OrderError):checkout(self.user,uuid.uuid4(),'同学','test@example.com','测试地址')
    def test_preorder_hidden_from_regular_and_visible_in_preview(self):
        regular=self.client.get('/');self.assertNotIn(self.product.pk,[p.pk for p in regular.context['page']])
        page=self.client.get('/',{'section':'upcoming'});self.assertContains(page,self.product.name)
        self.assertEqual(len(page.context['hidden_products']),0)
    def test_fx_official_feed_and_cache_failure(self):
        xml=b'<Envelope><Cube><Cube time="2026-11-03"><Cube currency="CNY" rate="8"/><Cube currency="USD" rate="1.2"/></Cube></Cube></Envelope>'
        with patch('shop.commerce_info.urllib.request.urlopen',return_value=BytesIO(xml)):
            data=fx_payload(refresh=True)
        self.assertEqual(data['quotes']['USD'],'6.666667');self.assertEqual(data['published_on'],'2026-11-03')
        ExchangeSnapshot.objects.update(attempted_at=timezone.now()-timedelta(hours=2))
        with patch('shop.commerce_info.urllib.request.urlopen',side_effect=OSError()):data=fx_payload(refresh=True)
        self.assertTrue(data['cached']);self.assertTrue(data['available'])
    def test_fx_failure_without_snapshot_never_invents_rate(self):
        with patch('shop.commerce_info.urllib.request.urlopen',side_effect=OSError()):data=fx_payload(refresh=True)
        self.assertFalse(data['available']);self.assertEqual(data['quotes'],{})
