from django.urls import path
from . import views, account_views

urlpatterns = [
    path("orders/<uuid:pk>/tracking/", views.order_tracking, name="order_tracking"),
    path("accounts/profile/", account_views.profile, name="profile"),
    path("accounts/captcha.svg", account_views.captcha, name="captcha"),
    path("accounts/phone-code/", account_views.send_code, name="send_phone_code"),
    path("exchange-rates/", views.exchange_rates, name="exchange_rates"),
    path("reservations/", views.reservations, name="reservations"),
    path("products/<int:pk>/reserve/", views.reserve_product, name="reserve_product"),
    path("fruit-market/", views.fruit_snapshot, name="fruit_snapshot"),
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
