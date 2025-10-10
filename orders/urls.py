from django.urls import path
from orders import views

urlpatterns = [
    path('shippingaddress/', views.shippingaddress, name="shippingaddress"),
]
