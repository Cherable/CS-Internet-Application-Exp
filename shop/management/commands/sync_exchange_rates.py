from django.core.management.base import BaseCommand
from shop.commerce_info import fx_payload
from shop.models import ExchangeSnapshot
class Command(BaseCommand):
    help="Fetch the latest published ECB reference rates with verified TLS"
    def add_arguments(self,parser):parser.add_argument('--force',action='store_true')
    def handle(self,*args,**options):
        if options['force']:ExchangeSnapshot.objects.filter(key='ecb').update(attempted_at=None)
        data=fx_payload(refresh=True)
        self.stdout.write(str(data))
