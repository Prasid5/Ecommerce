from django.urls import path
from users import views

urlpatterns = [
    path('signup/', views.signup, name="signup"),
    path('signin/', views.signin, name="signin"),
    path('signout/', views.signout, name="signout"),
    path('editprofile/', views.editprofile, name="editprofile"),
    path('addadmin/', views.addadmin, name="addadmin"),
    path('adminlist/', views.userlist,{"mode":"admin"}, name='adminlist'),
    path('customerlist/', views.userlist,{"mode":"customer"}, name="customerlist"),
    path('edituserform/', views.edituserform, name="edituserform"),
    path('edituser/', views.edituser, name="edituser"),
    path('update_user_status/', views.update_user_status, name="update_user_status"),

    path('shippingaddress/', views.shippingaddress, name="shippingaddress"),
    path('shippingaddressorder/', views.shippingaddress_order, name="shippingaddress_order"),


    path("admintopcustomers/", views.top_customers, name="admin_top_customers"),

]
