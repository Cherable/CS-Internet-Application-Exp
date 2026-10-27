from decimal import Decimal

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
