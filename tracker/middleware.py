# tracker/middleware.py
from django.shortcuts import redirect

class RestrictAdminMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # 1. Allow access to the login/logout pages so users can authenticate
        if request.path.startswith('/admin/login/'):
            return self.get_response(request)

        if request.path.startswith('/admin/logout/'):
            return self.get_response(request)


        # 2. Intercept all other /admin/ pages
        if request.path.startswith('/admin/'):
            user = request.user
            
            # Unauthenticated users -> redirect to dashboard
            if not user.is_authenticated:
                return redirect('dashboard')

            # Check if user is in a "bread maker" / "bread makers" group (case-insensitive)
            is_bread_maker = user.groups.filter(name__icontains='bread maker').exists()

            # If they are in the bread maker group OR simply not a superuser -> redirect to dashboard
            if is_bread_maker or not user.is_superuser:
                return redirect('dashboard')

        return self.get_response(request)
