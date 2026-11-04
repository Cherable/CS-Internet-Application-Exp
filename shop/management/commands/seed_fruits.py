from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from shop.models import Category, Product
from shop.fruit_market import ensure_day
from shop.extra_fruits import EXTRA_FRUITS
class Command(BaseCommand):
    help="Seed tropical fruit catalog; retire old goods without deleting orders"
    def handle(self,*args,**options):
        category,_=Category.objects.get_or_create(name="热带果实")
        Product.objects.filter(fruit_key="").update(is_active=False)
        fruits=[('mango', '阳光金芒 · 1kg', '39.90', '海南 · 热带果园', '浓郁花香 / 蜂蜜甜感 / 柔软多汁', '在温暖的季风中生长，待果肩饱满后采收，经分级、缓冲包装与运输，呈现不同熟度的风味。', [3, 4, 5, 6, 7]), ('pineapple', '金芯菠萝 · 1颗', '29.90', '海南 · 丘陵果园', '清亮酸甜 / 丰盈汁水 / 热带香气', '贴近地面的莲座叶承接日光，果实逐渐膨大。采收后按外观与成熟度分级，保留清爽的酸甜层次。', [3, 4, 5, 6, 7]), ('papaya', '日落木瓜 · 2颗', '35.90', '云南 · 热带河谷', '绵密果肉 / 轻盈乳香 / 柔和甜味', '温暖河谷孕育橙红果肉，按转色程度采收并分级。成熟后切开去籽，冷藏后口感更清润。', [8, 9, 10, 11, 12]), ('dragon', '绯红火龙果 · 1kg', '32.90', '广西 · 热带果园', '淡雅果香 / 清甜水润 / 细籽轻脆', '夜间开花后果实逐渐转色，依据果皮与鳞片状态安排采收，轻拿轻放，保持果皮完整。', [6, 7, 8, 9, 10, 11]), ('coconut', '海风椰子 · 2颗', '39.90', '海南 · 海岸椰林', '清冽椰水 / 淡淡坚果香 / 细嫩椰肉', '椰树适应温暖海岸气候，按食用需求选择采收成熟度，经清理与分级，保留椰水的自然清爽。', [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]), ('passion', '山谷百香果 · 500g', '26.90', '云南 · 热带山谷', '浓烈花果香 / 明快酸度 / 回甘悠长', '藤蔓间的花朵结成果实，转色成熟后采收分选。果壳逐渐起皱时，香气也更为集中。', [7, 8, 9, 10, 11])]
        for key,name,price,origin,flavor,story,months in fruits:
            p,created=Product.objects.get_or_create(fruit_key=key,sale_kind="regular",defaults=dict(category=category,name=name,price=price,stock=160,origin=origin,flavor=flavor,growing_story=story,season_months=months,image_name=key+".jpg",description=flavor+" · 精选分享装"))
            if key in ("coconut", "pineapple") and p.image_name in (key+".jpg", key+"-full.jpg"):
                p.image_name = "pineapple-whole.jpg" if key == "pineapple" else "coconut-full.jpg"
                p.save(update_fields=["image_name"])
            ensure_day(p)
        for key,kind in [("papaya","ready"),("mango","clearance")]:
            base=Product.objects.get(fruit_key=key,sale_kind="regular")
            p,_=Product.objects.get_or_create(fruit_key=key,sale_kind=kind,defaults=dict(category=category,name=base.name+(" · 即食熟度" if kind=="ready" else " · 临期分享"),price=base.price,stock=32,origin=base.origin,flavor=base.flavor,growing_story=base.growing_story,season_months=base.season_months,image_name=base.image_name,description="成熟批次，建议收到后尽快食用",best_before=timezone.localdate()+timedelta(days=2 if kind=="clearance" else 4)))
            ensure_day(p)
        for key,name,price,origin,flavor,story,months,stock in EXTRA_FRUITS:
            p,_=Product.objects.get_or_create(fruit_key=key,sale_kind="regular",defaults=dict(category=category,name=name,price=price,stock=stock,origin=origin,flavor=flavor,growing_story=story,season_months=months,image_name=key+".jpg",description=flavor+" · 热带果园精选"))
            ensure_day(p)
        self.stdout.write("Fruit catalog ready; existing fruit records preserved")
