from django.conf import settings
from django.conf.urls.static import static
from django.urls import path
from products import views
urlpatterns = [
    path('product/<slug:slug>/', views.productdetails, name='productdetails'),
    path('categories/', views.categories, name="categories"),
    # path('brand/', views.brand, name="brand"),
    path('brand/<slug:brand_slug>/',views.brand_view, name='brand'),
    path('addbrand/', views.addbrand, name="addbrand"),
    path('addcategory/', views.addcategory, name="addcategory"),
    path('addproduct/', views.addproduct, name="addproduct"),
    path('addproductvariant/', views.addproductvariant, name="addproductvariant"),

    path('brandlist/', views.brandlist, name="brandlist"),

    path("categorylist/", views.categorylist, name="categorylist"),
    path("categorylist/<slug:brand_slug>/", views.categorylist, name="categorylist_by_brand"),

    path('productlist/', views.productlist, name="productlist"),
    path("productlist/<slug:category_slug>/", views.productlist, name="productlist_by_category"),


    path("productvariantlist/", views.productvariantlist, name="productvariantlist"),
    path("productvariantlist/<slug:product_slug>/", views.productvariantlist, name="productvariantlist_by_product"),

    path("deletebrand/", views.deletebrand, name="deletebrand"),
    path("deletecategory/", views.deletecategory, name="deletecategory"),
    path("deleteproduct/", views.deleteproduct, name="deleteproduct"),
    path("deleteproductvariant/", views.deleteproductvariant, name="deleteproductvariant"),

    path("editbrand/", views.editbrand, name="editbrand"),
    path("editcategory/", views.editcategory, name="editcategory"),
    path("editproduct/", views.editproduct, name="editproduct"),
    path("editproductvariant/", views.editproductvariant, name="editproductvariant"),


] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
