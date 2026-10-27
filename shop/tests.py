from decimal import Decimal

from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.test import Client, TestCase
from django.urls import reverse

from .models import CartItem, Category, Product


class ShopTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user("alice", "alice@example.com", "Test-pw-2026!")
        cls.other = User.objects.create_user("bob", "bob@example.com", "Test-pw-2026!")
        cls.category = Category.objects.create(name="学习文具")
        cls.product = Product.objects.create(category=cls.category, name="点阵笔记本", description="用于学习", price="18.90", stock=5)
        cls.hidden = Product.objects.create(category=cls.category, name="下架测试商品", price="1.00", stock=5, is_active=False)

    def login(self):
        self.client.force_login(self.user)

    def test_registration_hashes_password_and_logs_in(self):
        response = self.client.post(reverse("register"), {"username": "charlie", "email": "c@example.com", "password1": "Good-study-2026!", "password2": "Good-study-2026!"})
        self.assertRedirects(response, reverse("catalog"))
        user = User.objects.get(username="charlie")
        self.assertTrue(user.check_password("Good-study-2026!"))
        self.assertNotEqual(user.password, "Good-study-2026!")
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)

    def test_duplicate_username_and_bad_email_rejected(self):
        response = self.client.post(reverse("register"), {"username": "alice", "email": "invalid", "password1": "Good-study-2026!", "password2": "Good-study-2026!"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("email", response.context["form"].errors)
        self.assertIn("username", response.context["form"].errors)
        self.assertEqual(User.objects.count(), 2)

    def test_weak_password_rejected(self):
        response = self.client.post(reverse("register"), {"username": "charlie", "email": "c@example.com", "password1": "123", "password2": "123"})
        self.assertIn("password2", response.context["form"].errors)

    def test_login_failure_and_success(self):
        response = self.client.post(reverse("login"), {"username": "alice", "password": "wrong"})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)
        response = self.client.post(reverse("login"), {"username": "alice", "password": "Test-pw-2026!"})
        self.assertRedirects(response, reverse("catalog"))

    def test_logout_requires_post(self):
        self.login()
        self.assertEqual(self.client.get(reverse("logout")).status_code, 405)
        self.assertRedirects(self.client.post(reverse("logout")), reverse("catalog"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_login_rejects_external_redirect(self):
        response = self.client.post(reverse("login"), {"username": "alice", "password": "Test-pw-2026!", "next": "https://evil.example/"})
        self.assertRedirects(response, reverse("catalog"))

    def test_catalog_search_category_and_hidden_products(self):
        response = self.client.get(reverse("catalog"), {"q": "笔记", "category": self.category.pk})
        self.assertContains(response, self.product.name)
        self.assertNotContains(response, self.hidden.name)
        self.assertEqual(self.client.get(reverse("product_detail", args=[self.hidden.pk])).status_code, 404)
        self.assertContains(self.client.get(reverse("catalog"), {"q": "无结果"}), "暂时没有")

    def test_bad_category_does_not_raise_server_error(self):
        for value in ("invalid", "9" * 40, "１２３"):
            response = self.client.get(reverse("catalog"), {"category": value})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context["page"].paginator.count, 0)

    def test_pagination_and_out_of_range_page(self):
        Product.objects.bulk_create([Product(category=self.category, name=f"商品{i}", price="1.00", stock=1) for i in range(12)])
        response = self.client.get(reverse("catalog"))
        self.assertEqual(len(response.context["page"]), 9)
        self.assertEqual(self.client.get(reverse("catalog"), {"page": "999"}).context["page"].number, 2)

    def test_anonymous_cart_requires_login(self):
        response = self.client.get(reverse("cart"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)

    def test_add_merges_cart_and_keeps_decimal_total(self):
        self.login()
        url = reverse("add_to_cart", args=[self.product.pk])
        self.client.post(url, {"quantity": 1})
        self.client.post(url, {"quantity": 2})
        self.assertEqual(CartItem.objects.get(user=self.user).quantity, 3)
        self.assertEqual(self.client.get(reverse("cart")).context["total"], Decimal("56.70"))
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 5)

    def test_invalid_and_overstock_quantities_rejected(self):
        self.login()
        for quantity in ("0", "-1", "1.2", "x", "6", "1000"):
            self.client.post(reverse("add_to_cart", args=[self.product.pk]), {"quantity": quantity})
        self.assertFalse(CartItem.objects.exists())
        self.client.post(reverse("add_to_cart", args=[self.product.pk]), {"quantity": 4})
        self.client.post(reverse("add_to_cart", args=[self.product.pk]), {"quantity": 2})
        self.assertEqual(CartItem.objects.get().quantity, 4)

    def test_out_of_stock_and_hidden_add_rejected(self):
        self.login()
        self.product.stock = 0
        self.product.save()
        self.client.post(reverse("add_to_cart", args=[self.product.pk]), {"quantity": 1})
        self.assertFalse(CartItem.objects.exists())
        self.assertEqual(self.client.post(reverse("add_to_cart", args=[self.hidden.pk]), {"quantity": 1}).status_code, 404)

    def test_owner_update_and_delete(self):
        self.login()
        item = CartItem.objects.create(user=self.user, product=self.product)
        self.client.post(reverse("update_cart", args=[item.pk]), {"quantity": 3})
        item.refresh_from_db()
        self.assertEqual(item.quantity, 3)
        self.client.post(reverse("remove_from_cart", args=[item.pk]))
        self.assertFalse(CartItem.objects.exists())

    def test_other_users_cannot_read_modify_or_delete_cart(self):
        self.login()
        item = CartItem.objects.create(user=self.other, product=self.product)
        self.assertEqual(list(self.client.get(reverse("cart")).context["items"]), [])
        self.assertEqual(self.client.post(reverse("update_cart", args=[item.pk]), {"quantity": 2}).status_code, 404)
        self.assertEqual(self.client.post(reverse("remove_from_cart", args=[item.pk])).status_code, 404)
        self.assertTrue(CartItem.objects.filter(pk=item.pk).exists())

    def test_cart_mutations_require_post_and_csrf(self):
        self.login()
        item = CartItem.objects.create(user=self.user, product=self.product)
        urls = [reverse("add_to_cart", args=[self.product.pk]), reverse("update_cart", args=[item.pk]), reverse("remove_from_cart", args=[item.pk])]
        for url in urls:
            self.assertEqual(self.client.get(url).status_code, 405)
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        self.assertEqual(client.post(urls[0], {"quantity": 1}).status_code, 403)

    def test_update_rejects_stock_reduction_and_inactive_product(self):
        self.login()
        item = CartItem.objects.create(user=self.user, product=self.product)
        self.client.post(reverse("update_cart", args=[item.pk]), {"quantity": 6})
        self.product.is_active = False
        self.product.save()
        self.client.post(reverse("update_cart", args=[item.pk]), {"quantity": 2})
        item.refresh_from_db()
        self.assertEqual(item.quantity, 1)

    def test_database_constraints(self):
        CartItem.objects.create(user=self.user, product=self.product)
        with self.assertRaises(IntegrityError), transaction.atomic():
            CartItem.objects.create(user=self.user, product=self.product)
        with self.assertRaises(IntegrityError), transaction.atomic():
            CartItem.objects.create(user=self.other, product=self.product, quantity=0)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Product.objects.create(category=self.category, name="零元商品", price=0)

    def test_html_escaped(self):
        self.product.name = '<script>alert("x")</script>'
        self.product.save()
        response = self.client.get(reverse("product_detail", args=[self.product.pk]))
        self.assertNotContains(response, '<script>alert("x")</script>')
        self.assertContains(response, "&lt;script&gt;")

    def test_customer_cannot_access_admin(self):
        self.login()
        response = self.client.get("/admin/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response.url)
