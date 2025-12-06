from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from products.models import ProductVariant
from products.views import backtoproductdetails
from users.models import ShippingAddress
from orders.models import Order, OrderItem
from carts.models import Cart, CartItem


@login_required
def buy_now_view(request):
    if request.method == "POST":
        variant_id = request.POST.get("variant_id")
        quantity = int(request.POST.get("quantity", 1))
    elif request.method == "GET":
        # Handle redirects from create_buy_order
        variant_id = request.GET.get("variant_id")
        quantity = int(request.GET.get("quantity", 1))
    else:
        return backtoproductdetails(request, variant_id=None)

    if not variant_id:
        messages.error(request, "No variant selected.")
        return backtoproductdetails(request, variant_id=None)

    variant = ProductVariant.objects.filter(id=variant_id).first()
    if not variant:
        messages.error(request, "Variant not found.")
        return backtoproductdetails(request, variant_id=variant_id)

    available_stock = getattr(variant.inventorystocks, "quantity", 0)
    if quantity > available_stock:
        messages.error(request, "Insufficient stock for this variant.")
        return backtoproductdetails(request, variant_id=variant_id)

    shipping_address = ShippingAddress.objects.filter(user=request.user)

    base_price = variant.product.base_price
    sub_total = base_price * quantity
    shipping_fee = 100 * quantity
    total_amount = sub_total + shipping_fee

    context = {
        "variant": variant,
        "quantity": quantity,
        "base_price": base_price,
        "sub_total": sub_total,
        "shipping_fee": shipping_fee,
        "total_amount": total_amount,
        "shipping_address": shipping_address,
    }

    return render(request, "buynoworder.html", context)


@login_required
def create_buy_order(request):
    if request.method != "POST":
        messages.error(request, "Invalid request method.")
        return redirect("home")

    variant_id = request.POST.get("variant_id")
    shipping_address_id = request.POST.get("shipping_address_id")
    quantity = int(request.POST.get("quantity", 1))

    if not variant_id:
        messages.error(request, "No variant selected.")
        return backtoproductdetails(request, variant_id=None)

    variant = ProductVariant.objects.filter(id=variant_id).first()
    if not variant:
        messages.error(request, "Variant not found.")
        return backtoproductdetails(request, variant_id=variant_id)

    shipping_address = ShippingAddress.objects.filter(
        id=shipping_address_id,
        user=request.user
    ).first()

    if not shipping_address:
        messages.error(request, "Please select a shipping address.")
        # Redirect back to buy_now_view with the same data
        return redirect(f"{reverse('buy_now_view')}?variant_id={variant_id}&quantity={quantity}")

    available_stock = getattr(variant.inventorystocks, "quantity", 0)
    if quantity > available_stock:
        messages.error(request, "Insufficient stock available.")
        return backtoproductdetails(request, variant_id=variant_id)

    base_price = variant.product.base_price
    sub_total = base_price * quantity
    shipping_fee = 100 * quantity
    total_amount = sub_total + shipping_fee

    order = Order.objects.create(
        user=request.user,
        shipping_address=shipping_address,
        subtotal=sub_total,
        shipping_fee=shipping_fee,
        total_amount=total_amount,
        status="pending"
    )

    OrderItem.objects.create(
        order=order,
        variant=variant,
        quantity=quantity,
        price=base_price,
        total_orderitem_amount=sub_total,
    )

    messages.success(request, "Order created! Proceed to payment.")

    return render(request, "payment.html", {"order": order})


@login_required
def order_view(request):
    if request.method == "POST":
        cart_id = request.POST.get("cart_id")
        if not cart_id:
            messages.error(request, "No Cart ID provided.")
            return redirect('cart_view')

        cart = Cart.objects.filter(id=cart_id, user=request.user).first()
        if not cart:
            messages.error(request, "No active cart found.")
            return redirect('cart_view')

        cart_items = cart.items.all()
        if not cart_items.exists():
            messages.error(request, "Your cart is empty.")
            return redirect('cart_view')

        shipping_address = ShippingAddress.objects.filter(user=request.user)
        sub_total= cart.total_cart_amount
        shipping_fee = 100 * cart.total_quantity
        total_amount = sub_total + shipping_fee
        
        return render(request, "order.html", {
            "cart": cart,
            "cart_items": cart_items,
            "sub_total": cart.total_cart_amount,
            "shipping_address": shipping_address,
            "shipping_fee": shipping_fee,
            "total_amount": total_amount,
        })
    else:
        return redirect("cart_view")


@login_required
def create_cart_order(request):
    if request.method == "POST":
        cart_id = request.POST.get("cart_id")
        if not cart_id:
            messages.error(request, "No order items found.")
            return render_order_page(request, cart_id, request.user)
        
        shipping_address_id = request.POST.get("shipping_address_id")
        if not shipping_address_id:
            messages.error(request, "Select shipping address for ordering.")
            return render_order_page(request, cart_id, request.user)

        cart = Cart.objects.filter(id=cart_id, user=request.user).first()
        if not cart:
            messages.error(request, "Cart not found.")
            return render_order_page(request, cart_id, request.user)

        shipping_address = ShippingAddress.objects.filter(
            id=shipping_address_id, 
            user=request.user
        ).first()
        
        if not shipping_address:
            messages.error(request, "Invalid shipping address selected.")
            return render_order_page(request, cart_id, request.user)

        sub_total = cart.total_cart_amount
        shipping_fee = cart.total_quantity * 100
        total_amount = cart.total_cart_amount + shipping_fee

        order = Order.objects.create(
            user=request.user,
            shipping_address=shipping_address,
            subtotal=sub_total,
            shipping_fee=shipping_fee,
            total_amount=total_amount,
            status="pending"
        )

        for item in cart.items.all():
            price_per_unit = item.item_amount / item.quantity if item.quantity > 0 else 0
            total_item_amount = item.item_amount
            
            OrderItem.objects.create(
                order=order,
                variant=item.variant,
                quantity=item.quantity,
                price=price_per_unit,
                total_orderitem_amount=total_item_amount
            )

        messages.success(request, "Order created successfully!")
        return render(request, 'payment.html', {'order': order})

    return redirect("cart_view")
    

def render_order_page(request, cart_id, user):
    if not cart_id:
        cart = Cart.objects.filter(user=user).first()
        if not cart:
            messages.error(request, "No active cart found.")
            return redirect("cart_view")
    else:
        cart = Cart.objects.filter(id=cart_id, user=user).first()
        if not cart:
            messages.error(request, "Cart not found.")
            return redirect("cart_view")
    
    cart_items = cart.items.all()
    if not cart_items.exists():
        messages.error(request, "Your cart is empty.")
        return redirect('cart_view')
    
    shipping_address = ShippingAddress.objects.filter(user=user)
    shipping_fee = 100 * cart.total_quantity
    sub_total=cart.total_cart_amount
    total_amount = cart.total_cart_amount + shipping_fee

    return render(request, "order.html", {
        "cart": cart,
        "cart_items": cart_items,
        "sub_total":sub_total,
        "shipping_address": shipping_address,
        "shipping_fee": shipping_fee,
        "total_amount": total_amount,
    })


def remove_item(request):
    if request.user.is_authenticated:
        cart_id = request.POST.get("cart_id")
        if request.method == "POST":
            item_id = request.POST.get("item_id")
            cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
            cart_item.delete()
            messages.success(request, "Item removed from cart.")
        
        return render_order_page(request, cart_id, request.user)

    return redirect('signin')


@login_required
def order_list(request):
    query = request.GET.get("query", "").strip()
    orders = Order.objects.filter(user=request.user).order_by("-order_date")
    
    if query:
        if query.isdigit():
            # Search by order ID
            orders = orders.filter(id=int(query))
        else:
            # Search by customer name
            orders = orders.filter(
                user__first_name__icontains=query
            ) | orders.filter(
                user__last_name__icontains=query
            )
    
    # Pagination
    from django.core.paginator import Paginator
    paginator = Paginator(orders, 10)  # 10 orders per page
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(request, "orderlist.html", {
        "page_obj": page_obj, 
        "query": query
    })


@login_required
def order_detail(request, order_id):
    order = Order.objects.filter(id=order_id, user=request.user).first()
    if order:
        return render(request, "orderdetaillist.html", {"order": order})
    else:
        return render(request, "orderdetaillist.html")

def shippingaddress(request):
    return render(request, 'shippingaddress.html')