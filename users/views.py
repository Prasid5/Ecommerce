import re
from django.shortcuts import render, redirect,  get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import make_password
from django.views.decorators.cache import never_cache
from django.db.models import Q
from django.core.paginator import Paginator
from carts.models import Cart
from users.models import User, ShippingAddress


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

        # === Validation checks ===
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

@never_cache
def signin(request):
    if request.method == 'POST':
        login_input = request.POST.get('login_input', '').strip().lower()
        password = request.POST.get('password', '').strip()
        context = {'login_input': login_input}

        user_obj = None

        # Try login_input as email
        try:
            user_obj = User.objects.get(email=login_input)
        except User.DoesNotExist:
            # Try login_input as username
            try:
                user_obj = User.objects.get(username=login_input)
            except User.DoesNotExist:
                user_obj = None

        if user_obj:
            # username= maps to USERNAME_FIELD which is email in your model
            user = authenticate(request, username=user_obj.email, password=password)
            if user is not None:
                login(request, user)
                if user.is_staff:
                    return redirect('admindashboard')
                else:
                    return redirect('home')

        messages.error(request, "Invalid email/username or password")
        return render(request, 'signin.html', context)

    return render(request, 'signin.html')

@login_required
def signout(request):
    cart = Cart.objects.filter(user=request.user).first()
    if cart:
        cart.items.all().delete()
        cart.delete()
    logout(request)
    return redirect('signin')


@never_cache
@login_required
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

            context={
                'username':username,
                'email':email,
                'phone':phone
            }
            
            if not username or not email or not password or not phone:
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
                is_staff=True
            )

            user.save()
            messages.success(request, "Admin Created")
            return render(request, 'signin.html')  
        return render(request, 'addadmin.html')


@never_cache
@login_required
def userlist(request, mode=None):
    if request.user.is_staff:
        query = request.GET.get("query", "")
        if mode == "customer":
            users = User.objects.filter(is_staff=False)
        elif mode == "admin":
            users=User.objects.filter(is_staff=True)
        
        users=users.order_by("created_at")#for descending order:-created_at

        if query:
            if query.isdigit():
                users = users.filter(Q(id=int(query)) | Q(username__icontains=query) | Q(email__icontains=query) | Q(phone__icontains=query))#__icontains for case insensitive
            else:
                users = users.filter(Q(username__icontains=query) | Q(email__icontains=query) | Q(phone__icontains=query))#__icontains for case insensitive

        paginator = Paginator(users, 1)
        page_number = request.GET.get("page")#for first-time page load, request.get={}
        page_obj = paginator.get_page(page_number)#for None, Paginator.get_page() default to 1. It also contain page object_list from paginator var

        return render(request, "userlist.html", {
            "page_obj": page_obj,
            "query": query,
            "mode":mode,
        })


@never_cache
@login_required
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
            if not request.user.is_staff:
                shipping_address1=request.POST.get('shipping_address1').strip()
                shipping_address2=request.POST.get('shipping_address2').strip()

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
def deleteuser(request):
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
                user.delete()
                messages.success(request, "User Deleted Successfully.")
                if user.is_staff:
                    messages.success(request, "Admin edited successfully.")
                    return redirect('adminlist')
                else:
                    messages.success(request, "Customer edited successfully.")
                    return redirect('customerlist')


@never_cache
@login_required
def editprofile(request):
    user = request.user  # already the authenticated user
    phone_pattern1 = r"^98\d{8}$"
    phone_pattern2 = r"^97\d{8}$"
    shipping_address = ShippingAddress.objects.filter(user=user).all()
    context = {
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
def shippingaddress(request):
    """Handle shipping address management from edit profile page"""
    user = request.user
    next_page = request.POST.get("next_page", "editprofile")

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
    shipping_fee = 100 * cart.total_quantity
    total_amount = cart.total_cart_amount + shipping_fee

    return render(request, "order.html", {
        "cart": cart,
        "cart_items": cart_items,
        "shipping_address": shipping_address,
        "shipping_fee": shipping_fee,
        "total_amount": total_amount,
    })


@never_cache
@login_required
def shippingaddress_order(request):
    """Handle shipping address management from order page"""
    user = request.user
    next_page = request.POST.get("next_page", "order")
    cart_id = request.POST.get("cart_id")

    # Debug: Print to check if cart_id is being received
    print(f"DEBUG: cart_id = {cart_id}, next_page = {next_page}")

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

        # UPDATE
        if formshippingaddress_id:
            shipping_address = ShippingAddress.objects.filter(id=formshippingaddress_id, user=user).first()

            if not shipping_address:
                messages.error(request, "Shipping address not found.")
                return render_order_page(request, cart_id, user)

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
                return render_order_page(request, cart_id, user)

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

        return render_order_page(request, cart_id, user)

    # EDIT BUTTON CLICKED or ADD NEW BUTTON
    elif request.method == "POST" and 'btn-edit' in request.POST:
        shippingaddress_id = request.POST.get('shippingaddress_id', '')
        
        if shippingaddress_id:
            shipping_address = ShippingAddress.objects.filter(id=shippingaddress_id, user=user).first()

            if not shipping_address:
                messages.error(request, "Shipping address not found.")
                return render_order_page(request, cart_id, user)

            return render(request, 'shippingaddress.html', {
                "shippingaddress": shipping_address,
                "next_page": next_page,
                "cart_id": cart_id
            })
        else:
            # ADD NEW button was clicked
            return render(request, 'shippingaddress.html', {
                "shippingaddress": None,
                "next_page": next_page,
                "cart_id": cart_id
            })

    # Default - render order page
    return render_order_page(request, cart_id, user)