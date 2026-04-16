from functools import wraps
from django.shortcuts import redirect


def staff_required(view_func):
    """Restrict view to staff users only. Redirects to home otherwise."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not request.user.is_staff:
            return redirect('/')
        return view_func(request, *args, **kwargs)
    return wrapper
