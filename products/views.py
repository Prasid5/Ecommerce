from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
import os

from products.models import Brand, Category, Product, ProductVariant

def productdetails(request, slug):
    """
    Fetch product by slug
    """
    product = get_object_or_404(Product, slug=slug)

    context = {
        'product': product
    }
    return render(request, 'productdetails.html', context)


def categories(request):
    return render(request,'categories.html')

# def brand(request):
#     return render(request, 'brand.html')

from django.shortcuts import render, get_object_or_404
from .models import Brand, Category

def brand_view(request, brand_slug):
    # Fetch the brand
    brand = get_object_or_404(Brand, slug=brand_slug)

    # Get all categories that include this brand
    categories = Category.objects.filter(brands=brand).prefetch_related('products')

    context = {
        'brand': brand,
        'categories': categories,
    }

    return render(request, 'brand.html', context)


def addbrand(request):
    context={}
    if request.method == 'POST':
        brand_name=request.POST.get('brand_name','').strip()
        slug=request.POST.get('slug','').strip()
        brand_logo=request.FILES.get('brand_logo')
        brand_picture=request.FILES.get('brand_picture')

        context = {
            'brand_name': brand_name,
            'slug': slug,
        }

        if not brand_name:
            messages.error(request, "All fields are required.")
            return render(request, 'addbrand.html', context)
        
        if Brand.objects.filter(brand_name=brand_name):
            messages.error(request,"Brand name already exists")
            return render(request, 'addbrand.html', context)
        
        if Brand.objects.filter(slug=slug):
            messages.error(request,"Slug already exists.")
            return render(request, 'addbrand.html', context)

        brand=Brand.objects.create(
            brand_name=brand_name,
            slug=slug,
            brand_logo=brand_logo,
            brand_picture=brand_picture,
        )

        brand.save()
        messages.success(request, "Brand created successfully")

        brands=Brand.objects.all()
        context ={
            'brands':brands
        }
        return render(request,'addcategory.html',context)
    return render(request, 'addbrand.html')

def addcategory(request):
    brands=Brand.objects.all()
    context={}
    if request.method == 'POST':
        brand_id=request.POST.get('brand')
        category_name=request.POST.get('category_name','').strip()
        slug=request.POST.get('slug','').strip()
        description=request.POST.get('description','').strip()

        context = {
            'brands':brands,
            'category_name': category_name,
            'slug': slug,
            'description': description
        }

        if not category_name or not description:
            messages.error(request, "All fields are required.")
            return render(request, 'addcategory.html', context)
        
        if Category.objects.filter(category_name=category_name):
            messages.error(request,"Category name already exists")
            return render(request, 'addcategory.html', context)
        
        if Category.objects.filter(slug=slug):
            messages.error(request,"Slug already exists.")
            return render(request, 'addcategory.html', context)

        # Step 1: create category WITHOUT brands
        category = Category.objects.create(
            category_name=category_name,
            slug=slug,
            description=description
        )

        # Step 2: add brand to ManyToMany field
        category.brands.add(brand_id)

        category.save()
        messages.success(request, "Category created successfully")
        categories =  Category.objects.all()
        context ={
            'categories':categories
        }
        return render(request, 'addproduct.html', context)
    return render(request, 'addcategory.html',{'brands':brands})

def addproduct(request):
    categories =  Category.objects.all()#Used to render all categories in the form
    if request.method == 'POST':
        category_id=request.POST.get('category')
        slug=request.POST.get('slug','').strip()
        product_name=request.POST.get('product_name','').strip()
        material=request.POST.get('material','').strip()
        base_price=request.POST.get('base_price','').strip()
        main_image=request.FILES.get('main_image')
        description=request.POST.get('description')

        context = {
            'categories': categories,
            'slug': slug,
            'product_name': product_name,
            'material': material,
            'base_price': base_price,
            'description': description
        }

        if not category_id or not product_name or not material or not base_price or not description:
            messages.error(request, "All fields are required")
            return render(request, 'addproduct.html', context)

        if not base_price.replace('.', '', 1).isdigit() or float(base_price) <= 0:
            messages.error(request, "Base Price must be positive")
            return render(request, "addproduct.html", context)

        if not main_image:
            messages.error(request,"Main image of product is required")
            return render(request, "addproduct.html", context)

        if slug and Product.objects.filter(slug=slug).exists():
            messages.error(request,"Slug already exits")
            return render(request,"addproduct.html", context)

        category=Category.objects.get(id=category_id)

        product=Product.objects.create(
            category=category,
            slug=slug,
            product_name=product_name,
            material=material,
            base_price=base_price,
            description=description,
            main_image=main_image
        )    

        messages.success(request, "Product added successfully")
        products=Product.objects.all()
        context={
            'products':products
        }
        return render(request, 'addproductvariant.html', context)
    
    return render(request,'addproduct.html',{'categories':categories})

def addproductvariant(request):
    products=Product.objects.all()
    if request.method == 'POST':
        product_id=request.POST.get('product')
        variant_name=request.POST.get('variant_name','').strip()
        color=request.POST.get('color','').strip()
        size=request.POST.get('size','').strip()
        stock=request.POST.get('stock','').strip()
        sku=request.POST.get('sku','').strip()
        top_image=request.FILES.get('top_image')
        right_image=request.FILES.get('right_image')
        left_image=request.FILES.get('left_image')
        back_image=request.FILES.get('back_image')

        context={
             'products':products,
             'variant_name':variant_name,
             'color':color,
             'size':size,
             'stock':stock,
             'sku':sku,
        }

        if not product_id or not variant_name or not color or not size or not stock:
            messages.error(request, "All fields except SKU are required.")
            return render(request, 'addproductvariant.html', context)
        
        if not sku:
            sku_base=variant_name[:3].upper() if len(variant_name)>=3 else variant_name.upper()
            last_variant=ProductVariant.objects.last()
            next_id=last_variant.id+1 if last_variant else 1
            sku=f"{next_id}{sku_base}"

            while ProductVariant.objects.filter(sku=sku).exists():
                next_id += 1
                sku = f"{next_id}{sku_base}"

        if sku and ProductVariant.objects.filter(sku=sku).exists():
            messages.error(request,"SKU already exists")
            return render(request,"addproductvariant.html", context)
        
        if not stock.isdigit() or int(stock)<=0:
            messages.error(request,"Stock must be a positive integer")
            return render(request, 'addproductvariant.html', context)

        product=Product.objects.get(id=product_id)
        productvariant=ProductVariant.objects.create(
            product=product,
            variant_name=variant_name,
            color=color,
            size=size,
            stock=int(stock),
            sku=sku,
            top_image=top_image,
            right_image=right_image,
            left_image=left_image,
            back_image=back_image,
        )

        messages.success(request, "Product Variant added successfully")
        return redirect('productlist')
    return render(request, 'addproductvariant.html', {'products':products})


def brandlist(request):
    query = request.GET.get("query", "")
    brands=Brand.objects.all().order_by("id")#for descending order:-created_at

    if query:
        if query.isdigit():
            brands = brands.filter(Q(id=int(query)) | Q(brand_name__icontains=query))
        else:
            brands = brands.filter(brand_name__icontains=query)
    paginator = Paginator(brands, 1)
    page_number = request.GET.get("page")#for first-time page load, request.get={}
    page_obj = paginator.get_page(page_number)#for None, Paginator.get_page() default to 1. It also contain page object_list from paginator var

    context={
        "page_obj": page_obj,
        "query": query,
    }
    return render(request, "brandlist.html", context)


def categorylist(request, brand_slug=None):
    query = request.GET.get("query", "")

    if brand_slug:
        brand = get_object_or_404(Brand, slug=brand_slug)
        categories = brand.categories.all().order_by("id")
    else:
        brand=None 
        categories=Category.objects.all().order_by("id")

    if query:
        if query.isdigit():
            categories = categories.filter(Q(id=int(query)) | Q(category_name__icontains=query))
        else:
            categories = categories.filter(category_name__icontains=query)
    paginator = Paginator(categories, 1)
    page_number = request.GET.get("page")#for first-time page load, request.get={}
    page_obj = paginator.get_page(page_number)#for None, Paginator.get_page() default to 1. It also contain page object_list from paginator var

    context={
        "page_obj": page_obj,
        "query": query,
        "brand":brand,
    }
    return render(request, "categorylist.html",context)


def productlist(request, category_slug=None):
    query = request.GET.get("query", "")

    if category_slug:
        category=get_object_or_404(Category, slug=category_slug)
        products=category.products.all().order_by("id")
    else:
        category=None
        products=Product.objects.all().order_by("-created_at")#for descending order:-created_at

    if query:
        if query.isdigit():
            products = products.filter(Q(id=int(query)) | Q(product_name__icontains=query))
        else:
            products = products.filter(product_name__icontains=query)
    paginator = Paginator(products, 1)
    page_number = request.GET.get("page")#for first-time page load, request.get={}
    page_obj = paginator.get_page(page_number)#for None, Paginator.get_page() default to 1. It also contain page object_list from paginator var

    context={
        "page_obj": page_obj,
        "query": query,
        "category":category
    }
    return render(request, "productlist.html", context)


def productvariantlist(request, product_slug=None):
    """
    Shows:
    - All variants (if no product_slug)
    - Only variants of a specific product (if product_slug given)
    """

    query = request.GET.get("query", "")

    if product_slug:
        product = get_object_or_404(Product, slug=product_slug)
        variants = product.productvariants.all().order_by("-id")
    else:
        product = None
        variants = ProductVariant.objects.all().order_by("-id")

    # Search logic
    if query:
        variants = variants.filter(variant_name__icontains=query)

    paginator = Paginator(variants, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj,
        "query": query,
        "product": product,
    }
    return render(request, "productvariantlist.html", context)


def deletebrand(request):
    if request.method == "POST":
        brand_id = request.POST.get("brand_id")
        brand = get_object_or_404(Brand, id=brand_id)

        brand.categories.clear()
        if brand.brand_logo:
            if os.path.isfile(brand.brand_logo.path):
                os.remove(brand.brand_logo.path)

        if brand.brand_picture:
            if os.path.isfile(brand.brand_picture.path):
                os.remove(brand.brand_picture.path)

        brand.delete()
        messages.success(request, "Brand deleted successfully!")
        return redirect("brandlist")
    
def deletecategory(request):
    if request.method == "POST":
        category_id = request.POST.get("category_id")
        category = get_object_or_404(Category, id=category_id)

        category.delete()
        messages.success(request, "Category deleted successfully!")
        return redirect("categorylist")

def deleteproduct(request):
    if request.method == "POST":
        product_id = request.POST.get("product_id")
        product = get_object_or_404(Product, id=product_id)

        if product.main_image:
            if os.path.isfile(product.main_image.path):
                os.remove(product.main_image.path)

        for productvariant in product.productvariants.all():
            for img_field in ["top_image", "right_image", "left_image", "back_image"]:
                img = getattr(productvariant, img_field)
                if img:
                    if os.path.isfile(img.path):
                        os.remove(img.path)

        product.delete()
        messages.success(request, "Product and its variants deleted successfully!")
        return redirect("productlist")
    
def deleteproductvariant(request):
    if request.method == "POST":
        productvariant_id = request.POST.get("productvariant_id")
        productvariant = get_object_or_404(ProductVariant, id=productvariant_id)

        # Remove variant images
        for img_field in ["top_image", "right_image", "left_image", "back_image"]:
            img = getattr(productvariant, img_field)
            if img:
                if os.path.isfile(img.path):
                    os.remove(img.path)

        productvariant.delete()
        messages.success(request, "Product variant deleted successfully!")
        return redirect("productvariantlist")

def editbrand(request):
    if request.method == "POST":
        brand_id = request.POST.get("brand_id")
        brand = get_object_or_404(Brand, id=brand_id)

        if "save_changes" in request.POST:
            brand.brand_name = request.POST.get("brand_name")
            brand.slug = request.POST.get("slug")

            if request.FILES.get("brand_logo"):
                if brand.brand_logo and os.path.isfile(brand.brand_logo.path):
                    os.remove(brand.brand_logo.path)
                brand.brand_logo = request.FILES["brand_logo"]

            if request.FILES.get("brand_picture"):
                if brand.brand_picture and os.path.isfile(brand.brand_picture.path):
                    os.remove(brand.brand_picture.path)
                brand.brand_picture = request.FILES["brand_picture"]

            brand.save()
            messages.success(request, "Brand updated successfully!")
            return redirect("brandlist")

        # First time opening edit page
        return render(request, "addbrand.html", {
            "edit_mode": True,
            "brand": brand,
            "brand_name": brand.brand_name,
            "slug": brand.slug,
        })

    return redirect("brandlist")


def editcategory(request):
    if request.method == "POST":
        category_id = request.POST.get("category_id")
        category = get_object_or_404(Category, id=category_id)

        if "save_changes" in request.POST:
            category.category_name = request.POST.get("category_name")
            category.slug = request.POST.get("slug")
            category.description = request.POST.get("description")

            # Updating the brand M2M
            selected_brand = request.POST.get("brand")
            if selected_brand:
                category.brands.set([selected_brand])

            category.save()
            messages.success(request, "Category updated successfully!")
            return redirect("categorylist")

        # Render edit form
        return render(request, "addcategory.html", {
            "edit_mode": True,
            "category": category,
            "category_name": category.category_name,
            "slug": category.slug,
            "description": category.description,
            "brands": Brand.objects.all(),
            "selected_brand": category.brands.first().id if category.brands.exists() else None
        })

    return redirect("categorylist")

def editproduct(request):
    if request.method == "POST":
        product_id = request.POST.get("product_id")
        product = get_object_or_404(Product, id=product_id)

        if "save_changes" in request.POST:
            # Update text fields
            product.product_name = request.POST.get("product_name")
            product.description = request.POST.get("description")
            product.material = request.POST.get("material")
            product.base_price = request.POST.get("base_price")
            product.slug = request.POST.get("slug")

            # Update category if changed
            category_id = request.POST.get("category")
            if category_id:
                product.category_id = category_id

            # ---------------------------
            # Handle main image replacement
            # ---------------------------
            if request.FILES.get("main_image"):
                # Delete old image file
                if product.main_image and os.path.isfile(product.main_image.path):
                    os.remove(product.main_image.path)
                # Assign new image
                product.main_image = request.FILES["main_image"]

            product.save()
            messages.success(request, "Product updated successfully!")
            return redirect("productlist")

        # First time opening edit page
        return render(request, "addproduct.html", {
            "edit_mode": True,
            "product": product,
            "categories": Category.objects.all(),
            "name": product.product_name,
            "slug": product.slug,
            "material": product.material,
            "base_price": product.base_price,
            "description": product.description,
        })

    return redirect("productlist")

import os
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import ProductVariant, Product

def editproductvariant(request):
    if request.method == "POST":
        variant_id = request.POST.get("variant_id")
        variant = get_object_or_404(ProductVariant, id=variant_id)

        if "save_changes" in request.POST:
            # Update text fields
            variant.variant_name = request.POST.get("variant_name")
            variant.color = request.POST.get("color")
            variant.size = request.POST.get("size")
            variant.stock = request.POST.get("stock") or 0
            variant.sku = request.POST.get("sku") or f"SKU-{variant.id}"

            # Update linked product if changed
            product_id = request.POST.get("product")
            if product_id:
                variant.product_id = int(product_id)

            # ---------------------------
            # Handle image replacements
            # ---------------------------
            for field_name in ["top_image", "right_image", "left_image", "back_image"]:
                if request.FILES.get(field_name):
                    old_file = getattr(variant, field_name)
                    if old_file and os.path.isfile(old_file.path):
                        os.remove(old_file.path)
                    setattr(variant, field_name, request.FILES[field_name])

            variant.save()
            messages.success(request, "Product Variant updated successfully!")
            return redirect("productvariantlist")

        # First time opening edit page
        return render(request, "addproductvariant.html", {
            "edit_mode": True,
            "variant": variant,
            "products": Product.objects.all(),
            "variant_name": variant.variant_name,
            "color": variant.color,
            "size": variant.size,
            "stock": variant.stock,
            "sku": variant.sku,
        })

    return redirect("productvariantlist")

# Create your views here.
