import re
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.hashers import make_password
from django.contrib.auth import authenticate, login, logout
from users.models import User
from django.views.decorators.cache import never_cache

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
            password=make_password(password),
            address=address,
            phone=phone,
            role='customer'
        )

        user.save()
        messages.success(request, "Account created successfully")
        return redirect(signin)
    
    return render(request, 'signup.html')

@never_cache
def signin(request):
    if request.method == 'POST':
        login_input=request.POST.get('login_input','').strip().lower()
        password=request.POST.get('password','').strip()
        context={
            'login_input':login_input,
            'password':password
        }

        try:
            user_obj = User.objects.get(email=login_input)
            user = authenticate(request, email=user_obj.email, password=password)

        except User.DoesNotExist:
            try:
                user_obj = User.objects.get(username=login_input)
                user = authenticate(request, email=user_obj.email, password=password)
            except User.DoesNotExist:
                user = None

        if user is not None:
            login(request, user)
            if user.is_staff:
                return redirect('admindashboard')
            else:
                return redirect('home')
        else:
            messages.error(request, "Invalid email or password")
            return render(request, 'signin.html', context)

    return render(request, 'signin.html')

def signout(request):
    logout(request)
    return redirect('signin')
