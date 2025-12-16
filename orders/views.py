from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.cache import never_cache
from django.contrib import messages

from django.db.models import Q, Sum, Count, Avg
from datetime import datetime
from django.db.models.functions import TruncMonth
from django.core.paginator import Paginator

from products.models import Product, ProductVariant
from inventory.models import Stock, StockTransaction
from users.models import ShippingAddress
from orders.models import Order, OrderItem
from carts.models import Cart, CartItem
from products.views import backtoproductdetails


def is_admin(user):
    return user.is_staff or user.is_superuser


def buy_now_view(request):
    if request.method == "POST" and not request.user.is_authenticated:
        request.session['post_login_action'] = 'buy_now'
        request.session['post_login_data'] = {
            'variant_id': request.POST.get('variant_id'),
            'quantity': request.POST.get('quantity', 1),
        }
        return redirect('signin')
    if request.method == "POST":
        variant_id = request.POST.get("variant_id")
        quantity = int(request.POST.get("quantity", 1))
    elif request.method == "GET":
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


@login_required
@never_cache
def cancel_order(request, order_id):
    """Handle order cancellation by customer"""
    if request.method == "POST":
        # Get the order for the current user
        order = get_object_or_404(Order, id=order_id, user=request.user)
        
        # Get the payment record
        payment = order.payments.first()
        
        if not payment:
            messages.error(request, "Payment information not found for this order.")
            return redirect('order_list')
        
        # ───────── ESEWA PAYMENT - CANNOT CANCEL ─────────
        if payment.payment_method == "esewa":
            messages.error(request, "Orders paid through eSewa cannot be cancelled. Please contact support for refund requests.")
            return redirect('order_list')
        
        # ───────── CASH ON DELIVERY - CONDITIONAL CANCELLATION ─────────
        if payment.payment_method == "cod":
            # Check if order is in a cancellable status
            non_cancellable_statuses = ["processing", "shipped", "delivered"]
            
            if order.status in non_cancellable_statuses:
                messages.error(request, f"Cannot cancel order. Order is already {order.status}.")
                return redirect('order_list')
            
            # Check if order is already cancelled
            if order.status == "cancelled":
                messages.info(request, "This order is already cancelled.")
                return redirect('order_list')
            
            # Order can be cancelled (pending or confirmed status)
            # Restore inventory back to stock
            success, message = restore_inventory_for_order(order)
            if not success:
                messages.error(request, f"Cannot cancel order. {message}")
                return redirect('order_list')
            
            # Update order status to cancelled
            order.status = "cancelled"
            order.save()
            
            # Update payment status to cancelled
            payment.payment_status = "cancelled"
            payment.save()
            
            messages.success(request, "Order cancelled successfully. Inventory has been restored.")
            return redirect('order_list')
        
        # ───────── UNKNOWN PAYMENT METHOD ─────────
        messages.error(request, "Invalid payment method.")
        return redirect('order_list')
    
    # If not POST request
    return redirect('order_list')


@login_required
@never_cache
def mark_order_received(request, order_id):
    """
    Customer marks order as received (shipped → delivered)
    Only for COD orders: Also update payment status to success
    """
    if request.method == "POST":
        # Get the order for the current user
        order = get_object_or_404(Order, id=order_id, user=request.user)
        
        # Check if order is in shipped status
        if order.status != "shipped":
            messages.error(request, "Only shipped orders can be marked as received.")
            return redirect('order_list')
        
        # Get payment record
        payment = order.payments.first()
        
        if not payment:
            messages.error(request, "Payment information not found for this order.")
            return redirect('order_list')
        
        # Update order status to delivered
        order.status = "delivered"
        order.save()
        
        # If COD order, update payment status to success (payment collected on delivery)
        if payment.payment_method == "cod" and payment.payment_status == "pending":
            payment.payment_status = "success"
            payment.save()
            messages.success(request, "Order marked as delivered! Payment status updated to collected.")
        else:
            messages.success(request, "Order marked as delivered!")
        
        return redirect('order_list')
    
    # If not POST request
    return redirect('order_list')


@login_required
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
            orders = orders.filter(id=int(query))
        else:
            orders = orders.filter(
                user__first_name__icontains=query
            ) | orders.filter(
                user__last_name__icontains=query
            )
    
    paginator = Paginator(orders, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # Check if we need to track a purchase
    track_purchase_order_id = request.session.pop('track_purchase_order_id', None)
    track_order = None
    
    if track_purchase_order_id:
        track_order = Order.objects.filter(
            id=track_purchase_order_id, 
            user=request.user
        ).first()

    return render(request, "orderlist.html", {
        "page_obj": page_obj, 
        "query": query,
        "track_order": track_order  # Pass order to track purchase
    })


@login_required
def order_detail(request, order_id):
    order = Order.objects.filter(id=order_id, user=request.user).first()
    if order:
        return render(request, "orderdetail.html", {"order": order})
    else:
        return render(request, "orderlist.html")



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


@login_required
@user_passes_test(is_admin)
def admin_order_list(request):
    """
    Admin view for all orders with search and pagination
    """
    query = request.GET.get("query", "").strip()
    orders = Order.objects.all().order_by("-order_date")
    
    if query:
        if query.isdigit():
            # Search by order ID
            orders = orders.filter(id=int(query))
        else:
            # Search by customer name or email
            orders = orders.filter(
                Q(user__first_name__icontains=query) |
                Q(user__last_name__icontains=query) |
                Q(user__email__icontains=query)
            )
    
    # Pagination
    paginator = Paginator(orders, 20)  # 20 orders per page for admin
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(request, "admin_orderlist.html", {
        "page_obj": page_obj,
        "query": query
    })


@login_required
@user_passes_test(is_admin)
def admin_order_detail(request, order_id):
    """
    Admin view for order details
    """
    order = get_object_or_404(Order, id=order_id)
    return render(request, "admin_orderdetail.html", {"order": order})


@login_required
@user_passes_test(is_admin)
def admin_update_order_status(request, order_id):
    """
    Admin can update order status:
    - Confirmed → Processing
    - Processing → Shipped
    """
    if request.method == "POST":
        order = get_object_or_404(Order, id=order_id)
        new_status = request.POST.get("new_status", "").strip()
        
        # Validate status transition
        valid_transitions = {
            "confirmed": "processing",
            "processing": "shipped"
        }
        
        if order.status in valid_transitions and new_status == valid_transitions[order.status]:
            order.status = new_status
            order.save()
            messages.success(request, f"Order status updated to {new_status.upper()}")
        else:
            messages.error(request, "Invalid status transition")
    
    return redirect("admin_order_list")


def restore_inventory_for_order(order):
    """
    Restore inventory stock for all items in a cancelled order.
    Creates StockTransaction records for audit trail.
    """
    try:
        for item in order.items.all():
            # Get the stock record for this variant
            stock = Stock.objects.get(productvariant=item.variant)
            
            # Calculate transaction cost based on current cost_per_unit
            transaction_cost = stock.cost_per_unit * item.quantity
            
            # Increase the quantity back
            stock.quantity += item.quantity
            
            # Increase total_cost back (stock coming in)
            stock.total_cost += transaction_cost
            stock.save()
            
            # Create a stock transaction record for audit
            StockTransaction.objects.create(
                productvariant=item.variant,
                change=item.quantity,  # Positive for stock in (restoration)
                transaction_cost=transaction_cost,  # Added transaction_cost
                reason=f"Order #{order.id} - Cancelled",
            )
        
        return True, "Inventory restored successfully"
    except Stock.DoesNotExist:
        return False, f"Stock record not found for variant"
    except Exception as e:
        return False, str(e)


@login_required
@user_passes_test(is_admin)
def admin_cancel_order(request, order_id):
    """
    Admin can cancel orders in pending, confirmed, or processing status.
    Cannot cancel shipped or delivered orders.
    Restores inventory and handles payment status automatically.
    """
    if request.method == "POST":
        order = get_object_or_404(Order, id=order_id)
        
        # Check if order is already cancelled
        if order.status == "cancelled":
            messages.info(request, f"Order #{order.id} is already cancelled.")
            return redirect("admin_order_list")
        
        # Admin cannot cancel shipped or delivered orders (Option 2)
        non_cancellable_statuses = ["shipped", "delivered"]
        if order.status in non_cancellable_statuses:
            messages.error(request, f"Cannot cancel order. Order is already {order.status}.")
            return redirect("admin_order_list")
        
        # Get payment record
        payment = order.payments.first()
        
        if not payment:
            messages.error(request, "Payment information not found for this order.")
            return redirect("admin_order_list")
        
        # Restore inventory
        success, message = restore_inventory_for_order(order)
        if not success:
            messages.error(request, f"Cannot cancel order. {message}")
            return redirect("admin_order_list")
        
        # Update order status to cancelled
        order.status = "cancelled"
        order.save()
        
        # Update payment status based on payment method and current status
        if payment.payment_method == "cod":
            # COD: Payment not collected yet
            payment.payment_status = "cancelled"
            payment.save()
            messages.success(request, f"Order #{order.id} cancelled successfully.")
        
        elif payment.payment_method == "esewa":
            if payment.payment_status == "success":
                # eSewa paid: Mark for refund
                payment.payment_status = "refund_pending"
                payment.save()
                messages.warning(
                    request, 
                    f"Order #{order.id} cancelled. eSewa refund of Rs.{order.total_amount} is pending."
                )
            else:
                # eSewa not completed
                payment.payment_status = "cancelled"
                payment.save()
                messages.success(request, f"Order #{order.id} cancelled successfully.")
        
        else:
            # Other payment methods
            payment.payment_status = "cancelled"
            payment.save()
            messages.success(request, f"Order #{order.id} cancelled successfully.")
    
    return redirect("admin_order_list")


@login_required
@user_passes_test(is_admin)
def monthly_report(request):
    # Get filter parameters
    year = request.GET.get("year", datetime.now().year)
    month = request.GET.get("month", "all")
    status = request.GET.get("status", "all")
    
    try:
        year = int(year)
    except (ValueError, TypeError):
        year = datetime.now().year

    # Base queryset
    orders = Order.objects.all()

    # Filter by year
    orders = orders.filter(order_date__year=year)

    # Filter by month
    if month != "all":
        try:
            month_num = int(month)
            if 1 <= month_num <= 12:
                orders = orders.filter(order_date__month=month_num)
        except (ValueError, TypeError):
            pass

    # Filter by status
    if status != "all":
        orders = orders.filter(status=status)

    # Monthly aggregation for charts/trends
    monthly_data = (
        Order.objects.filter(order_date__year=year)
        .annotate(month=TruncMonth('order_date'))
        .values('month')
        .annotate(
            total_orders=Count('id'),
            total_revenue=Sum('total_amount'),
            avg_order_value=Avg('total_amount')
        )
        .order_by('month')
    )

    # Overall statistics for selected filters
    stats = orders.aggregate(
        total_orders=Count('id'),
        total_revenue=Sum('total_amount'),
        avg_order_value=Avg('total_amount'),
        total_items_sold=Sum('items__quantity')
    )

    # Status breakdown
    status_breakdown = (
        orders.values('status')
        .annotate(count=Count('id'))
        .order_by('-count')
    )

    # Top selling products in the period
    top_products = (
        OrderItem.objects.filter(order__in=orders)
        .values('variant__product__product_name', 'variant__variant_name')
        .annotate(
            total_quantity=Sum('quantity'),
            total_revenue=Sum('total_orderitem_amount')
        )
        .order_by('-total_quantity')[:10]
    )

    # Paginate orders list
    orders_list = orders.order_by('-order_date')
    paginator = Paginator(orders_list, 15)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # Available years for dropdown
    available_years = (
        Order.objects.dates('order_date', 'year', order='DESC')
        .values_list('order_date__year', flat=True)
        .distinct()
    )

    context = {
        "page_obj": page_obj,
        "year": year,
        "month": month,
        "status": status,
        "monthly_data": list(monthly_data),
        "stats": stats,
        "status_breakdown": status_breakdown,
        "top_products": top_products,
        "available_years": list(available_years) if available_years else [datetime.now().year],
        "status_choices": Order.STATUS_CHOICES,
    }
    
    return render(request, "admin_monthlyreport.html", context)


