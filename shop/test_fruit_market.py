from datetime import timedelta
from decimal import Decimal
import uuid
from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from .models import Product, Category, FruitDay, CartItem
from .fruit_market import decorate, ensure_day
from .order_services import checkout, pay_demo, OrderError

class FruitMarketTests(TestCase):
    def setUp(self):
        self.p=Product.objects.create(category=Category.objects.create(name="水果"),name="测试芒果",price=Decimal("39.90"),stock=100,fruit_key="mango",season_months=list(range(1,13)),sale_kind="ready")
        self.user=User.objects.create_user("fruitbuyer")
    def test_daily_rows_are_persisted_and_not_rerolled(self):
        row=ensure_day(self.p);before=(row.simulated_units,row.discount)
        ensure_day(self.p);self.assertEqual(FruitDay.objects.count(),30)
        row.refresh_from_db();self.assertEqual(before,(row.simulated_units,row.discount))
    def test_manual_input_and_payment_are_immediate_without_double_count(self):
        decorate(self.p);before=self.p.month_sales
        row=ensure_day(self.p);row.manual_units=500;row.save()
        decorate(self.p);self.assertEqual(self.p.month_sales,before+500)
        CartItem.objects.create(user=self.user,product=self.p,quantity=3)
        order=checkout(self.user,uuid.uuid4(),"测试","test@example.com","测试地址")
        pay_demo(self.user,order.pk);pay_demo(self.user,order.pk)
        decorate(self.p);self.assertEqual(self.p.month_sales,before+503)
    def test_next_day_continues_and_rolling_window_moves(self):
        today=timezone.localdate();ensure_day(self.p,today)
        earliest=FruitDay.objects.filter(product=self.p).order_by('day').first();earliest.manual_units=999;earliest.save()
        decorate(self.p,today);before=self.p.month_sales
        decorate(self.p,today+timedelta(days=1))
        newest=FruitDay.objects.get(day=today+timedelta(days=1))
        self.assertEqual(self.p.month_sales,before-earliest.simulated_units-999+newest.simulated_units)
        self.assertEqual(FruitDay.objects.count(),31)
    def test_quote_matches_order_snapshot(self):
        price=self.p.current_price;self.assertLess(price,self.p.price)
        CartItem.objects.create(user=self.user,product=self.p,quantity=2)
        order=checkout(self.user,uuid.uuid4(),"测试","test@example.com","测试地址")
        self.assertEqual(order.total,price*2);self.assertEqual(order.items.get().price,price)
    def test_expired_lot_hidden_and_cannot_checkout(self):
        self.p.best_before=timezone.localdate()-timedelta(days=1);self.p.save()
        self.assertNotContains(self.client.get('/'),self.p.name)
        CartItem.objects.create(user=self.user,product=self.p)
        with self.assertRaises(OrderError):checkout(self.user,uuid.uuid4(),"测试","test@example.com","测试地址")
    def test_catalog_season_offers_and_sort(self):
        expensive=Product.objects.create(category=self.p.category,name="第二种",price=99,fruit_key="papaya",stock=10,season_months=[])
        response=self.client.get('/',{'section':'season'});self.assertContains(response,self.p.name);self.assertNotContains(response,expensive.name)
        self.assertNotContains(self.client.get('/',{'section':'offers'}),expensive.name)
        self.assertEqual(self.client.get('/',{'sort':'price'}).context['page'][0].pk,self.p.pk)
    def test_snapshot_and_manual_admin_permissions(self):
        self.assertEqual(self.client.get('/fruit-market/').status_code,200)
        self.client.force_login(self.user)
        self.assertEqual(self.client.get('/admin/shop/fruitday/').status_code,302)
