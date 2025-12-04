from django.urls import path
from payments import views

urlpatterns = [
    # path('shippingaddress/', views.shippingaddress, name="shippingaddress"),
    path('payments/',views.payment,name="payments"),
]