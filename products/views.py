from django.shortcuts import render, redirect
from django.contrib import messages
from products.models import Category

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
# Create your views here.
