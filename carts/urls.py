from django.urls import path
from carts import views

urlpatterns = [
    path('add-to-cart/', views.add_to_cart, name='add_to_cart'),
    path('cart/', views.cart_view, name='cart_view'),
    path('removecartitem/', views.remove_from_cart, name='remove_from_cart'),
]
