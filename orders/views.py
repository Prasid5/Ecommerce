from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from carts.models import Cart, CartItem
from users.models import ShippingAddress
from django.contrib import messages


@login_required
def order_view(request):
    if request.method == "POST":
        cart_id = request.POST.get("cart_id")
        cart = get_object_or_404(Cart, id=cart_id, user=request.user)
        cart_items = cart.items.all()
        shipping_address = ShippingAddress.objects.filter(user=request.user)
        shipping_fee = 100 * cart.total_quantity
        total_amount = cart.total_cart_amount + shipping_fee
        
        return render(request, "order.html", {
            "cart": cart,
            "cart_items": cart_items,
            "shipping_address": shipping_address,
            "shipping_fee": shipping_fee,
            "total_amount": total_amount,
        })
    else:
        return redirect("cart_view")
    
def remove_item(request):
    if request.user.is_authenticated:
        user=request.user
        cart_id = request.POST.get("cart_id")
        if request.method == "POST":
            item_id = request.POST.get("item_id")
            cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)

            cart_item.delete()
            messages.success(request, "Item removed from cart and order.")
        
        return render_order_page(request, cart_id, user)

    return redirect('signin')

def render_order_page(request, cart_id, user):
    """Helper function to render order.html with all necessary data"""

    if not cart_id:
        cart = Cart.objects.filter(user=user).first()
        if not cart:
            messages.error(request, "No active cart found.")
            return redirect("cart_view")
    else:
        cart = get_object_or_404(Cart, id=cart_id, user=user)
    
    cart_items = cart.items.all()
    shipping_address = ShippingAddress.objects.filter(user=user)
    shipping_fee = 100 * cart.total_quantity
    total_amount = cart.total_cart_amount + shipping_fee

    return render(request, "order.html", {
        "cart": cart,
        "cart_items": cart_items,
        "shipping_address": shipping_address,
        "shipping_fee": shipping_fee,
        "total_amount": total_amount,
    })

def shippingaddress(request):
    return render(request, 'shippingaddress.html')

def order(request):
    return render(request, 'order.html')
