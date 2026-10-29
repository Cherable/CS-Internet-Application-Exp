from django.urls import path
from . import views

urlpatterns = [
    path("", views.catalog, name="catalog"),
    path("accounts/register/", views.register, name="register"),
    path("products/<int:pk>/", views.product_detail, name="product_detail"),
    path("cart/", views.cart, name="cart"),
    path("cart/add/<int:pk>/", views.add_to_cart, name="add_to_cart"),
    path("cart/<int:pk>/update/", views.update_cart, name="update_cart"),
    path("cart/<int:pk>/remove/", views.remove_from_cart, name="remove_from_cart"),
    path("checkout/", views.checkout, name="checkout"),
    path("orders/", views.order_list, name="orders"),
    path("orders/<uuid:pk>/", views.order_detail, name="order_detail"),
    path("orders/<uuid:pk>/pay/", views.pay_order, name="pay_order"),
    path("orders/<uuid:pk>/cancel/", views.cancel_order, name="cancel_order"),
    path("sales/", views.sales, name="sales"),
    path("sales/<uuid:pk>/ship/", views.ship_order, name="ship_order"),
]
