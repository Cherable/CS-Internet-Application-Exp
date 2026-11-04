from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from .models import Category, Product, CartItem
class HiddenFruitTests(TestCase):
    def setUp(self):
        c=Category.objects.create(name="水果")
        self.live=Product.objects.create(category=c,name="在售香蕉",price=20,stock=5,fruit_key="banana",season_months=[timezone.localdate().month])
        self.off=Product.objects.create(category=c,name="过季榴莲",price=90,stock=4,fruit_key="durian",season_months=[])
        self.empty=Product.objects.create(category=c,name="缺货牛油果",price=30,stock=0,fruit_key="avocado",season_months=[timezone.localdate().month])
    def test_split_and_collapsed_markup(self):
        response=self.client.get('/')
        self.assertEqual([p.pk for p in response.context['page']],[self.live.pk])
        self.assertCountEqual([p.pk for p in response.context['hidden_products']],[self.off.pk,self.empty.pk])
        self.assertContains(response,'id="hidden-fruit-grid" hidden')
        self.assertContains(response,'加载更多（2）')
        self.assertContains(response,'is-dormant',count=2)
    def test_out_of_stock_detail_and_direct_add(self):
        user=User.objects.create_user('viewer');self.client.force_login(user)
        response=self.client.get(f'/products/{self.empty.pk}/')
        self.assertContains(response,'本批次售罄')
        self.client.post(f'/cart/add/{self.empty.pk}/',{'quantity':1})
        self.assertFalse(CartItem.objects.exists())
    def test_search_keeps_unavailable_results_in_reveal_area(self):
        response=self.client.get('/',{'q':'榴莲'})
        self.assertEqual(response.context['page'].paginator.count,0)
        self.assertEqual(response.context['hidden_products'][0].pk,self.off.pk)
    def test_snapshot_availability_changes_with_stock(self):
        snapshot={p['id']:p for p in self.client.get('/fruit-market/').json()['products']}
        self.assertFalse(snapshot[self.live.pk]['dormant'])
        self.assertTrue(snapshot[self.empty.pk]['dormant'])
        self.live.stock=0;self.live.save()
        snapshot={p['id']:p for p in self.client.get('/fruit-market/').json()['products']}
        self.assertTrue(snapshot[self.live.pk]['dormant'])
