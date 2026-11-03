from django.core.management.base import BaseCommand
from shop.models import Product
from shop.fruit_market import ensure_day
class Command(BaseCommand):
    help = "Generate missing daily fruit simulation rows without rewriting existing data"
    def handle(self, *args, **options):
        count=0
        for p in Product.objects.filter(is_active=True).exclude(fruit_key=""):
            ensure_day(p); count+=1
        self.stdout.write(f"Updated {count} fruits")
