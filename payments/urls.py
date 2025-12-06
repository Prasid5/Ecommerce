from django.urls import path
from payments import views

urlpatterns = [
    path('makepayment/', views.make_payment, name='make_payment'),
    path('payment-success/', views.esewa_payment_success, name='esewa_success'),
    path('payment-failure/', views.esewa_payment_failure, name='esewa_failure'),
    path('orders/<int:order_id>/cancel/', views.cancel_order, name='cancel_order'),

# Correct URL patterns for invoice functionality
path('orders/<int:order_id>/invoice/download/', views.download_invoice, name='download_invoice'),
path('orders/<int:order_id>/invoice/view/', views.view_invoice, name='view_invoice'),
]