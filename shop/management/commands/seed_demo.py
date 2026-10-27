from django.core.management.base import BaseCommand
from django.db import transaction
from shop.models import Category, Product


class Command(BaseCommand):
    help = "Create sample catalog entries; does not create accounts or overwrite existing products."

    @transaction.atomic
    def handle(self, *args, **options):
        examples = [
            ("学习文具", "点阵学习笔记本", "A5 点阵内页，适合课程笔记与每日计划。", "18.90", 80),
            ("数码配件", "轻巧无线鼠标", "安静按键与便携设计，适合自习和日常办公。", "59.00", 36),
            ("宿舍生活", "简约陶瓷水杯", "350mL 陶瓷杯，让学习间隙多一点温度。", "29.90", 50),
            ("学习文具", "顺滑中性笔套装", "黑色 0.5mm，六支装。", "12.80", 100),
            ("数码配件", "编织 USB-C 数据线", "1 米长度，日常充电与资料传输使用。", "25.00", 45),
            ("宿舍生活", "帆布随行袋", "轻便耐用，装下课本与生活小物。", "32.00", 60),
        ]
        created = 0
        for category_name, name, description, price, stock in examples:
            category, _ = Category.objects.get_or_create(name=category_name)
            _, new = Product.objects.get_or_create(name=name, category=category, defaults={
                "description": description, "price": price, "stock": stock,
            })
            created += new
        self.stdout.write(self.style.SUCCESS(f"Created {created} demo products (no accounts created)."))
