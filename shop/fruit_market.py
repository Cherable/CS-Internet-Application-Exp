"""Persisted daily simulation; real orders and manual additions remain separate."""
import hashlib
from datetime import timedelta, datetime, time
from decimal import Decimal, ROUND_HALF_UP
from django.db.models import Sum
from django.utils import timezone
from .models import FruitDay, OrderItem


def payment_window(start, end):
    # UTC-aware boundaries also work on MySQL installations without timezone tables.
    return {"order__paid_at__gte": timezone.make_aware(datetime.combine(start, time.min)),
            "order__paid_at__lt": timezone.make_aware(datetime.combine(end + timedelta(days=1), time.min))}


def ensure_day(product, today=None):
    today = today or timezone.localdate()
    existing = FruitDay.objects.filter(product=product, day=today).first()
    if existing:
        return existing
    latest = FruitDay.objects.filter(product=product, day__lte=today).order_by("-day").first()
    start = latest.day + timedelta(days=1) if latest else today - timedelta(days=29)
    previous = latest.simulated_units if latest else 24 + product.pk * 3
    if latest:
        actual = OrderItem.objects.filter(product=product, order__status__in=["paid","shipped"], **payment_window(latest.day, latest.day)).aggregate(n=Sum("quantity"))["n"] or 0
        previous += round(min(100, latest.manual_units + actual) * .15)
    while start <= today:
        seed = int(hashlib.sha256(f"{product.pk}:{start}".encode()).hexdigest()[:8], 16)
        in_season = start.month in product.season_months
        target = 44 if in_season else 24
        demand = max(5, round(previous * .8 + target * .2) + seed % 9 - 4)
        supply = max(8, round(target * (1.55 if in_season else 1.05)) + seed % 13)
        discount = min(25, max(0, round(25 * (supply / max(demand, 1) - 1))))
        if product.sale_kind == "ready": discount = max(discount, 20)
        if product.sale_kind == "clearance": discount = max(discount, 35)
        row, _ = FruitDay.objects.get_or_create(product=product, day=start,
            defaults={"simulated_units": demand, "supply": supply, "discount": discount})
        previous = row.simulated_units
        start += timedelta(days=1)
    return FruitDay.objects.get(product=product, day=today)


def quote(product):
    row = ensure_day(product)
    value = (Decimal(str(product.price)) * (100-row.discount) / 100).quantize(Decimal(".01"), rounding=ROUND_HALF_UP)
    return max(Decimal(".01"), value), row.discount


def decorate(product, today=None):
    today = today or timezone.localdate()
    row = ensure_day(product, today)
    start = today - timedelta(days=29)
    totals = FruitDay.objects.filter(product=product, day__range=(start,today)).aggregate(sim=Sum("simulated_units"), manual=Sum("manual_units"))
    actual = OrderItem.objects.filter(product=product, order__status__in=["paid","shipped"],
        **payment_window(start,today)).aggregate(n=Sum("quantity"))["n"] or 0
    product.month_sales = (totals["sim"] or 0) + (totals["manual"] or 0) + actual
    product.sim_sales = totals["sim"] or 0
    product.input_sales = (totals["manual"] or 0) + actual
    product.today_price = (Decimal(str(product.price)) * (100-row.discount) / 100).quantize(Decimal(".01"), rounding=ROUND_HALF_UP)
    product.discount_percent = row.discount
    product.is_season = today.month in product.season_months
    return product
