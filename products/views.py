from django.shortcuts import render, redirect
from django.contrib import messages
from products.models import Category, Product, ProductVariant

def productdetails(request):
    return render(request, 'productdetails.html')

def categories(request):
    return render(request,'categories.html')

def brands(request):
    return render(request, 'brands.html')

def addcategory(request):
    context={}
    if request.method == 'POST':
        category_name=request.POST.get('category_name','').strip()
        slug=request.POST.get('slug','').strip()
        description=request.POST.get('description','').strip()

        context = {
            'category_name': category_name,
            'slug': slug,
            'description': description
        }

        if not category_name or not slug or not description:
            messages.error(request, "All fields are required.")
            return render(request, 'addcategory.html', context)
        
        if Category.objects.filter(category_name=category_name):
            messages.error(request,"Category name already exists")
            return render(request, 'addcategory.html', context)
        
        if Category.objects.filter(slug=slug):
            messages.error(request,"Slug already exists.")
            return render(request, 'addcategory.html', context)

        category=Category.objects.create(
            category_name=category_name,
            slug=slug,
            description=description
        )

        category.save()
        messages.success(request, "Category created successfully")
        context ={}
        redirect(addcategory)
    return render(request, 'addcategory.html')

def addproduct(request):
    categories =  Category.objects.all()#Used to render all categories in the form
    if request.method == 'POST':
        category_id=request.POST.get('category')
        slug=request.POST.get('slug','').strip()
        name=request.POST.get('name','').strip()
        brand=request.POST.get('brand','').strip()
        material=request.POST.get('material','').strip()
        base_price=request.POST.get('base_price','').strip()
        main_image=request.FILES.get('main_image')
        description=request.POST.get('description')

        context = {
            'categories': categories,
            'slug': slug,
            'name': name,
            'brand': brand,
            'material': material,
            'base_price': base_price,
            'description': description
        }

        if not category_id or not slug or not name or not brand or not material or not base_price or not description:
            messages.error(request, "All fields are required")
            return render(request, 'addproduct.html', context)

        if not main_image:
            messages.error(request,"Main image of product is required")
            return render(request, "addproduct.html", context)

        if Product.objects.filter(slug=slug).exists():
            messages.error(request,"Slug already exits")
            return render(request,"addproduct.html", context)

        category=Category.objects.get(id=category_id)

        product=Product.objects.create(
            category=category,
            slug=slug,
            name=name,
            brand=brand,
            material=material,
            base_price=base_price,
            description=description,
            main_image=main_image
        )    

        messages.success(request, "Product added successfully")
        return redirect('addproductvariant')
    
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
        front_image=request.FILES.get('front_image')
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
             'front_image':front_image,
             'top_image':top_image,
             'right_image':right_image,
             'left_image':left_image,
             'back_image':back_image,
        }

        if not product_id or not variant_name or not color or not size or not stock:
            messages.error(request, "All fields except SKU are required.")
            return render(request, 'addproductvariant.html', context)
        
        if sku and ProductVariant.objects.filter(sku=sku).exists():
            messages.error(request,"SKU already exists")
            return render(request,"addproductvariant.html", context)

        product=Product.objects.get(id=product_id)
        productvariant=ProductVariant.objects.create(
            product=product,
            variant_name=variant_name,
            color=color,
            size=size,
            stock=int(stock),
            sku=sku or None,
            front_image=front_image,
            top_image=top_image,
            right_image=right_image,
            left_image=left_image,
            back_image=back_image,
        )

        messages.success(request, "Product Variant added successfully")
        return redirect('addproductvariant')
    return render(request, 'addproductvariant.html', {'products':products})
# Create your views here.
