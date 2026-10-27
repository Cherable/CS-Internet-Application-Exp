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
]
