from decimal import Decimal
import uuid

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.db.models import Sum, Count, F
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import CheckoutForm, QuantityForm, RegistrationForm
from .models import CartItem, Category, Product, Order, OrderItem
from . import order_services
from django.conf import settings
from django.core.exceptions import PermissionDenied


def register(request):
    form = RegistrationForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, "注册成功，欢迎来到 orangible。")
        return redirect("catalog")
    return render(request, "registration/register.html", {"form": form})


def catalog(request):
    products = Product.objects.filter(is_active=True).select_related("category")
    query = request.GET.get("q", "").strip()[:120]
    category = request.GET.get("category", "")
    if query:
        products = products.filter(Q(name__icontains=query) | Q(description__icontains=query))
    if category:
        if category.isascii() and category.isdigit() and len(category) < 10:
            products = products.filter(category_id=int(category))
        else:
            products = products.none()
    page = Paginator(products, 9).get_page(request.GET.get("page"))
    return render(request, "shop/catalog.html", {
        "page": page, "categories": Category.objects.all(), "query": query, "selected_category": category,
    })


def product_detail(request, pk):
    product = get_object_or_404(Product.objects.select_related("category"), pk=pk, is_active=True)
    return render(request, "shop/detail.html", {"product": product})


@login_required
def cart(request):
    items = list(CartItem.objects.filter(user=request.user).select_related("product"))
    return render(request, "shop/cart.html", {
        "items": items, "total": sum((item.subtotal for item in items), Decimal("0.00")),
    })


@login_required
@require_POST
def add_to_cart(request, pk):
    form = QuantityForm(request.POST)
    if not form.is_valid():
        messages.error(request, "数量必须是 1 至 999 的整数。")
        return redirect("product_detail", pk=pk)
    # Serializes changes to the same product on MySQL, including first insert.
    # Adding to cart does not reserve stock; checkout must revalidate in stage 2.
    with transaction.atomic():
        get_user_model().objects.select_for_update().get(pk=request.user.pk)
        product = get_object_or_404(Product.objects.select_for_update(), pk=pk, is_active=True)
        item = CartItem.objects.filter(user=request.user, product=product).first()
        quantity = (item.quantity if item else 0) + form.cleaned_data["quantity"]
        if quantity > min(product.stock, 999):
            messages.error(request, "加入失败：超过可用库存或购物车数量上限。")
        else:
            if item:
                item.quantity = quantity
                item.save(update_fields=["quantity"])
            else:
                CartItem.objects.create(user=request.user, product=product, quantity=quantity)
            messages.success(request, "已加入购物车。")
    return redirect("cart")


@login_required
@require_POST
def update_cart(request, pk):
    form = QuantityForm(request.POST)
    with transaction.atomic():
        get_user_model().objects.select_for_update().get(pk=request.user.pk)
        # Same lock order as add_to_cart: user, product, then cart row.
        existing = get_object_or_404(CartItem, pk=pk, user=request.user)
        product = get_object_or_404(Product.objects.select_for_update(), pk=existing.product_id)
        item = get_object_or_404(CartItem.objects.select_for_update(), pk=pk, user=request.user)
        if not form.is_valid():
            messages.error(request, "数量必须是 1 至 999 的整数。")
        elif not product.is_active or form.cleaned_data["quantity"] > product.stock:
            messages.error(request, "商品已下架或库存不足，请移除或调整数量。")
        else:
            item.quantity = form.cleaned_data["quantity"]
            item.save(update_fields=["quantity"])
            messages.success(request, "购物车已更新。")
    return redirect("cart")


@login_required
@require_POST
def remove_from_cart(request, pk):
    with transaction.atomic():
        get_user_model().objects.select_for_update().get(pk=request.user.pk)
        item = get_object_or_404(CartItem, pk=pk, user=request.user)
        item.delete()
    messages.success(request, "商品已移除。")
    return redirect("cart")


@login_required
def checkout(request):
    if request.method == "GET":
        token = str(uuid.uuid4())
        request.session["checkout_tokens"] = (request.session.get("checkout_tokens", []) + [token])[-8:]
        form = CheckoutForm(initial={"token": token, "email": request.user.email})
    else:
        form = CheckoutForm(request.POST)
        if form.is_valid():
            if str(form.cleaned_data["token"]) not in request.session.get("checkout_tokens", []):
                form.add_error(None, "结算凭证失效，请重新打开结算页。")
            else:
                try:
                    order = order_services.checkout(request.user, **form.cleaned_data)
                except order_services.OrderError as exc:
                    form.add_error(None, str(exc))
                else:
                    return redirect("order_detail", pk=order.pk)
    items = list(CartItem.objects.filter(user=request.user).select_related("product"))
    return render(request, "shop/checkout.html", {"form": form, "items": items,
        "total": sum((item.subtotal for item in items), Decimal("0.00"))})


@login_required
def order_list(request):
    page = Paginator(Order.objects.filter(user=request.user), 10).get_page(request.GET.get("page"))
    return render(request, "shop/orders.html", {"page": page})


@login_required
def order_detail(request, pk):
    order = get_object_or_404(Order.objects.prefetch_related("items"), pk=pk, user=request.user)
    return render(request, "shop/order_detail.html", {"order": order, "demo_enabled": settings.DEMO_PAYMENT_ENABLED})


@login_required
@require_POST
def pay_order(request, pk):
    get_object_or_404(Order, pk=pk, user=request.user)
    try:
        order_services.pay_demo(request.user, pk)
        messages.success(request, "演示付款已确认，未发生真实扣款。")
    except order_services.OrderError as exc:
        messages.error(request, str(exc))
    return redirect("order_detail", pk=pk)


@login_required
@require_POST
def cancel_order(request, pk):
    get_object_or_404(Order, pk=pk, user=request.user)
    try:
        order_services.cancel(request.user, pk)
        messages.success(request, "订单已取消，预留库存已释放。")
    except order_services.OrderError as exc:
        messages.error(request, str(exc))
    return redirect("order_detail", pk=pk)


def require_sales(user, permission):
    if not user.is_staff or not user.has_perm(permission):
        raise PermissionDenied


@login_required
def sales(request):
    require_sales(request.user, "shop.view_order")
    recognized = Order.objects.filter(status__in=[Order.Status.PAID, Order.Status.SHIPPED])
    return render(request, "shop/sales.html", {
        "orders": Paginator(Order.objects.select_related("user"), 20).get_page(request.GET.get("page")),
        "stats": recognized.aggregate(revenue=Sum("total"), count=Count("pk")),
        "products": OrderItem.objects.filter(order__in=recognized).values("product_id", "name").annotate(
            units=Sum("quantity"), revenue=Sum(F("price") * F("quantity"))).order_by("-revenue"),
    })


@login_required
@require_POST
def ship_order(request, pk):
    require_sales(request.user, "shop.change_order")
    get_object_or_404(Order, pk=pk)
    try:
        order_services.ship(pk)
        messages.success(request, "已标记发货，通知邮件进入待处理队列。")
    except order_services.OrderError as exc:
        messages.error(request, str(exc))
    return redirect("sales")
