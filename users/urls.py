from django.urls import path
from users import views

urlpatterns = [
    path('signup/', views.signup, name="signup"),
    path('signin/', views.signin, name="signin"),
    path('signout/', views.signout, name="signout"),
    path('addadmin/', views.addadmin, name="addadmin"),
    path('adminlist/', views.userlist,{"mode":"admin"}, name='adminlist'),
    path('customerlist/', views.userlist,{"mode":"customer"}, name="customerlist"),
    path('edituserform/', views.edituserform, name="edituserform"),
    path('edituser/', views.edituser, name="edituser"),
    path('deleteuser/', views.deleteuser, name="deleteuser"),
]
