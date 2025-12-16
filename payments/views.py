import uuid
import base64
import json
import hmac
import hashlib

from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import never_cache
from django.contrib.auth.decorators import login_required

from django.contrib import messages
from django.conf import settings
from django.http import HttpResponse

from carts.models import CartItem, Cart
from orders.models import Order, OrderItem
from payments.models import Payment
from inventory.models import Stock, StockTransaction


import os
from django.conf import settings
from django.http import HttpResponse, FileResponse
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

# ───────────────────────────────────
# Helper Functions
# ───────────────────────────────────

def generate_signature(total_amount, transaction_uuid, product_code, secret_key):
    """Generate eSewa signature"""
    data = f"total_amount={total_amount},transaction_uuid={transaction_uuid},product_code={product_code}"
    key = secret_key
    message = data.encode()
    key_bytes = key.encode()
    signature = hmac.new(key_bytes, message, hashlib.sha256).digest()
    encoded_signature = base64.b64encode(signature).decode()
    return encoded_signature


def decode_base64_response(encoded_data):
    """Decode eSewa response"""
    try:
        decoded = base64.b64decode(encoded_data)
        response_data = json.loads(decoded)
        return response_data
    except Exception as e:
        print(f"Error decoding eSewa response: {e}")
        return None


def reduce_inventory_for_order(order):
    """
    Reduce inventory stock for all items in the order.
    Creates StockTransaction records for audit trail.
    """
    try:
        for item in order.items.all():
            # Get the stock record for this variant
            stock = Stock.objects.get(productvariant=item.variant)
            
            # Check if sufficient stock is available
            if stock.quantity >= item.quantity:
                # Calculate transaction cost based on current cost_per_unit
                transaction_cost = stock.cost_per_unit * item.quantity
                
                # Reduce stock quantity
                stock.quantity -= item.quantity
                
                # Reduce total_cost (stock going out)
                stock.total_cost -= transaction_cost
                stock.save()
                
                # Create a stock transaction record for audit
                StockTransaction.objects.create(
                    productvariant=item.variant,
                    change=-item.quantity,  # Negative for stock out
                    transaction_cost=transaction_cost,  # Added transaction_cost
                    reason=f"Order #{order.id} - Payment Confirmed",
                )
            else:
                raise ValueError(f"Insufficient stock for {item.variant.product.product_name}")
        
        return True, "Inventory reduced successfully"
    except Stock.DoesNotExist:
        return False, f"Stock record not found for variant"
    except Exception as e:
        return False, str(e)


def delete_user_cart(user):
    """Delete all cart items and cart for user"""
    cart = Cart.objects.filter(user=user)
    CartItem.objects.filter(cart__in=cart).delete()
    cart.delete()


# ───────────────────────────────────
# Payment Views
# ───────────────────────────────────

@login_required
def make_payment(request):
    """Handle payment method selection and processing"""
    if request.method == "POST":
        order_id = request.POST.get('order_id')
        payment_method = request.POST.get('payment_method', '').strip()

        order = get_object_or_404(Order, id=order_id, user=request.user)

        # ───────── VALIDATION ─────────
        if not payment_method:
            messages.error(request, "Please select a payment method.")
            return render(request, "payment.html", {"order": order})

        # Check if order is cancelled - DO NOT allow payment
        if order.status == "cancelled":
            messages.error(request, "This order has been cancelled. Please create a new order.")
            return redirect('order_list')

        # If order already has successful payment
        if Payment.objects.filter(order=order, payment_status="success").exists():
            messages.info(request, "This order is already paid.")
            return redirect('order_list')

        # Check if payment already failed - DO NOT allow retry
        existing_payment = order.payments.first()
        if existing_payment and existing_payment.payment_status == "failed":
            messages.error(request, "Payment for this order has failed. Please create a new order.")
            return redirect('order_list')

        # ───────── CASH ON DELIVERY ─────────
        if payment_method == "cod":
            # Check if payment record already exists
            payment = order.payments.first()
            
            # Only update if payment status is "pending"
            if payment and payment.payment_status == "pending":
                # Update existing pending payment
                payment.payment_method = "cod"
                payment.paid_amount = order.total_amount
                payment.save()
            elif not payment:
                # Create new payment record only if none exists
                Payment.objects.create(
                    order=order,
                    payment_method="cod",
                    payment_status="pending",
                    paid_amount=order.total_amount,
                )

            # Reduce inventory for confirmed order
            success, message = reduce_inventory_for_order(order)
            if not success:
                messages.error(request, f"Error reducing inventory: {message}")
                return redirect('checkout')

            # Update order status to confirmed
            order.status = "confirmed"
            order.save()

            try:
                generate_invoice_pdf(order)
            except Exception as e:
                print(f"Invoice generation failed for order {order.id}: {e}")

            # Delete cart items
            delete_user_cart(request.user)

            # Store order ID in session for GA4 tracking
            request.session['track_purchase_order_id'] = order.id

            messages.success(request, "Order confirmed! Invoice generated. Payment will be collected on delivery.")
            return redirect('order_list')

        # ───────── ESEWA PAYMENT ─────────
        elif payment_method == "esewa":
            # Check if payment record already exists
            payment = order.payments.first()
            
            # Only update if payment status is "pending"
            if payment and payment.payment_status == "pending":
                # Update existing pending payment
                payment.payment_method = "esewa"
                payment.paid_amount = order.total_amount
                payment.transaction_id = None  # Clear any old transaction ID
                payment.save()
            elif not payment:
                # Create new payment record only if none exists
                payment = Payment.objects.create(
                    order=order,
                    payment_method="esewa",
                    payment_status="pending",
                    paid_amount=order.total_amount,
                )

            # Store order info in session for callback
            request.session['order_id'] = order.id
            
            # eSewa payment details
            total_amount = str(int(order.total_amount))
            transaction_uuid = str(uuid.uuid4())
            product_code = settings.ESEWA_MERCHANT_CODE
            secret_key = settings.ESEWA_SECRET_KEY

            # Generate signature
            signature = generate_signature(total_amount, transaction_uuid, product_code, secret_key)

            # Create eSewa form
            html_response = f"""
            <html>
            <head>
                <title>Redirecting to eSewa...</title>
            </head>
            <body onload="document.getElementById('esewa-form').submit();">
                <form id="esewa-form" action="{settings.ESEWA_BASE_URL}" method="POST">
                    <input type="hidden" name="amount" value="{total_amount}">
                    <input type="hidden" name="tax_amount" value="0">
                    <input type="hidden" name="total_amount" value="{total_amount}">
                    <input type="hidden" name="transaction_uuid" value="{transaction_uuid}">
                    <input type="hidden" name="product_code" value="{product_code}">
                    <input type="hidden" name="product_service_charge" value="0">
                    <input type="hidden" name="product_delivery_charge" value="0">
                    <input type="hidden" name="success_url" value="{settings.ESEWA_SUCCESS_URL}">
                    <input type="hidden" name="failure_url" value="{settings.ESEWA_FAILURE_URL}">
                    <input type="hidden" name="signed_field_names" value="total_amount,transaction_uuid,product_code">
                    <input type="hidden" name="signature" value="{signature}">
                </form>
                <p>Redirecting to eSewa payment gateway...</p>
            </body>
            </html>
            """
            return HttpResponse(html_response)

        else:
            messages.error(request, "Invalid payment method selected.")
            return render(request, "payment.html", {"order": order})

    return redirect('home')



@login_required
@never_cache
def esewa_payment_success(request):
    """Handle successful eSewa payment callback"""
    order_id = request.session.get('order_id')

    if not order_id:
        messages.error(request, "Session expired. Please try again.")
        return redirect('order_list')

    order = get_object_or_404(Order, id=order_id, user=request.user)
    payment = order.payments.first()

    if not payment:
        messages.error(request, "Payment record not found.")
        return redirect('order_list')

    # Get eSewa response
    encoded_response = request.GET.get('data')

    if not encoded_response:
        messages.error(request, "No response from eSewa payment gateway.")
        # Mark payment as failed and cancel order
        payment.payment_status = "failed"
        payment.save()
        order.status = "cancelled"
        order.save()
        request.session.pop('order_id', None)
        return redirect('order_list')

    # Decode response
    response_data = decode_base64_response(encoded_response)

    if response_data is None:
        messages.error(request, "Invalid response format from eSewa.")
        # Mark payment as failed and cancel order
        payment.payment_status = "failed"
        payment.save()
        order.status = "cancelled"
        order.save()
        request.session.pop('order_id', None)
        return redirect('order_list')

    # Check payment status
    status = response_data.get('status')
    transaction_uuid = response_data.get('transaction_uuid')

    if status == "COMPLETE" and transaction_uuid:
        # Update payment record to success
        payment.payment_status = "success"
        payment.transaction_id = transaction_uuid
        payment.save()

        # Reduce inventory
        success, message = reduce_inventory_for_order(order)
        if not success:
            messages.error(request, f"Error reducing inventory: {message}")

        # Update order status to confirmed
        order.status = "confirmed"
        order.save()

        # Generate invoice (shows "PAID" with transaction ID)
        try:
            generate_invoice_pdf(order)
        except Exception as e:
            # Log error but don't block order
            print(f"Invoice generation failed for order {order.id}: {e}")

        # Delete cart
        delete_user_cart(request.user)

        # Store order ID for GA4 tracking before clearing session
        request.session['track_purchase_order_id'] = order.id
        
        # Clear eSewa order session
        request.session.pop('order_id', None)

        messages.success(request, "Payment successful! Your order has been confirmed. Invoice generated.")
        return redirect('order_list')
    else:
        # Payment failed - Mark as failed and cancel order
        payment.payment_status = "failed"
        payment.save()
        order.status = "cancelled"
        order.save()
        request.session.pop('order_id', None)
        messages.error(request, "Payment failed. Order has been cancelled. Please create a new order.")
        return redirect('order_list')


@login_required
@never_cache
def esewa_payment_failure(request):
    """Handle failed eSewa payment callback"""
    order_id = request.session.get('order_id')

    if not order_id:
        request.session.pop('order_id', None)
        messages.error(request, "Session expired.")
        return redirect('order_list')

    order = get_object_or_404(Order, id=order_id, user=request.user)
    payment = order.payments.first()

    if not payment:
        messages.error(request, "Payment record not found.")
        return redirect('order_list')

    # Get eSewa response
    encoded_response = request.GET.get('data')

    if not encoded_response:
        request.session.pop('order_id', None)
        messages.error(request, "Payment cancelled by user.")
        # Mark payment as failed and cancel order
        payment.payment_status = "failed"
        payment.save()
        order.status = "cancelled"
        order.save()
        return redirect('order_list')

    # Decode response
    response_data = decode_base64_response(encoded_response)

    if response_data is None:
        messages.error(request, "Invalid response format from eSewa.")
        # Mark payment as failed and cancel order
        payment.payment_status = "failed"
        payment.save()
        order.status = "cancelled"
        order.save()
        request.session.pop('order_id', None)
        return redirect('order_list')

    # Payment failed
    status = response_data.get('status')
    if status != "COMPLETE":
        request.session.pop('order_id', None)
        # Mark payment as failed and cancel order
        payment.payment_status = "failed"
        payment.save()
        order.status = "cancelled"
        order.save()
        messages.error(request, "Payment failed or was cancelled. Please create a new order.")
        return redirect('order_list')

    messages.error(request, "Payment processing failed.")
    return redirect('order_list')


def generate_invoice_pdf(order):
    """
    Generate invoice PDF for an order and save it to media directory
    Invoice always shows order status as 'CONFIRMED' regardless of actual status
    """
    # Create media/invoices directory if it doesn't exist
    invoice_dir = os.path.join(settings.MEDIA_ROOT, 'invoices')
    os.makedirs(invoice_dir, exist_ok=True)
    
    # Create filename with order ID and timestamp
    invoice_filename = f"invoice_order_{order.id}_{order.order_date.strftime('%Y%m%d_%H%M%S')}.pdf"
    invoice_path = os.path.join(invoice_dir, invoice_filename)
    
    # Create PDF document
    doc = SimpleDocTemplate(
        invoice_path,
        pagesize=A4,
        rightMargin=0.25*inch,
        leftMargin=0.25*inch,
        topMargin=0.25*inch,
        bottomMargin=0.25*inch,
    )
    
    # Container for PDF elements
    elements = []
    
    # Define styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#080033'),
        spaceAfter=12,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=12,
        textColor=colors.HexColor('#080033'),
        spaceAfter=6,
        fontName='Helvetica-Bold'
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=3,
    )
    
    # Title
    elements.append(Paragraph("SNEAKEE", title_style))
    elements.append(Paragraph("Invoice", heading_style))
    
    invoice_info = f"""
    <b>Invoice Number:</b> INV-{order.id:05d}<br/>
    <b>Invoice Date:</b> {order.order_date.strftime('%d %B %Y')}<br/>
    <b>Order Date:</b> {order.order_date.strftime('%d %B %Y %H:%M')}<br/>
    """
    elements.append(Paragraph(invoice_info, normal_style))
    elements.append(Spacer(1, 8))
    
    # Customer Information
    elements.append(Paragraph("Bill To:", heading_style))
    customer_info = f"""
    <b>Customer Name:</b> {order.user.username}<br/>
    <b>Email:</b> {order.user.email}<br/>
    <b>Phone:</b> {order.user.phone}<br/>
    """
    elements.append(Paragraph(customer_info, normal_style))
    elements.append(Spacer(1, 8))
    
    # Shipping Address
    elements.append(Paragraph("Shipping Address:", heading_style))
    if order.shipping_address:
        shipping_info = f"""
        <b>Contact Person:</b> {order.shipping_address.contact_person}<br/>
        <b>Province:</b> {order.shipping_address.province}<br/>
        <b>District:</b> {order.shipping_address.district}<br/>
        <b>City:</b> {order.shipping_address.city}<br/>
        <b>Location:</b> {order.shipping_address.location}<br/>
        <b>Landmark:</b> {order.shipping_address.landmark if order.shipping_address.landmark else 'N/A'}<br/>
        <b>Phone:</b> {order.shipping_address.contact_number if order.shipping_address.contact_number else 'N/A'}<br/>
        """
        elements.append(Paragraph(shipping_info, normal_style))
    elements.append(Spacer(1, 12))
    
    # Order Items Table
    elements.append(Paragraph("Order Details:", heading_style))
    elements.append(Spacer(1, 6))
    
    # Build items table
    items_data = [
        ['SKU', 'Variant', 'Size', 'Quantity', 'Unit Price', 'Amount']
    ]
    
    for item in order.items.all():
        items_data.append([
            item.variant.sku,
            item.variant.variant_name,
            item.variant.size,
            str(item.quantity),
            f"NPR {item.price:,.2f}",
            f"NPR {item.total_orderitem_amount:,.2f}"
        ])
    
    items_table = Table(
        items_data,
        colWidths=[1.0*inch, 2.5*inch, 0.6*inch, 0.6*inch, 1.2*inch, 1.5*inch]
    )
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#E0E0E0")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
    ]))
    elements.append(items_table)
    elements.append(Spacer(1, 12))
    
    # Summary Section
    summary_data = [
        ['', 'Subtotal:', f"NPR {order.subtotal:,.2f}"],
        ['', 'Shipping Fee:', f"NPR {order.shipping_fee:,.2f}"],
        ['', 'Total Amount:', f"NPR {order.total_amount:,.2f}"],
    ]
    
    summary_table = Table(summary_data, colWidths=[2.5*inch, 1.5*inch, 1.5*inch])
    summary_table.setStyle(TableStyle([
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('FONT', (1, 0), (1, -2), 'Helvetica', 9),
        ('FONT', (1, -1), (1, -1), 'Helvetica-Bold', 12),
        ('FONT', (2, 0), (2, -2), 'Helvetica', 9),
        ('FONT', (2, -1), (2, -1), 'Helvetica-Bold', 12),
        ('TEXTCOLOR', (2, -1), (2, -1), colors.HexColor('#080033')),
        ('BACKGROUND', (1, -1), (-1, -1), colors.HexColor('#e5e7eb')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 12))
    
    # Payment Information
    payment = order.payments.first()
    if payment:
        elements.append(Paragraph("Payment Information:", heading_style))
        
        if payment.payment_method == "cod":
            # COD: Show PENDING status
            payment_info = f"""
            <b>Payment Method:</b> CASH ON DELIVERY<br/>
            <b>Payment Status:</b> PENDING - Cash on Delivery<br/>
            <b>Amount to be Paid:</b> NPR {payment.paid_amount:,.2f}
            """
        elif payment.payment_method == "esewa":
            # eSewa: Show PAID status with transaction ID
            if payment.payment_status == "success":
                payment_info = f"""
                <b>Payment Method:</b> ESEWA (Online Payment)<br/>
                <b>Payment Status:</b> PAID<br/>
                <b>Transaction ID:</b> {payment.transaction_id if payment.transaction_id else 'N/A'}<br/>
                <b>Amount Paid:</b> NPR {payment.paid_amount:,.2f}
                """
            else:
                # eSewa but payment not successful (shouldn't normally happen)
                payment_info = f"""
                <b>Payment Method:</b> ESEWA (Online Payment)<br/>
                <b>Payment Status:</b> {payment.payment_status.upper()}<br/>
                <b>Amount:</b> NPR {payment.paid_amount:,.2f}
                """
        else:
            # Fallback for other payment methods
            payment_info = f"""
            <b>Payment Method:</b> {payment.payment_method.upper()}<br/>
            <b>Payment Status:</b> {payment.payment_status.upper()}<br/>
            <b>Amount:</b> NPR {payment.paid_amount:,.2f}
            """
        
        elements.append(Paragraph(payment_info, normal_style))
        elements.append(Spacer(1, 12))
    
    # Order Status - ALWAYS show as CONFIRMED in invoice
    elements.append(Paragraph("Order Status:", heading_style))
    status_text = f"""
    <b>Status:</b> CONFIRMED<br/>
    <b>Order ID:</b> {order.id}
    """
    elements.append(Paragraph(status_text, normal_style))
    elements.append(Spacer(1, 20))
    
    # Footer
    footer_text = """
    Thank you for your purchase from Sneakee!<br/>
    For inquiries, please contact us through our website.<br/>
    <font size=8>This is a computer-generated invoice. No signature is required.</font>
    """
    elements.append(Paragraph(footer_text, ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=9,
        alignment=TA_CENTER,
        textColor=colors.grey,
    )))
    
    # Build PDF
    doc.build(elements)
    
    # Return the relative path for storing in database
    relative_path = os.path.join('invoices', invoice_filename)
    return relative_path


@login_required
def view_invoice(request, order_id):
    """
    View invoice PDF in browser
    Invoice is available once order is confirmed
    - Admin: Can view invoices for all orders including cancelled ones
    - Customer: Cannot view invoices for cancelled orders
    """
    # Admin can view any order, customer can only view their own
    if request.user.is_staff or request.user.is_superuser:
        order = get_object_or_404(Order, id=order_id)
    else:
        order = get_object_or_404(Order, id=order_id, user=request.user)
    
    # Check invoice availability based on user role
    if request.user.is_staff or request.user.is_superuser:
        # Admin: Can view invoices for confirmed and later stages including cancelled
        if order.status not in ["confirmed", "processing", "shipped", "delivered", "cancelled"]:
            messages.error(request, "Invoice not available for this order.")
            return redirect('admin_order_list')
    else:
        # Customer: Cannot view invoices for cancelled orders
        if order.status == "cancelled":
            messages.error(request, "Invoice is not available for cancelled orders.")
            return redirect('order_list')
        
        # Customer: Invoice available for confirmed and later stages only
        if order.status not in ["confirmed", "processing", "shipped", "delivered"]:
            messages.error(request, "Invoice not available for this order.")
            return redirect('order_list')
    
    # Generate invoice filename
    invoice_filename = f"invoice_order_{order.id}_{order.order_date.strftime('%Y%m%d_%H%M%S')}.pdf"
    invoice_path = os.path.join(settings.MEDIA_ROOT, 'invoices', invoice_filename)
    
    # Generate invoice if it doesn't exist
    if not os.path.exists(invoice_path):
        try:
            generate_invoice_pdf(order)
        except Exception as e:
            messages.error(request, f"Error generating invoice: {str(e)}")
            if request.user.is_staff or request.user.is_superuser:
                return redirect('admin_order_list')
            return redirect('order_list')
    
    # Check if file was created successfully
    if not os.path.exists(invoice_path):
        messages.error(request, "Error generating invoice. Please try again.")
        if request.user.is_staff or request.user.is_superuser:
            return redirect('admin_order_list')
        return redirect('order_list')
    
    # Return file for viewing
    try:
        response = FileResponse(open(invoice_path, 'rb'), content_type='application/pdf')
        response['Content-Disposition'] = 'inline; filename="invoice.pdf"'
        return response
    except Exception as e:
        messages.error(request, f"Error viewing invoice: {str(e)}")
        if request.user.is_staff or request.user.is_superuser:
            return redirect('admin_order_list')
        return redirect('order_list')


@login_required
def download_invoice(request, order_id):
    """
    Download invoice PDF for an order
    Invoice is available once order is confirmed
    - Admin: Can download invoices for all orders including cancelled ones
    - Customer: Cannot download invoices for cancelled orders
    """
    # Admin can view any order, customer can only view their own
    if request.user.is_staff or request.user.is_superuser:
        order = get_object_or_404(Order, id=order_id)
    else:
        order = get_object_or_404(Order, id=order_id, user=request.user)
    
    # Check invoice availability based on user role
    if request.user.is_staff or request.user.is_superuser:
        # Admin: Can download invoices for confirmed and later stages including cancelled
        if order.status not in ["confirmed", "processing", "shipped", "delivered", "cancelled"]:
            messages.error(request, "Invoice not available for this order.")
            return redirect('admin_order_list')
    else:
        # Customer: Cannot download invoices for cancelled orders
        if order.status == "cancelled":
            messages.error(request, "Invoice cannot be downloaded for cancelled orders.")
            return redirect('order_list')
        
        # Customer: Invoice available for confirmed and later stages only
        if order.status not in ["confirmed", "processing", "shipped", "delivered"]:
            messages.error(request, "Invoice not available for this order.")
            return redirect('order_list')
    
    invoice_filename = f"invoice_order_{order.id}_{order.order_date.strftime('%Y%m%d_%H%M%S')}.pdf"
    invoice_path = os.path.join(settings.MEDIA_ROOT, 'invoices', invoice_filename)
    
    # Generate invoice if it doesn't exist
    if not os.path.exists(invoice_path):
        try:
            generate_invoice_pdf(order)
        except Exception as e:
            messages.error(request, f"Error generating invoice: {str(e)}")
            if request.user.is_staff or request.user.is_superuser:
                return redirect('admin_order_list')
            return redirect('order_list')
    
    # Check if file was created successfully
    if not os.path.exists(invoice_path):
        messages.error(request, "Error generating invoice. Please try again.")
        if request.user.is_staff or request.user.is_superuser:
            return redirect('admin_order_list')
        return redirect('order_list')
    
    # Return file for download
    try:
        response = FileResponse(open(invoice_path, 'rb'), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="invoice_order_{order.id}.pdf"'
        return response
    except Exception as e:
        messages.error(request, f"Error downloading invoice: {str(e)}")
        if request.user.is_staff or request.user.is_superuser:
            return redirect('admin_order_list')
        return redirect('order_list')