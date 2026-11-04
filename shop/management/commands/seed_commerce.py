from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from shop.models import Product
class Command(BaseCommand):
    help="Add persistent demo release batches and logistics estimates"
    def handle(self,*args,**options):
        specs={"durian":("THB",24,120,2),"mangosteen":("THB",24,96,3),"avocado":("USD",24,120,4),"rambutan":("THB",24,96,2)}
        for p in Product.objects.exclude(fruit_key=""):
            if p.fruit_key in specs:
                currency,dispatch,transit,taste=specs[p.fruit_key];p.overseas=True;p.source_currency=currency;p.dispatch_hours=dispatch;p.transit_hours=transit;p.tasting_days=taste;p.save(update_fields=['overseas','source_currency','dispatch_hours','transit_hours','tasting_days'])
            elif p.fruit_key in ('banana','papaya','lychee'):p.tasting_days=2;p.save(update_fields=['tasting_days'])
        banana=Product.objects.filter(fruit_key="banana").first()
        if banana:
            Product.objects.get_or_create(fruit_key="banana-overseas", defaults=dict(category=banana.category,name="菲律宾香蕉 · 1kg",price=banana.price,stock=60,image_name=banana.image_name,origin="菲律宾 · 热带种植园",flavor=banana.flavor,growing_story=banana.growing_story,description=banana.description,season_months=list(range(1,13)),overseas=True,source_currency="PHP",dispatch_hours=24,transit_hours=96,tasting_days=3))
        for key,days in [('mango',7),('durian',21),('mangosteen',35)]:
            base=Product.objects.filter(fruit_key=key,sale_kind='regular').first()
            if not base:continue
            Product.objects.get_or_create(fruit_key=key+'-preview',defaults=dict(category=base.category,name=base.name+' · 新季预约',price=base.price,stock=0,image_name=base.image_name,origin=base.origin,flavor=base.flavor,growing_story=base.growing_story,description=base.description,season_months=base.season_months,available_on=timezone.localdate()+timedelta(days=days),overseas=base.overseas,source_currency=base.source_currency,dispatch_hours=base.dispatch_hours,transit_hours=base.transit_hours,tasting_days=base.tasting_days))
        self.stdout.write('Commerce demo metadata ready')
