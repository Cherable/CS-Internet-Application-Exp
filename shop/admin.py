from django.contrib import admin
from .models import Category, Product, Order, OrderItem, ShipmentEmail
from .order_services import ship, OrderError

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


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    can_delete = False
    readonly_fields = ["product", "name", "price", "quantity"]

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "total", "status", "created_at"]
    list_filter = ["status", "created_at"]
    search_fields = ["recipient", "user__username", "email"]
    readonly_fields = [field.name for field in Order._meta.fields]
    inlines = [OrderItemInline]
    actions = ["ship_selected"]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.action(description="发货并创建通知邮件任务", permissions=["change"])
    def ship_selected(self, request, queryset):
        for order in queryset:
            try:
                ship(order.pk)
            except OrderError as exc:
                self.message_user(request, str(exc), level="ERROR")


@admin.register(ShipmentEmail)
class ShipmentEmailAdmin(admin.ModelAdmin):
    list_display = ["order", "status", "attempts", "last_error", "processed_at"]
    readonly_fields = [field.name for field in ShipmentEmail._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
