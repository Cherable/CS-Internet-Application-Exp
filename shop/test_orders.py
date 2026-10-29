import uuid
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from io import StringIO
from threading import Barrier
from unittest.mock import patch

from django.contrib.auth.models import Permission, User
from django.core import mail
from django.core.management import call_command
from django.db import close_old_connections, connection
from django.test import Client, TestCase, TransactionTestCase, override_settings
from django.urls import reverse

from .models import CartItem, Category, Order, Product, ShipmentEmail
from .order_services import OrderError, cancel, checkout, pay_demo, ship


@override_settings(DEMO_PAYMENT_ENABLED=True, EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class OrderTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user("buyer", "buyer@example.com", "Unshared-test-password!")
        cls.other = User.objects.create_user("other")
        cls.staff = User.objects.create_user("seller", is_staff=True)
        cls.staff.user_permissions.add(*Permission.objects.filter(codename__in=["view_order", "change_order"]))
        cls.product = Product.objects.create(category=Category.objects.create(name="文具"), name="橙色笔记本", price="18.90", stock=5)

    def make_order(self, user=None, quantity=2, token=None):
        user = user or self.user
        CartItem.objects.create(user=user, product=self.product, quantity=quantity)
        return checkout(user, token or uuid.uuid4(), "同学", user.email or "test@example.com", "校园自提点")

    def test_checkout_snapshot_reserves_stock_and_clears_cart(self):
        order = self.make_order()
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 3)
        self.assertEqual(order.total, Decimal("37.80"))
        self.assertFalse(CartItem.objects.exists())
        self.product.name = "已改名"
        self.product.price = Decimal("99.00")
        self.product.save()
        self.assertEqual(order.items.get().name, "橙色笔记本")
        self.assertEqual(order.items.get().subtotal, Decimal("37.80"))

    def test_checkout_replay_does_not_charge_stock_twice(self):
        order = self.make_order()
        again = checkout(self.user, order.checkout_token, "换名字", "new@example.com", "新地址")
        self.assertEqual(order.pk, again.pk)
        self.assertEqual(Order.objects.count(), 1)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 3)

    def test_checkout_all_or_nothing_for_insufficient_stock(self):
        CartItem.objects.create(user=self.user, product=self.product, quantity=1)
        other = Product.objects.create(category=self.product.category, name="售罄", price=2, stock=0)
        CartItem.objects.create(user=self.user, product=other)
        with self.assertRaises(OrderError):
            checkout(self.user, uuid.uuid4(), "同学", "test@example.com", "地址")
        self.assertFalse(Order.objects.exists())
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 5)
        self.assertEqual(CartItem.objects.count(), 2)

    def test_inactive_and_empty_cart_rejected(self):
        with self.assertRaises(OrderError):
            checkout(self.user, uuid.uuid4(), "同学", "test@example.com", "地址")
        self.product.is_active = False
        self.product.save()
        with self.assertRaises(OrderError):
            self.make_order()

    def test_demo_payment_replay_and_server_total(self):
        order = self.make_order()
        self.client.force_login(self.user)
        for _ in range(2):
            self.client.post(reverse("pay_order", args=[order.pk]), {"total": "0.01", "status": "shipped"})
        order.refresh_from_db()
        self.assertEqual(order.status, "paid")
        self.assertEqual(order.total, Decimal("37.80"))
        paid_at = order.paid_at
        pay_demo(self.user, order.pk)
        order.refresh_from_db()
        self.assertEqual(order.paid_at, paid_at)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 3)

    @override_settings(DEMO_PAYMENT_ENABLED=False)
    def test_payment_can_be_disabled(self):
        order = self.make_order()
        with self.assertRaises(OrderError):
            pay_demo(self.user, order.pk)
        order.refresh_from_db()
        self.assertEqual(order.status, "pending")

    def test_cancel_restores_inventory_once_and_blocks_payment(self):
        order = self.make_order()
        cancel(self.user, order.pk)
        cancel(self.user, order.pk)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 5)
        with self.assertRaises(OrderError):
            pay_demo(self.user, order.pk)

    def test_shipping_transition_and_outbox_idempotency(self):
        order = self.make_order()
        with self.assertRaises(OrderError):
            ship(order.pk)
        pay_demo(self.user, order.pk)
        with self.assertRaises(OrderError):
            cancel(self.user, order.pk)
        ship(order.pk)
        ship(order.pk)
        self.assertEqual(ShipmentEmail.objects.count(), 1)
        order.refresh_from_db()
        self.assertEqual(order.status, "shipped")
        self.assertIsNotNone(order.shipped_at)

    def test_outbox_preview_not_delivery_and_no_resend(self):
        order = self.make_order()
        pay_demo(self.user, order.pk)
        ship(order.pk)
        for _ in range(2):
            call_command("send_shipment_emails", stdout=StringIO())
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.user.email])
        self.assertIn(str(order.pk), mail.outbox[0].body)
        self.assertEqual(order.shipment_email.status, "preview")
        self.assertEqual(order.shipment_email.attempts, 1)

    def test_outbox_failure_retry_without_rolling_back_shipment(self):
        order = self.make_order()
        pay_demo(self.user, order.pk)
        ship(order.pk)
        with patch("shop.management.commands.send_shipment_emails.send_mail", side_effect=ConnectionError("private")):
            call_command("send_shipment_emails", stdout=StringIO())
        message = ShipmentEmail.objects.get()
        self.assertEqual(message.status, "failed")
        self.assertEqual(message.last_error, "ConnectionError")
        order.refresh_from_db()
        self.assertEqual(order.status, "shipped")
        call_command("send_shipment_emails", stdout=StringIO())
        message.refresh_from_db()
        self.assertEqual(message.status, "preview")
        self.assertEqual(message.attempts, 2)

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend")
    def test_mock_smtp_records_acceptance_only(self):
        order = self.make_order()
        pay_demo(self.user, order.pk)
        ship(order.pk)
        with patch("shop.management.commands.send_shipment_emails.send_mail", return_value=1):
            call_command("send_shipment_emails", stdout=StringIO())
        self.assertEqual(ShipmentEmail.objects.get().status, "accepted")

    def test_cross_customer_read_pay_cancel_forbidden(self):
        order = self.make_order()
        self.client.force_login(self.other)
        for name in ("order_detail", "pay_order", "cancel_order"):
            response = self.client.get(reverse(name, args=[order.pk])) if name == "order_detail" else self.client.post(reverse(name, args=[order.pk]))
            self.assertEqual(response.status_code, 404)
        self.assertNotContains(self.client.get(reverse("orders")), str(order.pk))

    def test_checkout_form_requires_issued_token_and_valid_address(self):
        self.client.force_login(self.user)
        CartItem.objects.create(user=self.user, product=self.product)
        data = {"token": str(uuid.uuid4()), "recipient": "同学", "email": "test@example.com", "address": "地址"}
        response = self.client.post(reverse("checkout"), data)
        self.assertContains(response, "结算凭证失效")
        response = self.client.get(reverse("checkout"))
        data["token"] = str(response.context["form"].initial["token"])
        data["email"] = "bad"
        self.assertEqual(self.client.post(reverse("checkout"), data).status_code, 200)
        self.assertFalse(Order.objects.exists())
        data["email"] = "test@example.com"
        first = self.client.post(reverse("checkout"), data)
        again = self.client.post(reverse("checkout"), data)
        self.assertEqual(first.url, again.url)
        self.assertEqual(Order.objects.count(), 1)

    def test_csrf_and_http_methods(self):
        order = self.make_order()
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        for name in ("pay_order", "cancel_order"):
            url = reverse(name, args=[order.pk])
            self.assertEqual(client.get(url).status_code, 405)
            self.assertEqual(client.post(url).status_code, 403)
        self.assertEqual(client.post(reverse("checkout")).status_code, 403)

    def test_staff_permissions_and_statistics_exclude_unpaid_cancelled(self):
        paid = self.make_order()
        pay_demo(self.user, paid.pk)
        cancelled = self.make_order(self.other, quantity=1)
        cancel(self.other, cancelled.pk)
        self.make_order(quantity=1)
        for user in (self.user, User.objects.create_user("no_permission", is_staff=True)):
            self.client.force_login(user)
            self.assertEqual(self.client.get(reverse("sales")).status_code, 403)
            self.assertEqual(self.client.post(reverse("ship_order", args=[paid.pk])).status_code, 403)
        self.client.force_login(self.staff)
        response = self.client.get(reverse("sales"))
        self.assertEqual(response.context["stats"], {"revenue": Decimal("37.80"), "count": 1})
        self.assertEqual(list(response.context["products"])[0]["units"], 2)
        self.assertEqual(self.client.post(reverse("ship_order", args=[paid.pk])).status_code, 302)
        paid.refresh_from_db()
        self.assertEqual(paid.status, "shipped")

    def test_admin_order_has_no_manual_status_or_delete(self):
        from .admin import OrderAdmin
        from django.contrib import admin
        from django.test import RequestFactory
        model_admin = OrderAdmin(Order, admin.site)
        request = RequestFactory().get("/")
        request.user = self.staff
        self.assertIn("status", model_admin.readonly_fields)
        self.assertFalse(model_admin.has_add_permission(request))
        self.assertFalse(model_admin.has_delete_permission(request))


class MySQLConcurrencyTests(TransactionTestCase):
    """Real parallel connections; never pretend SQLite tests establish row locking."""
    def setUp(self):
        if connection.vendor != "mysql":
            self.skipTest("MySQL row-lock concurrency requires a MySQL test database")
        self.users = [User.objects.create_user(f"concurrent{i}") for i in range(2)]
        self.product = Product.objects.create(category=Category.objects.create(name="并发"), name="最后一件", price="9.90", stock=1)

    def run_parallel(self, operation):
        barrier = Barrier(2)
        def worker(index):
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                return operation(index)
            finally:
                close_old_connections()
        with ThreadPoolExecutor(max_workers=2) as pool:
            return list(pool.map(worker, range(2)))

    def test_two_buyers_last_unit_only_one_succeeds(self):
        for user in self.users:
            CartItem.objects.create(user=user, product=self.product)
        def buy(index):
            try:
                checkout(self.users[index], uuid.uuid4(), "同学", "test@example.com", "地址")
                return "ok"
            except OrderError:
                return "out_of_stock"
        self.assertCountEqual(self.run_parallel(buy), ["ok", "out_of_stock"])
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 0)
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(CartItem.objects.count(), 1)

    def test_parallel_same_checkout_token_reserves_once(self):
        user = self.users[0]
        token = uuid.uuid4()
        CartItem.objects.create(user=user, product=self.product)
        ids = self.run_parallel(lambda _: checkout(user, token, "同学", "test@example.com", "地址").pk)
        self.assertEqual(ids[0], ids[1])
        self.assertEqual(Order.objects.count(), 1)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 0)

    @override_settings(DEMO_PAYMENT_ENABLED=True)
    def test_parallel_payment_and_cancel_have_one_terminal_transition(self):
        user = self.users[0]
        CartItem.objects.create(user=user, product=self.product)
        order = checkout(user, uuid.uuid4(), "同学", "test@example.com", "地址")
        def transition(index):
            try:
                return (pay_demo if index == 0 else cancel)(user, order.pk).status
            except OrderError:
                return "blocked"
        results = self.run_parallel(transition)
        self.assertIn("blocked", results)
        order.refresh_from_db()
        self.product.refresh_from_db()
        self.assertIn(order.status, ["paid", "cancelled"])
        self.assertEqual(self.product.stock, 0 if order.status == "paid" else 1)
