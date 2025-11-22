from django.conf import settings
from django.conf.urls.static import static
from django.urls import path
from products import views
urlpatterns = [
    path('product/<int:product_id>/', views.productdetails, name='productdetails'),
    path('categories/', views.categories, name="categories"),
    path('brands/', views.brands, name="brands"),
    path('addcategory/', views.addcategory, name="addcategory"),
    path('addproduct/', views.addproduct, name="addproduct"),
    path('addproductvariant/', views.addproductvariant, name="addproductvariant"),
    path('productlist/', views.productlist, name="productlist")
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
