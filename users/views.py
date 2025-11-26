import re
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.hashers import make_password
from django.contrib.auth import authenticate, login, logout
from django.views.decorators.cache import never_cache
from django.db.models import Q
from django.core.paginator import Paginator
from users.models import User

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
        
        user= User.objects.create_user(
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

@never_cache
def addadmin(request):
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

def signout(request):
    logout(request)
    return redirect('signin')

def userlist(request, mode=None):
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

def edituserform(request):
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

def edituser(request):
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

        context = {
            'user_id':user_id,
            'username': username,
            'email': email,
            'address': address,
            'phone': phone,
        }

        # === Validation checks ===
        if not username or not email or not address or not phone:
            messages.error(request, "All fields are required.")
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
                user.password=password
            user.address= address
            user.phone= phone
            user.save()
        if user.is_staff:
            messages.success(request, "Admin edited successfully.")
            return redirect('adminlist')
        else:
            messages.success(request, "Customer edited successfully.")
            return redirect('customerlist')
    
    return render(request, 'edituser.html')

def deleteuser(request):
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