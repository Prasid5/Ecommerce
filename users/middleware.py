# users/middleware.py
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth import logout
from django.urls import reverse

class SingleSessionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # 🚫 Skip middleware for login page
        if request.path in [reverse('signin')]:
            return self.get_response(request)

        if request.user.is_authenticated:
            current_key = request.session.session_key

            # Ensure session exists
            if not current_key:
                logout(request)
                messages.error(request, "Session expired. Please log in again.")
                return redirect('signin')

            # Detect login from another device
            if request.user.active_session_key != current_key:
                logout(request)
                messages.error(
                    request,
                    "Your account was logged in from another device."
                )
                return redirect('signin')

        return self.get_response(request)
