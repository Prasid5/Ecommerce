from django.urls import path
from orders import views

urlpatterns = [
    
    path('orderview/', views.order_view, name="order_view"),
    path('createcartorder/', views.create_cart_order, name="create_cart_order"),


    path('buynowview/', views.buy_now_view, name="buy_now_view"),
    path('createbuyorder/', views.create_buy_order, name="create_buy_order"),


    path('removeitem/', views.remove_item, name='remove_item'),


    path('orderlist/', views.order_list, name='order_list'),
    path('orderdetail/<int:order_id>/', views.order_detail, name='order_detail'),
    path('cancelorder/<int:order_id>/cancel/', views.cancel_order, name='cancel_order'),
    path('markorderreceived/<int:order_id>', views.mark_order_received, name='mark_order_received'),


    path('adminorderlist/', views.admin_order_list, name='admin_order_list'),
    path('adminorderdetail/<int:order_id>/', views.admin_order_detail, name='admin_order_detail'),
    path('admincancelorder/<int:order_id>/cancel/', views.admin_cancel_order, name='admin_cancel_order'),
    path('adminupdateorder/<int:order_id>/update-status/', views.admin_update_order_status, name='admin_update_order_status'),


    path('adminmonthlyreport/', views.monthly_report, name='admin_monthly_report'),
    

    # path('admintopproducts/', views.top_products, name='admin_topproducts'),
]
