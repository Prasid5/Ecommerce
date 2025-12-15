from django.shortcuts import redirect, get_object_or_404, render
from django.views.decorators.cache import never_cache
from django.contrib import messages

from .models import Cart, CartItem
from products.models import ProductVariant
from products.views import backtoproductdetails

@never_cache
def cart_view(request):
    if request.user.is_authenticated:
        cart = _get_cart(request)
        cart_items = cart.items.all()  # using related_name
        return render(request, 'cart.html', {
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
    if not request.user.is_authenticated:
        request.session['post_login_action'] = 'add_to_cart'
        request.session['post_login_data'] = {
            'product_slug': request.POST.get('product_slug'),
            'variant_id': request.POST.get('variant_id'),
            'quantity': request.POST.get('quantity', 1),
        }
        return redirect('signin')

    if request.method == "POST":
        product_slug = request.POST.get("product_slug")
        variant_id = request.POST.get("variant_id")
        quantity = int(request.POST.get("quantity", 1))

        variant = get_object_or_404(ProductVariant, id=variant_id)

        # Check stock
        available_stock = getattr(variant.inventorystocks, "quantity", 0)
        
        # If user tries to add more than stock, redirect back
        if quantity > available_stock:
            messages.error(request, f"Insufficient stock available. Only {available_stock} items in stock.")
            return redirect('productdetails', slug=product_slug)

        cart = _get_cart(request)

        # Check if item already exists in cart
        cart_item, created = CartItem.objects.get_or_create(cart=cart, variant=variant)

        if created:
            # New cart item
            if quantity > available_stock:
                messages.error(request, f"Insufficient stock available. Only {available_stock} items in stock.")
                return redirect('productdetails', slug=product_slug)
            cart_item.quantity = quantity
        else:
            # Existing item → check cumulative quantity
            new_quantity = cart_item.quantity + quantity

            if new_quantity > available_stock:
                remaining = available_stock - cart_item.quantity
                if remaining > 0:
                    messages.error(request, f"You already have {cart_item.quantity} in your cart. You can only add {remaining} more (Total stock: {available_stock}).")
                else:
                    messages.error(request, f"You already have {cart_item.quantity} in your cart. No more stock available (Total stock: {available_stock}).")
                return redirect('productdetails', slug=product_slug)

            cart_item.quantity = new_quantity

        cart_item.save()

        messages.success(request, f"Item added to cart successfully! You now have {cart_item.quantity} in your cart.")

    return redirect('cart_view')
