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
    def subtotal(self):
        return self.product.price * self.quantity


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "待付款"
        PAID = "paid", "已付款（演示）"
        SHIPPED = "shipped", "已发货"
        CANCELLED = "cancelled", "已取消"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    checkout_token = models.UUIDField(unique=True, editable=False)
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
