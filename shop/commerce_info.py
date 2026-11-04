import math
import ssl
import certifi
import urllib.request
import xml.etree.ElementTree as ET
from decimal import Decimal, ROUND_HALF_UP
from datetime import timedelta
from django.db import transaction
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import ExchangeSnapshot, Reservation, Product

ECB_URL="https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"

def preorder_quote(product, day=None):
    day = day or timezone.localdate()
    days = max(0,(product.available_on-day).days) if product.available_on else 0
    discount = Decimal(str(20*math.expm1(min(days,30)/14)/math.expm1(30/14))).quantize(Decimal('.01'))
    price=(Decimal(str(product.price))*(100-discount)/100).quantize(Decimal('.01'),rounding=ROUND_HALF_UP)
    return price,discount

@transaction.atomic
def reserve(user, product_id, quantity):
    get_user_model().objects.select_for_update().get(pk=user.pk)
    product=Product.objects.select_for_update().get(pk=product_id,is_active=True)
    if not product.is_upcoming: raise ValueError("该商品当前不在预约期。")
    existing=Reservation.objects.filter(user=user,product=product).first()
    if existing: return existing
    price,discount=preorder_quote(product)
    return Reservation.objects.create(user=user,product=product,quantity=quantity,price=price,discount=discount,available_on=product.available_on)

def fx_payload(refresh=False):
    row,_=ExchangeSnapshot.objects.get_or_create(key="ecb")
    now=timezone.now()
    if refresh and (not row.attempted_at or row.attempted_at < now-timedelta(hours=1)):
        ExchangeSnapshot.objects.filter(pk=row.pk).update(attempted_at=now)
        try:
            request=urllib.request.Request(ECB_URL,headers={"User-Agent":"Mozilla/5.0 (orangible reference rates)"})
            with urllib.request.urlopen(request,timeout=5,context=ssl.create_default_context(cafile=certifi.where())) as response: data=response.read(200000)
            xml=ET.fromstring(data)
            rates={"EUR":"1"};published=None
            for node in xml.iter():
                if "time" in node.attrib: published=node.attrib['time']
                if "currency" in node.attrib: rates[node.attrib['currency']]=str(Decimal(node.attrib['rate']))
            if not published or 'CNY' not in rates: raise ValueError('Incomplete reference feed')
            row.rates=rates;row.published_on=published;row.fetched_at=now;row.failed=False
            row.save(update_fields=['rates','published_on','fetched_at','failed'])
        except Exception:
            ExchangeSnapshot.objects.filter(pk=row.pk).update(failed=True)
        row.refresh_from_db()
    quotes={}
    if row.rates.get('CNY'):
        for currency in ['USD','EUR','THB','IDR','PHP','MYR']:
            if row.rates.get(currency):quotes[currency]=str((Decimal(row.rates['CNY'])/Decimal(row.rates[currency])).quantize(Decimal('.000001')))
    return {'quotes':quotes,'published_on':str(row.published_on) if row.published_on else None,'fetched_at':row.fetched_at.isoformat() if row.fetched_at else None,'cached':row.failed,'available':bool(quotes),'source':ECB_URL}

def decorate_commerce(product):
    product.reservation_price,product.reservation_discount=preorder_quote(product)
    if product.is_upcoming:
        product.month_sales=0
        product.today_price=product.reservation_price
        product.discount_percent=product.reservation_discount
    product.tax_example=(product.current_price*Decimal('.063')).quantize(Decimal('.01'),rounding=ROUND_HALF_UP) if product.overseas else None
    return product
