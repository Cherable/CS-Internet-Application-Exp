"""Transactional order transitions. Payment is explicitly a local demonstration."""
from decimal import Decimal

from django.conf import settings
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import F

from .models import CartItem, Order, OrderItem, Product, ShipmentEmail, Reservation


class OrderError(ValueError):
    pass


@transaction.atomic
def checkout(user, token, recipient, email, address):
    # Every cart mutation takes this same user lock before touching products.
    get_user_model().objects.select_for_update().get(pk=user.pk)
    existing = Order.objects.filter(user=user, checkout_token=token).first()
    if existing:
        return existing
    items = list(CartItem.objects.filter(user=user).order_by("product_id"))
    if not items:
        raise OrderError("购物车为空。")
    products = {p.pk: p for p in Product.objects.select_for_update().filter(
        pk__in=[item.product_id for item in items]).order_by("pk")}
    reservations = {}
    prices = {}
    total = Decimal("0.00")
    for item in items:
        product = products[item.product_id]
        if product.is_upcoming: raise OrderError("预约商品尚未上架。")
        if not product.is_active or product.stock < item.quantity or (product.best_before and product.best_before < timezone.localdate()):
            raise OrderError(f"{product.name} 已下架或库存不足，请调整购物车。")
        reservation=Reservation.objects.select_for_update().filter(user=user,product=product,order__isnull=True).first()
        if reservation and item.quantity > reservation.quantity:
            raise OrderError("该商品超过预约数量，请调整数量后使用预约优惠。")
        if reservation: reservations[product.pk]=reservation
        prices[product.pk] = min(product.current_price,reservation.price) if reservation else product.current_price
        total += prices[product.pk] * item.quantity
    order = Order.objects.create(user=user, checkout_token=token, recipient=recipient,
                                 email=email, address=address, total=total,
                                 simulated_dispatch_hours=max(p.dispatch_hours for p in products.values()),
                                 simulated_transit_hours=max(p.transit_hours for p in products.values()))
    for item in items:
        product = products[item.product_id]
        # Conditional UPDATE is an additional oversell guard, including SQLite preview.
        if Product.objects.filter(pk=product.pk, stock__gte=item.quantity).update(
                stock=F("stock") - item.quantity) != 1:
            raise OrderError("库存发生变化，请重试。")
        OrderItem.objects.create(order=order, product=product, name=product.name,
                                 price=prices[product.pk], quantity=item.quantity)
    for reservation in reservations.values():
        reservation.order=order
        reservation.save(update_fields=["order"])
    CartItem.objects.filter(pk__in=[item.pk for item in items]).delete()
    return order


@transaction.atomic
def pay_demo(user, order_id):
    if not settings.DEMO_PAYMENT_ENABLED:
        raise OrderError("演示支付已关闭；尚未接入平台沙箱，不支持真实收款。")
    order = Order.objects.select_for_update().get(pk=order_id, user=user)
    if order.status in (Order.Status.PAID, Order.Status.SHIPPED):
        return order
    if order.status != Order.Status.PENDING:
        raise OrderError("当前订单不能付款。")
    from django.utils import timezone
    order.status = Order.Status.PAID
    order.paid_at = timezone.now()
    order.save(update_fields=["status", "paid_at"])
    return order


@transaction.atomic
def cancel(user, order_id):
    get_user_model().objects.select_for_update().get(pk=user.pk)
    order = Order.objects.select_for_update().get(pk=order_id, user=user)
    if order.status == Order.Status.CANCELLED:
        return order
    if order.status != Order.Status.PENDING:
        raise OrderError("仅待付款订单可以取消。")
    items = list(order.items.order_by("product_id"))
    # Lock in the same product order as checkout.
    list(Product.objects.select_for_update().filter(
        pk__in=[item.product_id for item in items]).order_by("pk"))
    for item in items:
        Product.objects.filter(pk=item.product_id).update(stock=F("stock") + item.quantity)
    Reservation.objects.filter(order=order).update(order=None)
    order.status = Order.Status.CANCELLED
    order.save(update_fields=["status"])
    return order


@transaction.atomic
def ship(order_id):
    order = Order.objects.select_for_update().get(pk=order_id)
    if order.status == Order.Status.SHIPPED:
        return order
    if order.status != Order.Status.PAID:
        raise OrderError("仅已付款订单可以发货。")
    from django.utils import timezone
    order.status = Order.Status.SHIPPED
    order.shipped_at = timezone.now()
    order.save(update_fields=["status", "shipped_at"])
    ShipmentEmail.objects.get_or_create(order=order)
    return order
