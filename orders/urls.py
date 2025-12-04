from django.urls import path
from orders import views

urlpatterns = [
    # path('shippingaddress/', views.shippingaddress, name="shippingaddress"),
    path('order/',views.order,name="order"),
    path('orderview/', views.order_view, name="order_view"),
    path('removeitem/', views.remove_item, name='remove_item'),

]
