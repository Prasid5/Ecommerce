from django.urls import path
from orders import views

urlpatterns = [
    # path('shippingaddress/', views.shippingaddress, name="shippingaddress"),
    path('orderview/', views.order_view, name="order_view"),
    path('removeitem/', views.remove_item, name='remove_item'),
    path('buynowview/', views.buy_now_view, name="buy_now_view"),

    path('createcartorder/', views.create_cart_order, name="create_cart_order"),
    path('createbuyorder/', views.create_buy_order, name="create_buy_order"),

    path('orderlist/', views.order_list, name='order_list'),
    path('orders/<int:order_id>/', views.order_detail, name='order_detail'),


]
