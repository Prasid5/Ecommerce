from django.shortcuts import redirect, get_object_or_404, render
from .models import Cart, CartItem
from products.models import ProductVariant
from django.contrib.auth.decorators import login_required
from django.contrib import messages

def cart_view(request):
    if request.user.is_authenticated:
        cart = _get_cart(request)
        cart_items = cart.items.all()  # using related_name
        return render(request, 'order.html', {
            'cart': cart,
            'cart_items': cart_items,
        })
    else:
        return redirect('signin')

def _get_cart(request):
    cart, _ = Cart.objects.get_or_create(user=request.user)
    return cart

def remove_from_cart(request):
    if request.user.is_authenticated:
        if request.method == "POST":
            item_id = request.POST.get("item_id")
            cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)

            cart_item.delete()
            messages.success(request, "Item removed from cart.")
        
        return redirect('cart_view')

    return redirect('signin')

def add_to_cart(request):
    if request.user.is_authenticated:
        if request.method == "POST":
            variant_id = request.POST.get("variant_id")
            quantity = int(request.POST.get("quantity", 1))
            
            
            variant = get_object_or_404(ProductVariant, id=variant_id)        
            cart = _get_cart(request)

            cart_item, created = CartItem.objects.get_or_create(cart=cart, variant=variant)

            if created:
                cart_item.quantity = quantity
            else:
                cart_item.quantity += quantity
            
            cart_item.save()
        
        return redirect('cart_view')
    else:
        return redirect('signin')



