import re
from django.shortcuts import render, redirect,  get_object_or_404
from django.contrib import messages

from django.contrib.auth import authenticate, login, logout
from django.views.decorators.cache import never_cache
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.sessions.models import Session

from django.db.models import Q, Count
from django.core.paginator import Paginator

from users.models import User, ShippingAddress
from carts.models import Cart
from products.models import ProductVariant

from carts.views import add_to_cart

def is_admin(user):
    return user.is_staff or user.is_superuser

@never_cache
def signup(request):
    email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    phone_pattern1 = r"^98\d{8}$"
    phone_pattern2 = r"^97\d{8}$"
    no_space= r"^\S+$"

    if request.method == 'POST':
        username = request.POST.get('username', '').strip().lower()
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '').strip()
        address = request.POST.get('address', '').strip()
        phone = request.POST.get('phone', '').strip()

        context = {
            'username': username,
            'email': email,
            'address': address,
            'phone': phone,
        }

        if not username or not email or not password or not address or not phone:
            messages.error(request, "All fields are required.")
            return render(request, 'signup.html', context)
        
        elif not re.match(no_space,username):
            messages.error(request, "Username cannot contain spaces.")
            return render(request, 'signup.html', context)
        
        elif not re.match(email_pattern, email):
            messages.error(request, "Please enter a valid email address.")
            return render(request, 'signup.html', context)
        
        elif not len(password) >= 6:
            messages.error(request, "Password must be at least 6 characters long.")
            return render(request, 'signup.html', context)
        
        elif not (re.match(phone_pattern1, phone) or re.match(phone_pattern2, phone)):
            messages.error(request, "Invalid phone number. Must start with 97 or 98 and be 10 digits long.")
            return render(request,'signup.html', context)
        
        if User.objects.filter(username=username).exists():
            messages.error(request,"Username already taken.")
            return render(request, 'signup.html', context)
        
        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already registered.")
            return render(request, 'signup.html', context)
        
        user= User.objects.create_user(#create_user hash password automatically
            username=username,
            email=email,
            password=password,
            address=address,
            phone=phone
        )

        user.save()
        messages.success(request, "Account created successfully")
        return redirect('signin')
    
    return render(request, 'signup.html')


from django.urls import reverse
from django.contrib.sessions.models import Session

@never_cache
def signin(request):
    if request.method == 'POST':
        login_input = request.POST.get('login_input', '').strip().lower()
        password = request.POST.get('password', '').strip()
        context = {'login_input': login_input}

        user_obj = None

        try:
            user_obj = User.objects.get(email=login_input)
        except User.DoesNotExist:
            try:
                user_obj = User.objects.get(username=login_input)
            except User.DoesNotExist:
                user_obj = None

        if user_obj:
            if not user_obj.is_active:
                messages.error(request, "Your account has been deactivated.")
                return render(request, 'signin.html', context)

            user = authenticate(request, username=user_obj.email, password=password)

            if user:
                # 🔴 Kill previous session
                if user.active_session_key:
                    Session.objects.filter(session_key=user.active_session_key).delete()

                login(request, user)
                request.session.save()

                user.active_session_key = request.session.session_key
                user.save(update_fields=['active_session_key'])

                action = request.session.pop('post_login_action', None)
                data = request.session.pop('post_login_data', None)

                if action == 'buy_now' and data:
                    return redirect(
                        f"{reverse('buy_now_view')}?variant_id={data['variant_id']}&quantity={data['quantity']}"
                    )

                if action == 'add_to_cart' and data:
                    request.POST = request.POST.copy()
                    request.POST.update(data)
                    return add_to_cart(request)

                if user.is_staff:
                    return redirect('admindashboard')
                return redirect('home')

        messages.error(request, "Invalid credentials")
        return render(request, 'signin.html', context)

    return render(request, 'signin.html')



@login_required
def signout(request):
    user = request.user

    user.active_session_key = None
    user.save(update_fields=["active_session_key"])

    logout(request)
    return redirect('signin')


@never_cache
@login_required
def editprofile(request):
    user = request.user  # already the authenticated user
    if user.is_staff:
        base_template='administrator/base.html'
    else:
        base_template='customer/base.html'

    phone_pattern1 = r"^98\d{8}$"
    phone_pattern2 = r"^97\d{8}$"
    shipping_address = ShippingAddress.objects.filter(user=user).all()
    context = {
        "base_template":base_template,
        "username": user.username,
        "email": user.email,
        "user_id": user.id,
        "address":user.address,
        "phone":user.phone,
        'shippingaddress':shipping_address,
    }

    if request.method == "POST":
        # Update password if provided
        user=User.objects.filter(id=user.id).first()
        password = request.POST.get('password', '').strip()
        phone = request.POST.get('phone', '').strip()

        if password and not len(password)>=6:
            messages.error(request, "Password must be atleast 6 characters long.")
            return render(request, 'editprofile.html', context) 

        elif not (re.match(phone_pattern1, phone) or re.match(phone_pattern2, phone)):
            messages.error(request, "Invalid phone number. Must start with 97 or 98 and be 10 digits long.")
            return render(request,'editprofile.html', context)
        
        elif User.objects.filter(phone=phone).exclude(id=int(user.id)).exists():
            messages.error(request, "Phone already exists.")
            return render(request,'editprofile.html',context)
        
        if password:
            user.set_password(password) # always use set_password

        if phone:
            user.phone = phone  # assuming you have a Profile model with phone
            user.save()

        user.save()
        messages.success(request, "Profile updated successfully.")
        return redirect("editprofile")
    
    return render(request, 'editprofile.html', context)


@never_cache
@login_required
@user_passes_test(is_admin)
def addadmin(request):
    if request.user.is_superuser:
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        phone_pattern1 = r"^98\d{8}$"
        phone_pattern2 = r"^97\d{8}$"
        no_space= r"^\S+$"

        if request.method=='POST':
            username = request.POST.get('username', '').strip().lower()
            email = request.POST.get('email', '').strip().lower()
            password = request.POST.get('password', '').strip()
            phone = request.POST.get('phone', '').strip()
            address = request.POST.get('address', '').strip()


            context={
                'username':username,
                'email':email,
                'phone':phone,
                'address':address,
            }
            
            if not username or not email or not password or not address or not phone:
                messages.error(request,"All field are required.")
                return render(request, 'addadmin.html',context)
            
            elif not re.match(no_space, username):
                messages.error(request, "Username cannot contain spaces.")
                return render(request, 'addadmin.html', context)
            
            elif not re.match(email_pattern, email):
                messages.error(request, "Invalid Email")
                return render(request, 'addadmin.html', context)
            
            elif not len(password)>=6:
                messages.error(request, "Password must be atleast 6 characters long.")
                return render(request, 'addadmin.html', context)
            
            elif not (re.match(phone_pattern1, phone) or re.match(phone_pattern2, phone)):
                messages.error(request, "Invalid phone number. Must start with 97 or 98 and be 10 digits long.")
                return render(request,'addadmin.html', context)
            
            if User.objects.filter(username=username).exists():
                messages.error(request, "User already exists.")
                return render(request, 'addadmin.html', context)
            
            if User.objects.filter(phone=phone).exists():
                messages.error(request, "Phone already exists.")
                return render(request, 'addadmin.html', context)
            
            user= User.objects.create_user(
                username=username,
                email=email,
                password=password,
                phone=phone,
                address=address,
                is_staff=True
            )

            user.save()
            messages.success(request, "Admin Created")
            return render(request, 'signin.html')  
        return render(request, 'addadmin.html')
    else:
        messages.error(request, "Only superadmins can view the admin list.")
        return redirect("userdashboard")


@never_cache
@login_required
@user_passes_test(is_admin)
def userlist(request, mode=None):
    if request.user.is_staff:
        query = request.GET.get("query", "")
        if mode == "customer":
            users = User.objects.filter(is_staff=False)
        elif mode == "admin":
            if not request.user.is_superuser:
                messages.error(request, "Only superadmins can view the admin list.")
                return redirect("userdashboard")
            users=User.objects.filter(is_staff=True, is_superuser=False)
        
        users=users.order_by("created_at")#for descending order:-created_at

        if query:
            if query.isdigit():
                users = users.filter(Q(id=int(query)) | Q(username__icontains=query) | Q(email__icontains=query) | Q(phone__icontains=query))#__icontains for case insensitive
            else:
                users = users.filter(Q(username__icontains=query) | Q(email__icontains=query) | Q(phone__icontains=query))#__icontains for case insensitive

        paginator = Paginator(users, 8)
        page_number = request.GET.get("page")#for first-time page load, request.get={}
        page_obj = paginator.get_page(page_number)#for None, Paginator.get_page() default to 1. It also contain page object_list from paginator var

        return render(request, "userlist.html", {
            "page_obj": page_obj,
            "query": query,
            "mode":mode,
        })


@never_cache
@login_required
@user_passes_test(is_admin)
def edituserform(request):
    if request.user.is_staff:
        if request.method == 'POST':
            user_id=request.POST.get('user_id','').strip()

            user = User.objects.filter(id=user_id).first()
            if not user:
                messages.error(request, "User not found.")
                return redirect('userlist')  # Or any page you want
            else:
                context = {
                    'user_id':user.id,
                    'username': user.username,
                    'email': user.email,
                    'address': user.address,
                    'phone': user.phone,
                }
                return render(request, 'edituser.html', context)


@never_cache
@login_required
@user_passes_test(is_admin)
def edituser(request):
    if request.user.is_staff:
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        phone_pattern1 = r"^98\d{8}$"
        phone_pattern2 = r"^97\d{8}$"
        no_space= r"^\S+$"

        if request.method == 'POST':
            user_id=request.POST.get('user_id', '').strip()
            username = request.POST.get('username', '').strip().lower()
            email = request.POST.get('email', '').strip().lower()
            password = request.POST.get('password', '').strip()
            address = request.POST.get('address', '').strip()
            phone = request.POST.get('phone', '').strip()
            shipping_address1 = ""
            shipping_address2 = ""
            if not request.user.is_staff:
                shipping_address1=request.POST.get('shipping_address1','').strip()
                shipping_address2=request.POST.get('shipping_address2','').strip()

            context = {
                'user_id':user_id,
                'username': username,
                'email': email,
                'address': address,
                'phone': phone,
                'shipping_address1':shipping_address1,
                'shipping_address2':shipping_address2,
            }

            # === Validation checks ===
            if not username or not email or not address or not phone:
                messages.error(request, "All fields are required.")
                return render(request, 'edituser.html', context)
            
            if not request.user.is_staff:
                if not shipping_address1 or not shipping_address2:
                    messages.error(request, "Both shipping address are required.")
                    return render(request, 'edituser.html', context)
            
            elif not re.match(no_space,username):
                messages.error(request, "Username cannot contain spaces.")
                return render(request, 'edituser.html', context)
            
            elif not re.match(email_pattern, email):
                messages.error(request, "Please enter a valid email address.")
                return render(request, 'edituser.html', context)        
            
            elif not (re.match(phone_pattern1, phone) or re.match(phone_pattern2, phone)):
                messages.error(request, "Invalid phone number. Must start with 97 or 98 and be 10 digits long.")
                return render(request,'edituser.html', context)
            
            if password and len(password) < 6:
                messages.error(request, "Password must be at least 6 characters long.")
                return render(request, 'edituser.html', context)
            
            if User.objects.filter(username=username).exclude(id=int(user_id)).exists():
                messages.error(request,"Username already taken.")
                return render(request, 'edituser.html', context)
            
            if User.objects.filter(email=email).exclude(id=int(user_id)).exists():
                messages.error(request, "Email already registered.")
                return render(request, 'edituser.html', context)
            
            user=User.objects.filter(id=user_id).first()
            if user:
                user.id=user_id
                user.username= username
                user.email= email
                if password:
                    user.set_password(password)
                user.address= address
                user.phone= phone
                if not user.is_staff:
                    user.shipping_address1=shipping_address1
                    user.shipping_address2=shipping_address2
                user.save()
            if user.is_staff:
                messages.success(request, "Admin edited successfully.")
                return redirect('adminlist')
            else:
                messages.success(request, "Customer edited successfully.")
                return redirect('customerlist')
        
        return render(request, 'edituser.html')


@never_cache
@login_required
@user_passes_test(is_admin)
def update_user_status(request):
    if request.user.is_staff:
        if request.method=='POST':
            user_id=request.POST.get('user_id','').strip()

            user=User.objects.filter(id=user_id).first()
            
            if not user:
                messages.error(request, "User not found.")
                if user.is_staff:
                    return redirect('adminlist')
                else:
                    return redirect('customerlist')
            else:
                if user.is_active == True:
                    user.is_active=False
                    user.save()
                    if user.is_staff:
                        messages.success(request, "Admin deactivated successfully.")
                        return redirect('adminlist')
                    else:
                        messages.success(request, "Customer deactivated successfully.")
                        return redirect('customerlist')
                else:
                    user.is_active=True
                    user.save()
                    if user.is_staff:
                        messages.success(request, "Admin activated successfully.")
                        return redirect('adminlist')
                    else:
                        messages.success(request, "Customer activated successfully.")
                        return redirect('customerlist')

@never_cache
@login_required
def shippingaddress(request):
    """Handle shipping address management from edit profile page"""
    user = request.user
    next_page = request.GET.get("next_page") or request.POST.get("next_page", "editprofile")
    
    phone_pattern1 = r"^98\d{8}$"
    phone_pattern2 = r"^97\d{8}$"

    # CANCEL BUTTON - Handle via GET request
    if request.method == "GET" and request.GET.get('action') == 'cancel':
        return redirect(next_page)

    # SAVE BUTTON (Add or Update)
    if request.method == "POST" and 'btn-save' in request.POST:

        formshippingaddress_id = request.POST.get('formshippingaddress_id', '').strip()

        contact_person = request.POST.get('contact_person', '').strip()
        contact_number = request.POST.get('contact_number', '').strip()
        location_of = request.POST.get('location_of', '').strip()
        province = request.POST.get('province', '').strip()
        district = request.POST.get('district', '').strip()
        city = request.POST.get('city', '').strip()
        location = request.POST.get('location', '').strip()
        landmark = request.POST.get('landmark', '').strip()
        location_description = request.POST.get('location_description', '').strip()

        # Create a simple class to hold the data
        class ShippingAddressData:
            def __init__(self, data):
                for key, value in data.items():
                    setattr(self, key, value)

        shipping_address_obj = ShippingAddressData({
            'id': formshippingaddress_id,
            'contact_person': contact_person,
            'contact_number': contact_number,
            'location_of': location_of,
            'province': province,
            'district': district,
            'city': city,
            'location': location,
            'landmark': landmark,
            'location_description': location_description,
        })

        # Create context BEFORE validation checks
        context = {
            'shippingaddress': shipping_address_obj,
            'next_page': next_page
        }

        # === Validation checks ===
        if not contact_person or not contact_number or not location_of or not province or not district or not city or not location or not landmark:
            messages.error(request, "All fields are required except location description.")
            return render(request, 'shippingaddress.html', context)
        
        if not (re.match(phone_pattern1, contact_number) or re.match(phone_pattern2, contact_number)):
            messages.error(request, "Invalid contact number. Must start with 97 or 98 and be 10 digits long.")
            return render(request, 'shippingaddress.html', context)

        # UPDATE
        if formshippingaddress_id:
            shipping_address = ShippingAddress.objects.filter(id=formshippingaddress_id, user=user).first()

            if not shipping_address:
                messages.error(request, "Shipping address not found.")
                return redirect(next_page)

            shipping_address.contact_person = contact_person
            shipping_address.contact_number = contact_number
            shipping_address.location_of = location_of
            shipping_address.province = province
            shipping_address.district = district
            shipping_address.city = city
            shipping_address.location = location
            shipping_address.landmark = landmark
            shipping_address.location_description = location_description
            shipping_address.save()

            messages.success(request, "Shipping address updated successfully.")

        # ADD NEW
        else:
            if ShippingAddress.objects.filter(user=user).count() >= 2:
                messages.error(request, "You can only have up to 2 shipping addresses.")
                return redirect(next_page)

            ShippingAddress.objects.create(
                user=user,
                contact_person=contact_person,
                contact_number=contact_number,
                location_of=location_of,
                province=province,
                district=district,
                city=city,
                location=location,
                landmark=landmark,
                location_description=location_description
            )

            messages.success(request, "Shipping address added successfully.")

        return redirect(next_page)

    # EDIT BUTTON CLICKED
    elif request.method == "POST":

        shippingaddress_id = request.POST.get('shippingaddress_id')

        shipping_address = ShippingAddress.objects.filter(id=shippingaddress_id, user=user).first()

        if not shipping_address:
            messages.error(request, "Shipping address not found.")
            return redirect(next_page)

        return render(request, 'shippingaddress.html', {
            "shippingaddress": shipping_address,
            "next_page": next_page
        })

    # DEFAULT (Add New)
    return render(request, 'shippingaddress.html', {
        "shippingaddress": None,
        "next_page": next_page
    })


def render_order_page(request, cart_id, user):
    """Helper function to render order.html with all necessary data"""
    # If cart_id is not provided, get user's first active cart
    if not cart_id:
        cart = Cart.objects.filter(user=user).first()
        if not cart:
            messages.error(request, "No active cart found.")
            return redirect("cart_view")
    else:
        cart = get_object_or_404(Cart, id=cart_id, user=user)
    
    cart_items = cart.items.all()
    shipping_address = ShippingAddress.objects.filter(user=user)
    sub_total= cart.total_cart_amount
    shipping_fee = 100 * cart.total_quantity
    total_amount = cart.total_cart_amount + shipping_fee

    return render(request, "order.html", {
        "cart": cart,
        "cart_items": cart_items,
        "shipping_address": shipping_address,
        "shipping_fee": shipping_fee,
        "sub_total":sub_total,
        "total_amount": total_amount,
    })


def render_buy_now_order_page(request, variant_id, quantity, user):
    """Helper function to render buynoworder.html with all necessary data"""
    variant = ProductVariant.objects.filter(id=variant_id).first()
    if not variant:
        messages.error(request, "The selected product variant does not exist.")
        return redirect("home")
    
    quantity = int(quantity) if quantity else 1

    shipping_address = ShippingAddress.objects.filter(user=user)

    # Pricing using product base price
    base_price = variant.product.base_price
    sub_total = base_price * quantity
    shipping_fee = 100 * quantity
    total_amount = sub_total + shipping_fee

    # Render buy now order page with correct template name
    return render(request, "buynoworder.html", {
        "variant": variant,
        "variant_id": variant_id,
        "quantity": quantity,
        "base_price": base_price,
        "sub_total": sub_total,
        "shipping_fee": shipping_fee,
        "total_amount": total_amount,
        "shipping_address": shipping_address,
    })


@never_cache
@login_required
def shippingaddress_order(request):
    """Handle shipping address management from order page"""
    user = request.user
    next_page = request.GET.get("next_page") or request.POST.get("next_page", "order")
    cart_id = request.GET.get("cart_id") or request.POST.get("cart_id", "")
    variant_id = request.GET.get("variant_id") or request.POST.get("variant_id", "")
    quantity = request.GET.get("quantity") or request.POST.get("quantity", "")
    
    phone_pattern1 = r"^98\d{8}$"
    phone_pattern2 = r"^97\d{8}$"

    # CANCEL BUTTON - Handle via GET request
    if request.method == "GET" and request.GET.get('action') == 'cancel':
        if cart_id:
            return render_order_page(request, cart_id, user)
        else:
            return render_buy_now_order_page(request, variant_id, quantity, user)

    # SAVE BUTTON (Add or Update)
    if request.method == "POST" and 'btn-save' in request.POST:

        formshippingaddress_id = request.POST.get('formshippingaddress_id', '').strip()

        contact_person = request.POST.get('contact_person', '').strip()
        contact_number = request.POST.get('contact_number', '').strip()
        location_of = request.POST.get('location_of', '').strip()
        province = request.POST.get('province', '').strip()
        district = request.POST.get('district', '').strip()
        city = request.POST.get('city', '').strip()
        location = request.POST.get('location', '').strip()
        landmark = request.POST.get('landmark', '').strip()
        location_description = request.POST.get('location_description', '').strip()

        # Create a simple class to hold the data
        class ShippingAddressData:
            def __init__(self, data):
                for key, value in data.items():
                    setattr(self, key, value)

        shipping_address_obj = ShippingAddressData({
            'id': formshippingaddress_id,
            'contact_person': contact_person,
            'contact_number': contact_number,
            'location_of': location_of,
            'province': province,
            'district': district,
            'city': city,
            'location': location,
            'landmark': landmark,
            'location_description': location_description,
        })

        # Create context BEFORE validation checks
        context = {
            'shippingaddress': shipping_address_obj,
            'next_page': next_page,
            'cart_id': cart_id,
            'variant_id': variant_id,
            'quantity': quantity
        }

        # === Validation checks ===
        if not contact_person or not contact_number or not location_of or not province or not district or not city or not location or not landmark:
            messages.error(request, "All fields are required except location description.")
            return render(request, 'shippingaddress.html', context)
        
        if not (re.match(phone_pattern1, contact_number) or re.match(phone_pattern2, contact_number)):
            messages.error(request, "Invalid contact number. Must start with 97 or 98 and be 10 digits long.")
            return render(request, 'shippingaddress.html', context)

        # UPDATE
        if formshippingaddress_id:
            shipping_address = ShippingAddress.objects.filter(id=formshippingaddress_id, user=user).first()

            if not shipping_address:
                messages.error(request, "Shipping address not found.")
                if cart_id:
                    return render_order_page(request, cart_id, user)
                else:
                    return render_buy_now_order_page(request, variant_id, quantity, user)

            shipping_address.contact_person = contact_person
            shipping_address.contact_number = contact_number
            shipping_address.location_of = location_of
            shipping_address.province = province
            shipping_address.district = district
            shipping_address.city = city
            shipping_address.location = location
            shipping_address.landmark = landmark
            shipping_address.location_description = location_description
            shipping_address.save()

            messages.success(request, "Shipping address updated successfully.")

        # ADD NEW
        else:
            if ShippingAddress.objects.filter(user=user).count() >= 2:
                messages.error(request, "You can only have up to 2 shipping addresses.")
                if cart_id:
                    return render_order_page(request, cart_id, user)
                else:
                    return render_buy_now_order_page(request, variant_id, quantity, user)

            ShippingAddress.objects.create(
                user=user,
                contact_person=contact_person,
                contact_number=contact_number,
                location_of=location_of,
                province=province,
                district=district,
                city=city,
                location=location,
                landmark=landmark,
                location_description=location_description
            )

            messages.success(request, "Shipping address added successfully.")

        # Return to appropriate page after save
        if cart_id:
            return render_order_page(request, cart_id, user)
        else:
            return render_buy_now_order_page(request, variant_id, quantity, user)

    # EDIT BUTTON CLICKED or ADD NEW BUTTON
    elif request.method == "POST" and 'btn-edit' in request.POST:
        shippingaddress_id = request.POST.get('shippingaddress_id', '')
        
        if shippingaddress_id:
            shipping_address = ShippingAddress.objects.filter(id=shippingaddress_id, user=user).first()

            if not shipping_address:
                messages.error(request, "Shipping address not found.")
                if cart_id:
                    return render_order_page(request, cart_id, user)
                else:
                    return render_buy_now_order_page(request, variant_id, quantity, user)

            return render(request, 'shippingaddress.html', {
                "shippingaddress": shipping_address,
                "next_page": next_page,
                "cart_id": cart_id,
                "variant_id": variant_id,
                "quantity": quantity
            })
        else:
            # ADD NEW button was clicked
            return render(request, 'shippingaddress.html', {
                "shippingaddress": None,
                "next_page": next_page,
                "cart_id": cart_id,
                "variant_id": variant_id,
                "quantity": quantity
            })

    # Default - render appropriate order page
    if cart_id:
        return render_order_page(request, cart_id, user)
    else:
        return render_buy_now_order_page(request, variant_id, quantity, user)
    

@never_cache
@login_required
@user_passes_test(is_admin)
def top_customers(request):
    # Annotate users with total number of orders
    customers = (
        User.objects
        .annotate(total_orders=Count("orders"))
        .filter(total_orders__gt=0)
        .order_by("-total_orders")
    )

    paginator = Paginator(customers, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(request, "admin_topcustomers.html", {
        "page_obj": page_obj
    })