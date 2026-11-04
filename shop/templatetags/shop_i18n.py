from django import template
from shop.localization import translate
register=template.Library()
register.simple_tag(translate,name='tr')
register.filter('tr',translate)
