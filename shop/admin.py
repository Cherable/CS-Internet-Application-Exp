from django.contrib import admin
from .models import Category, Product

admin.site.site_header = "orangible · 销售管理"
admin.site.site_title = "orangible 管理"

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    search_fields = ["name"]


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ["name", "category", "price", "stock", "is_active"]
    list_filter = ["category", "is_active"]
    search_fields = ["name", "description"]
