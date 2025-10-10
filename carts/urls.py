from django.urls import path
from carts import views

urlpatterns = [
    path('cart/',views.cart, name="cart")
]
