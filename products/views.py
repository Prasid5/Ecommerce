from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.cache import never_cache
from django.urls import reverse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils.http import urlencode
from django.utils.text import slugify

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Sum, Prefetch

from products.models import Brand, Category, Product, ProductVariant


def is_admin(user):
    return user.is_staff or user.is_superuser


def productdetails(request, slug):
    # Only show active products
    product = Product.objects.filter(slug=slug, is_active=True).first()
    
    if not product:
        messages.error(request, "Product not found or unavailable.")
        return redirect('home')
    
    # Only get active variants that have an associated Stock record
    variants = product.productvariants.filter(
        is_active=True,
        inventorystocks__isnull=False
    ).order_by('id')
    
    context = {
        'product': product,
        'variants': variants,
    }
    return render(request, 'productdetails.html', context)


def backtoproductdetails(request, variant_id):
    # Only show active variants
    variant = ProductVariant.objects.filter(id=variant_id, is_active=True).first()
    if not variant:
        messages.error(request, "Variant not found or unavailable.")
        return redirect('home')

    product = variant.product
    
    # Check if parent product is active
    if not product.is_active:
        messages.error(request, "Product not available.")
        return redirect('home')
    
    # Only get active variants
    variants = product.productvariants.filter(
        is_active=True,
        inventorystocks__isnull=False
    ).order_by('id')

    context = {
        'product': product,
        'variants': variants,
    }
    return render(request, 'productdetails.html', context)


def brand_view(request, brand_slug):
    # Fetch the brand
    brand = get_object_or_404(Brand, slug=brand_slug)

    # Get all categories that include this brand
    # Prefetch only active products for each category
    categories = Category.objects.filter(brands=brand).prefetch_related(
        Prefetch('products', queryset=Product.objects.filter(is_active=True))
    )

    context = {
        'brand': brand,
        'categories': categories,
    }

    return render(request, 'brand.html', context)

def category_view_by_name(request, category_name):
    query = request.GET.get("query", "")
    
    categories = Category.objects.filter(category_name=category_name)
    
    if not categories.exists():
        messages.error(request, "Category not found.")
        return redirect('home')
    
    products = Product.objects.filter(
        category__in=categories,
        is_active=True
    ).select_related('category').prefetch_related('productvariants', 'category__brands').order_by("-id")
    
    if query:
        # Search by product name, brand name, or variant name
        products = products.filter(
            Q(product_name__icontains=query) |
            Q(category__brands__brand_name__icontains=query) |
            Q(productvariants__variant_name__icontains=query)
        ).distinct()
    
    paginator = Paginator(products, 12)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    
    context = {
        'category_name': category_name,
        'page_obj': page_obj,
        'query': query,
    }
    
    return render(request, 'categories.html', context)


def category_view(request, category_slug):
    """
    Original view - shows products from a SPECIFIC category (brand-specific)
    """
    query = request.GET.get("query", "")
    
    category = get_object_or_404(Category, slug=category_slug)
    
    products = category.products.filter(is_active=True).select_related('category').prefetch_related('productvariants', 'category__brands').order_by("-id")
    
    if query:
        # Search by product name, brand name, or variant name
        products = products.filter(
            Q(product_name__icontains=query) |
            Q(category__brands__brand_name__icontains=query) |
            Q(productvariants__variant_name__icontains=query)
        ).distinct()
    
    paginator = Paginator(products, 12)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    
    context = {
        'category': category,
        'category_name': category.category_name,
        'page_obj': page_obj,
        'query': query,
    }
    
    return render(request, 'categories.html', context)

def trending_products(request):
    query = request.GET.get("query", "")

    trending_products = (
        Product.objects
        .filter(is_active=True)
        .annotate(total_orders=Sum('productvariants__orderitem__quantity'))
        .filter(total_orders__gt=0)
        .order_by("-total_orders")
    )

    if query:
        trending_products = trending_products.filter(
            Q(product_name__icontains=query) |
            Q(category__category_name__icontains=query) |
            Q(category__brands__brand_name__icontains=query) |
            Q(productvariants__variant_name__icontains=query),
        )

    paginator = Paginator(trending_products, 12)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(request, 'trendingproducts.html', {
        "page_obj": page_obj,
        "query": query,
    })

@never_cache
@login_required
@user_passes_test(is_admin)
def addbrand(request):
    context = {}
    if request.method == 'POST':
        brand_name = request.POST.get('brand_name', '').strip()
        slug = request.POST.get('slug', '').strip()
        brand_logo = request.FILES.get('brand_logo')
        brand_picture = request.FILES.get('brand_picture')

        context = {
            'brand_name': brand_name,
            'slug': slug,
        }

        # Validate all required fields
        if not brand_name or not slug:
            messages.error(request, "Brand name and slug are required.")
            return render(request, 'addbrand.html', context)
        
        if not brand_logo or not brand_picture:
            messages.error(request, "Brand logo and picture are required.")
            return render(request, 'addbrand.html', context)
        
        if Brand.objects.filter(brand_name=brand_name).exists():
            messages.error(request, "Brand name already exists")
            return render(request, 'addbrand.html', context)
        
        if Brand.objects.filter(slug=slug).exists():
            messages.error(request, "Slug already exists.")
            return render(request, 'addbrand.html', context)

        Brand.objects.create(
            brand_name=brand_name,
            slug=slug,
            brand_logo=brand_logo,
            brand_picture=brand_picture,
        )

        messages.success(request, "Brand created successfully")
        return redirect('addcategory')
    
    return render(request, 'addbrand.html', context)

@never_cache
@login_required
@user_passes_test(is_admin)
def addcategory(request):
    brands = Brand.objects.all()
    context = {'brands': brands}
    
    if request.method == 'POST':
        brand_id = request.POST.get('brand')
        category_name = request.POST.get('category_name', '').strip()
        slug = request.POST.get('slug', '').strip()
        description = request.POST.get('description', '').strip()

        context.update({
            'category_name': category_name,
            'slug': slug,
            'description': description,
            'selected_brand': brand_id,
        })

        # Validate required fields
        if not brand_id:
            messages.error(request, "Please select a brand.")
            return render(request, 'addcategory.html', context)
        
        if not category_name or not description:
            messages.error(request, "All fields are required.")
            return render(request, 'addcategory.html', context)
        
        # Get the brand
        brand = get_object_or_404(Brand, id=brand_id)
        
        # Auto-generate slug with brand name if not provided
        if not slug:
            slug = slugify(f"{brand.brand_name}-{category_name}")
        
        # Check if slug already exists
        if Category.objects.filter(slug=slug).exists():
            messages.error(request, "Slug already exists. Try a different one.")
            return render(request, 'addcategory.html', context)

        # Create category with explicit slug
        category = Category.objects.create(
            category_name=category_name,
            slug=slug,
            description=description
        )
        category.brands.add(brand_id)

        messages.success(request, "Category created successfully")
        return redirect('addproduct')
    
    return render(request, 'addcategory.html', context)

@never_cache
@login_required
@user_passes_test(is_admin)
def addproduct(request):
    # Optimize query to avoid N+1 problem
    categories = Category.objects.prefetch_related('brands').all()
    
    if request.method == 'POST':
        category_id = request.POST.get('category')
        slug = request.POST.get('slug', '').strip()
        product_name = request.POST.get('product_name', '').strip()
        material = request.POST.get('material', '').strip()
        base_price = request.POST.get('base_price', '').strip()
        main_image = request.FILES.get('main_image')
        description = request.POST.get('description')

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
            messages.error(request, "Main image of product is required")
            return render(request, "addproduct.html", context)

        if slug and Product.objects.filter(slug=slug).exists():
            messages.error(request, "Slug already exists")
            return render(request, "addproduct.html", context)

        category = Category.objects.get(id=category_id)

        product = Product.objects.create(
            category=category,
            slug=slug,
            product_name=product_name,
            material=material,
            base_price=base_price,
            description=description,
            main_image=main_image
        )    

        messages.success(request, "Product added successfully")
        return redirect('addproductvariant')
    
    return render(request, 'addproduct.html', {'categories': categories})

@never_cache
@login_required
@user_passes_test(is_admin)
def addproductvariant(request):
    products = Product.objects.all()

    if request.method == 'POST':
        product_id = request.POST.get('product')
        variant_name = request.POST.get('variant_name', '').strip()
        color = request.POST.get('color', '').strip()
        size = request.POST.get('size', '').strip()
        low_stock_threshold = request.POST.get('low_stock_threshold', '').strip()
        sku = request.POST.get('sku', '').strip()

        main_image = request.FILES.get('main_image')
        top_image = request.FILES.get('top_image')
        right_image = request.FILES.get('right_image')
        left_image = request.FILES.get('left_image')
        back_image = request.FILES.get('back_image')

        context = {
            'products': products,
            'variant_name': variant_name,
            'color': color,
            'size': size,
            'low_stock_threshold': low_stock_threshold,
            'sku': sku,
        }

        if not product_id or not color or not size:
            messages.error(request, "Product, Color and Size are required.")
            return render(request, 'addproductvariant.html', context)

        product = Product.objects.get(id=product_id)

        # Auto variant name
        if not variant_name:
            variant_name = f"{product.product_name} - {color}"

        # Auto SKU
        if not sku:
            sku_base = variant_name[:3].upper()
            color_base = color[0:2].upper()
            last_variant = ProductVariant.objects.last()
            next_id = (last_variant.id + 1) if last_variant else 1
            sku = f"{next_id}{sku_base}{color_base}{size}"

            while ProductVariant.objects.filter(sku=sku).exists():
                next_id += 1
                sku = f"{next_id}{sku_base}{color_base}{size}"

        if ProductVariant.objects.filter(sku=sku).exists():
            messages.error(request, "SKU already exists.")
            return render(request, 'addproductvariant.html', context)

        productvariant = ProductVariant.objects.create(
            product=product,
            variant_name=variant_name,
            color=color,
            size=size,
            low_stock_threshold=int(low_stock_threshold or 0),
            sku=sku,
            main_image=main_image,
            top_image=top_image,
            right_image=right_image,
            left_image=left_image,
            back_image=back_image,
        )

        messages.success(request, "Product Variant added successfully")

        url = reverse('addstock')
        params = urlencode({'productvariant_id': productvariant.id})
        return redirect(f"{url}?{params}")

    return render(request, 'addproductvariant.html', {'products': products})

@never_cache
@login_required
@user_passes_test(is_admin)
def brandlist(request):
    query = request.GET.get("query", "")
    brands=Brand.objects.all().order_by("id")#for descending order:-created_at

    if query:
        if query.isdigit():
            brands = brands.filter(Q(id=int(query)) | Q(brand_name__icontains=query))
        else:
            brands = brands.filter(brand_name__icontains=query)
    paginator = Paginator(brands, 5)
    page_number = request.GET.get("page")#for first-time page load, request.get={}
    page_obj = paginator.get_page(page_number)#for None, Paginator.get_page() default to 1. It also contain page object_list from paginator var

    context={
        "page_obj": page_obj,
        "query": query,
    }
    return render(request, "brandlist.html", context)

@never_cache
@login_required
@user_passes_test(is_admin)
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
    paginator = Paginator(categories, 10)
    page_number = request.GET.get("page")#for first-time page load, request.get={}
    page_obj = paginator.get_page(page_number)#for None, Paginator.get_page() default to 1. It also contain page object_list from paginator var

    context={
        "page_obj": page_obj,
        "query": query,
        "brand":brand,
    }
    return render(request, "categorylist.html",context)

@never_cache
@login_required
@user_passes_test(is_admin)
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
    paginator = Paginator(products, 10)
    page_number = request.GET.get("page")#for first-time page load, request.get={}
    page_obj = paginator.get_page(page_number)#for None, Paginator.get_page() default to 1. It also contain page object_list from paginator var

    context={
        "page_obj": page_obj,
        "query": query,
        "category":category
    }
    return render(request, "productlist.html", context)

@never_cache
@login_required
@user_passes_test(is_admin)
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


'''
@login_required
@user_passes_test(is_admin)
def deletebrand(request):
    if request.method == "POST":
        brand_id = request.POST.get("brand_id")
        brand = get_object_or_404(Brand, id=brand_id)

        brand.categories.clear()

        brand.delete()
        messages.success(request, "Brand deleted successfully!")
        return redirect("brandlist")

@login_required
@user_passes_test(is_admin)
def deletecategory(request):
    if request.method == "POST":
        category_id = request.POST.get("category_id")
        category = get_object_or_404(Category, id=category_id)

        category.delete()
        messages.success(request, "Category deleted successfully!")
        return redirect("categorylist")
'''
@never_cache    
@login_required
@user_passes_test(is_admin)
def update_product_status(request):
    if request.method == "POST":
        product_id = request.POST.get("product_id")
        product = get_object_or_404(Product, id=product_id)
        productvariants=ProductVariant.objects.filter(product=product).all()

        if product.is_active:
            productvariants.update(is_active=False)
            product.is_active=False
            product.save()
            messages.success(request, "Product and its variant deactivated successfully.")
            return redirect("productlist")
        else:
            productvariants.update(is_active=True)
            product.is_active=True
            product.save()
            messages.success(request, "Product and its variant activated successfully.")
            return redirect("productlist")


@never_cache
@login_required
@user_passes_test(is_admin)    
def update_productvariant_status(request):
    if request.method == "POST":
        productvariant_id = request.POST.get("productvariant_id")
        productvariant = get_object_or_404(ProductVariant, id=productvariant_id)

        if productvariant.is_active:
            productvariant.is_active=False
            productvariant.save()
            messages.success(request, "Product variant deactivated successfully.")
            return redirect("productvariantlist")
        else:
            productvariant.is_active=True
            productvariant.save()
            messages.success(request, "Product variant activated successfully.")
            return redirect("productvariantlist")
        
@never_cache
@login_required
@user_passes_test(is_admin)
def editbrand(request):
    if request.method == "POST":
        brand_id = request.POST.get("brand_id")
        brand = get_object_or_404(Brand, id=brand_id)

        if "save_changes" in request.POST:
            brand_name = request.POST.get("brand_name", "").strip()
            slug = request.POST.get("slug", "").strip()
            
            # Validation
            if not brand_name or not slug:
                messages.error(request, "Brand name and slug are required.")
                return render(request, "addbrand.html", {
                    "edit_mode": True,
                    "brand": brand,
                    "brand_name": brand_name,
                    "slug": slug,
                })
            
            # Check uniqueness (excluding current brand)
            if Brand.objects.filter(brand_name=brand_name).exclude(id=brand.id).exists():
                messages.error(request, "Brand name already exists")
                return render(request, "addbrand.html", {
                    "edit_mode": True,
                    "brand": brand,
                    "brand_name": brand_name,
                    "slug": slug,
                })
            
            if Brand.objects.filter(slug=slug).exclude(id=brand.id).exists():
                messages.error(request, "Slug already exists")
                return render(request, "addbrand.html", {
                    "edit_mode": True,
                    "brand": brand,
                    "brand_name": brand_name,
                    "slug": slug,
                })
            
            brand.brand_name = brand_name
            brand.slug = slug

            if request.FILES.get("brand_logo"):
                brand.brand_logo = request.FILES["brand_logo"]

            if request.FILES.get("brand_picture"):
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

@never_cache
@login_required
@user_passes_test(is_admin)
def editcategory(request):
    if request.method == "POST":
        category_id = request.POST.get("category_id")
        category = get_object_or_404(Category, id=category_id)

        if "save_changes" in request.POST:
            category_name = request.POST.get("category_name", "").strip()
            slug = request.POST.get("slug", "").strip()
            description = request.POST.get("description", "").strip()
            selected_brand = request.POST.get("brand")

            # Validation
            if not category_name or not description:
                messages.error(request, "Category name and description are required.")
                return render(request, "addcategory.html", {
                    "edit_mode": True,
                    "category": category,
                    "category_name": category_name,
                    "slug": slug,
                    "description": description,
                    "brands": Brand.objects.all(),
                    "selected_brand": selected_brand,
                })
            
            if not selected_brand:
                messages.error(request, "Please select a brand.")
                return render(request, "addcategory.html", {
                    "edit_mode": True,
                    "category": category,
                    "category_name": category_name,
                    "slug": slug,
                    "description": description,
                    "brands": Brand.objects.all(),
                    "selected_brand": selected_brand,
                })
            
            # Get the brand
            brand = get_object_or_404(Brand, id=selected_brand)
            
            # Auto-generate slug with brand name if not provided
            if not slug:
                slug = slugify(f"{brand.brand_name}-{category_name}")
            
            # Check uniqueness (excluding current category)
            if Category.objects.filter(slug=slug).exclude(id=category.id).exists():
                messages.error(request, "Slug already exists. Try a different one.")
                return render(request, "addcategory.html", {
                    "edit_mode": True,
                    "category": category,
                    "category_name": category_name,
                    "slug": slug,
                    "description": description,
                    "brands": Brand.objects.all(),
                    "selected_brand": selected_brand,
                })

            category.category_name = category_name
            category.slug = slug
            category.description = description

            # Update brand M2M
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

@never_cache
@login_required
@user_passes_test(is_admin)
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

            # Handle main image replacement
            if request.FILES.get("main_image"):
                product.main_image = request.FILES["main_image"]

            product.save()
            messages.success(request, "Product updated successfully!")
            return redirect("productlist")

        # First time opening edit page
        return render(request, "addproduct.html", {
            "edit_mode": True,
            "product": product,
            "categories": Category.objects.prefetch_related('brands').all(),
            "name": product.product_name,
            "slug": product.slug,
            "material": product.material,
            "base_price": product.base_price,
            "description": product.description,
        })

    return redirect("productlist")

@never_cache
@login_required
@user_passes_test(is_admin)
def editproductvariant(request):
    if request.method == "POST":
        variant_id = request.POST.get("variant_id")
        variant = get_object_or_404(ProductVariant, id=variant_id)

        if "save_changes" in request.POST:

            variant.variant_name = request.POST.get("variant_name")
            variant.color = request.POST.get("color")
            variant.size = request.POST.get("size")

            new_sku = request.POST.get("sku")
            variant.sku = new_sku if new_sku else variant.sku

            # Update product reference
            product_id = request.POST.get("product")
            if product_id:
                variant.product_id = int(product_id)

            # Replace images
            for field_name in ["main_image", "top_image", "right_image", "left_image", "back_image"]:
                if request.FILES.get(field_name):
                    setattr(variant, field_name, request.FILES[field_name])

            variant.save()
            messages.success(request, "Product Variant updated successfully!")
            return redirect("productvariantlist")

        return render(request, "addproductvariant.html", {
            "edit_mode": True,
            "variant": variant,
            "products": Product.objects.all(),
            "variant_name": variant.variant_name,
            "color": variant.color,
            "size": variant.size,
            "sku": variant.sku,
            "low_stock_threshold": variant.low_stock_threshold,
        })

    return redirect("productvariantlist")

@never_cache
@login_required
@user_passes_test(is_admin)
def top_products(request):
    product_variants = (
        ProductVariant.objects
        .select_related('product', 'product__category')  # Optimize queries
        .annotate(total_orders=Sum("orderitem__quantity"))
        .filter(total_orders__gt=0)
        .order_by("-total_orders")
    )

    paginator = Paginator(product_variants, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(request, "admin_topproducts.html", {"page_obj": page_obj})
# Create your views here.
