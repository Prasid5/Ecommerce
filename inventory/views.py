from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.cache import never_cache
from django.utils.http import urlencode
from django.contrib import messages

from django.core.paginator import Paginator
from django.db.models import Q

from products.models import ProductVariant
from inventory.models import Stock, StockTransaction


def is_admin(user):
    return user.is_staff or user.is_superuser

@never_cache
@login_required
@user_passes_test(is_admin)
def stocktracking(request):
    """
    Shows:
    - All variants with their current stock
    """
    query = request.GET.get("query", "")

    product = None
    variants = ProductVariant.objects.all().order_by("-id").prefetch_related('inventorystocks')

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
    return render(request, "stocktracking.html", context)


@never_cache
@login_required
@user_passes_test(is_admin)
def addstock(request):
    if request.method=="POST":
        productvariant_id=productvariant_id = request.GET.get('productvariant_id') or request.POST.get('productvariant_id')
        productvariant=ProductVariant.objects.filter(id=productvariant_id).first()

        if not productvariant:
            messages.error(request, "Product Variant Not Found.")
            return redirect('stocktracking')

        inventorystock = Stock.objects.filter(productvariant=productvariant).first()
        if inventorystock:
            messages.error(request, "Stock already initialized for this Product Variant.")
            return redirect('managestock')

        if "save_changes" in request.POST:
            quantity = request.POST.get('quantity','')
            cost_per_unit=request.POST.get('cost','')
            
            context ={
                'productvariant':productvariant,
                'quantity': quantity,
                'cost_per_unit':cost_per_unit,
            }

            # Validate quantity
            if not quantity.isdigit() or (int(quantity) <= 0):
                messages.error(request, "Stock must be a positive integer")
                return render(request, 'addstock.html', context)
            quantity = int(quantity)

            # Validate cost_per_unit
            try:
                cost_per_unit = float(cost_per_unit)
            except ValueError:
                messages.error(request, "Invalid cost per unit.")
                return render(request, 'addstock.html', context)

            if cost_per_unit <= 0:
                messages.error(request, "Invalid cost per unit.")
                return render(request, 'addstock.html', context)

            total_cost = cost_per_unit * quantity

            inventorystock = Stock.objects.create(
                productvariant=productvariant,
                quantity=quantity,
                cost_per_unit=cost_per_unit,
                total_cost=total_cost,
            )

            StockTransaction.objects.create(
                productvariant=productvariant,
                change=quantity,
                transaction_cost=total_cost,
                reason="Stock Initialized",
            )
            messages.success(request, "Stock added successfully")
            return redirect('stocktracking')

    return render(request, "addstock.html")


@never_cache
@login_required
@user_passes_test(is_admin)
def managestock(request):
    all_variants = ProductVariant.objects.all().prefetch_related('inventorystocks')
    
    if request.method=="POST":
        productvariant_id=request.POST.get('productvariant_id')
        productvariant=ProductVariant.objects.filter(id=productvariant_id).first()
        
        if not productvariant:
            messages.error(request, "Product Variant Not Found.")
            return redirect('stocktracking')
        
        stock = Stock.objects.filter(productvariant=productvariant).first()
        if not stock:
            messages.error(request, "Stock has not been initialized while adding product variant. Please add stock first.")
            url = reverse('addstock')
            params = urlencode({'productvariant_id': productvariant.id})
            return redirect(f"{url}?{params}")

        if "save_changes" in request.POST:
            change = int(request.POST.get('change'))
            reason = request.POST.get('reason','').strip()

            stock = Stock.objects.filter(productvariant=productvariant).first()
            if not stock:
                messages.error(request, "Stock has not been initialized. Please add stock first.")
                return redirect("addstock")
            
            if not change or not reason:
                messages.error(request, "All Field Required.")
                return render(request, 'managestock.html',{'productvariant':productvariant})
           
           # Prevent removing stock if zero
            if stock.quantity == 0 and change < 0:
                messages.error(request, "Cannot remove stock when quantity is zero.")
                return render(request, 'managestock.html',{'productvariant':productvariant})
            
            # Prevent making stock negative
            if change < 0 and stock.quantity + change < 0:
                messages.error(request, "Insufficient stock for removal.")
                return render(request, "managestock.html", {"productvariant": productvariant})

            # ---- STOCK IN ----
            if change > 0:
                stock.quantity += change

                # cost_per_unit remains SAME as stored in Stock model
                transaction_cost = stock.cost_per_unit * change

                # update total_cost value in stock model
                stock.total_cost += transaction_cost

            # ---- STOCK OUT ----
            elif change < 0:
                stock.quantity += change

                # use existing cost_per_unit
                transaction_cost = stock.cost_per_unit * abs(change)

                stock.total_cost -= transaction_cost
            stock.save()

            # Record transaction
            StockTransaction.objects.create(
                productvariant=productvariant,
                change=change,
                transaction_cost=transaction_cost,
                reason=reason,
            )

            messages.success(request, "Stock updated successfully!")
            return redirect("stocktracking")

        return render(request, "managestock.html", {
            "productvariant": productvariant,
        })
    
    return render(request, "managestock.html", {"all_variants": all_variants})


@never_cache
@login_required
@user_passes_test(is_admin)
def stocktransaction(request):
    query = request.GET.get("query", "")
    stock_type = request.GET.get("type", "all")   # 'all', 'in', 'out'

    stocktransaction = StockTransaction.objects.all().order_by("-timestamp")

    # Filter by Stock In / Out
    if stock_type == "in":
        stocktransaction = stocktransaction.filter(change__gt=0)
    elif stock_type == "out":
        stocktransaction = stocktransaction.filter(change__lt=0)

    # Search
    if query:
        if query.isdigit():
            stocktransaction = stocktransaction.filter(
                Q(id=int(query)) |
                Q(productvariant__variant_name__icontains=query)
            )
        else:
            stocktransaction = stocktransaction.filter(
                productvariant__variant_name__icontains=query
            )

    paginator = Paginator(stocktransaction, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj,
        "query": query,
        "stock_type": stock_type,
    }
    return render(request, "stocktransaction.html", context)