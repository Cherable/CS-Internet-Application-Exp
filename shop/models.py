from decimal import Decimal
import uuid

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class Category(models.Model):
    name = models.CharField("分类名称", max_length=60, unique=True)

    class Meta:
        verbose_name = "商品分类"
        verbose_name_plural = verbose_name
        ordering = ["id"]

    def __str__(self):
        return self.name


class Product(models.Model):
    category = models.ForeignKey(Category, on_delete=models.PROTECT, verbose_name="分类")
    name = models.CharField("商品名称", max_length=120, db_index=True)
    description = models.TextField("商品描述", blank=True)
    price = models.DecimalField("单价", max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    stock = models.PositiveIntegerField("库存", default=0)
    is_active = models.BooleanField("上架", default=True)
    fruit_key = models.SlugField(blank=True)
    image_name = models.CharField(max_length=100, blank=True)
    origin = models.CharField("产地", max_length=160, blank=True)
    flavor = models.TextField("风味", blank=True)
    growing_story = models.TextField("种植与采收", blank=True)
    season_months = models.JSONField("旺季月份（模拟）", default=list, blank=True)
    sale_kind = models.CharField("销售类型", max_length=12, default="regular", choices=[("regular", "常规"), ("ready", "即食"), ("clearance", "临期")])
    best_before = models.DateField("建议食用截止日期", null=True, blank=True)

    available_on = models.DateField("预计上架日期", null=True, blank=True)
    overseas = models.BooleanField("海外水果", default=False)
    source_currency = models.CharField("参考外币", max_length=3, default="CNY")
    dispatch_hours = models.PositiveIntegerField("平均备货小时（估计）", default=24)
    transit_hours = models.PositiveIntegerField("平均运输小时（估计）", default=48)
    tasting_days = models.PositiveIntegerField("送达后赏味天数（估计）", default=3)

    @property
    def is_upcoming(self):
        from django.utils import timezone
        return bool(self.available_on and self.available_on > timezone.localdate())

    @property
    def delivery_days(self):
        return round((self.dispatch_hours + self.transit_hours) / 24, 1)

    @property
    def current_price(self):
        if not self.fruit_key:
            return self.price
        if hasattr(self, "today_price"):
            return self.today_price
        from .fruit_market import quote
        return quote(self)[0]

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "商品"
        verbose_name_plural = verbose_name
        ordering = ["-created_at", "-id"]
        constraints = [models.CheckConstraint(condition=models.Q(price__gt=0), name="product_price_positive")]

    def __str__(self):
        return self.name


class CartItem(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])

    class Meta:
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(fields=["user", "product"], name="unique_user_product_cart"),
            models.CheckConstraint(condition=models.Q(quantity__gte=1), name="cart_quantity_positive"),
        ]

    @property
    def unit_price(self):
        reservation=Reservation.objects.filter(user_id=self.user_id,product_id=self.product_id,order__isnull=True).first()
        if reservation and not self.product.is_upcoming and self.quantity<=reservation.quantity:
            return min(self.product.current_price,reservation.price)
        return self.product.current_price

    @property
    def subtotal(self):
        return self.unit_price * self.quantity


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "待付款"
        PAID = "paid", "已付款（演示）"
        SHIPPED = "shipped", "已发货"
        CANCELLED = "cancelled", "已取消"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    checkout_token = models.UUIDField(unique=True, editable=False)
    simulated_dispatch_hours = models.PositiveIntegerField(default=24)
    simulated_transit_hours = models.PositiveIntegerField(default=48)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    recipient = models.CharField("收件人", max_length=80)
    email = models.EmailField("发货通知邮箱")
    address = models.CharField("收货地址", max_length=300)
    total = models.DecimalField("订单金额", max_digits=14, decimal_places=2)
    status = models.CharField("状态", max_length=12, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    shipped_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "订单"
        verbose_name_plural = verbose_name
        constraints = [
            models.CheckConstraint(condition=models.Q(total__gt=0), name="order_total_positive"),
            models.CheckConstraint(condition=models.Q(status__in=["pending", "paid", "shipped", "cancelled"]), name="order_status_valid"),
        ]

    def __str__(self):
        return str(self.pk)


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    name = models.CharField(max_length=120)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField()

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(quantity__gt=0), name="order_item_quantity_positive"),
            models.CheckConstraint(condition=models.Q(price__gt=0), name="order_item_price_positive"),
        ]

    @property
    def subtotal(self):
        return self.price * self.quantity


class ShipmentEmail(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "待处理"
        PREVIEW = "preview", "本地预览，未投递"
        ACCEPTED = "accepted", "SMTP 已接受，未确认收件"
        FAILED = "failed", "失败，可重试"

    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="shipment_email")
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    attempts = models.PositiveIntegerField(default=0)
    last_error = models.CharField(max_length=160, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)


class FruitDay(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="market_days")
    day = models.DateField()
    simulated_units = models.PositiveIntegerField(default=0)
    manual_units = models.PositiveIntegerField("补录销量（不含本站订单）", default=0)
    supply = models.PositiveIntegerField("模拟供给", default=0)
    discount = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["product", "day"], name="unique_fruit_day")]
        ordering = ["-day", "product_id"]
        verbose_name = "水果每日数据"
        verbose_name_plural = verbose_name


class Reservation(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    discount = models.DecimalField(max_digits=5, decimal_places=2)
    available_on = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    order = models.ForeignKey(Order, on_delete=models.PROTECT, null=True, blank=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "product"], name="unique_user_fruit_reservation"), models.CheckConstraint(condition=models.Q(quantity__gte=1), name="reservation_positive_quantity")]


class ExchangeSnapshot(models.Model):
    key = models.CharField(max_length=20, primary_key=True, default="ecb")
    rates = models.JSONField(default=dict)
    published_on = models.DateField(null=True)
    fetched_at = models.DateTimeField(null=True)
    attempted_at = models.DateTimeField(null=True)
    failed = models.BooleanField(default=False)


class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    display_name = models.CharField(max_length=60, blank=True)
    default_recipient = models.CharField(max_length=80, blank=True)
    default_address = models.CharField(max_length=300, blank=True)
    phone = models.CharField(max_length=16, null=True, blank=True, unique=True)
    phone_verified = models.BooleanField(default=False)
    phone_demo = models.BooleanField(default=False)

class PhoneChallenge(models.Model):
    session_key = models.CharField(max_length=40)
    phone = models.CharField(max_length=16)
    code_hash = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    attempts = models.PositiveIntegerField(default=0)
    consumed = models.BooleanField(default=False)
    demo = models.BooleanField(default=False)

class VerificationThrottle(models.Model):
    key = models.CharField(max_length=64, primary_key=True)
    window_started = models.DateTimeField()
    last_sent = models.DateTimeField(null=True)
    count = models.PositiveIntegerField(default=0)
