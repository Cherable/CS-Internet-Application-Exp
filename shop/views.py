from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import QuantityForm, RegistrationForm
from .models import CartItem, Category, Product


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
        # Same lock order as add_to_cart: product, then cart row.
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
    item = get_object_or_404(CartItem, pk=pk, user=request.user)
    item.delete()
    messages.success(request, "商品已移除。")
    return redirect("cart")
