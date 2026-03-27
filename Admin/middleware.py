# ──────────────────────────────────────────────
# 1. settings.py ga qo'shing:
# ──────────────────────────────────────────────
#
# LOGIN_URL = '/login/'
# LOGIN_REDIRECT_URL = '/'
# LOGOUT_REDIRECT_URL = '/'
#
# AUTH_USER_MODEL = 'core.User'   # agar hali yo'q bo'lsa


# ──────────────────────────────────────────────
# 2. views.py — Login view (rol bo'yicha redirect)
# ──────────────────────────────────────────────

from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.http import HttpResponseForbidden
from django.contrib.auth import logout
from django.shortcuts import redirect


class AdminAccessMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith('/admin/'):
            if request.user.is_authenticated:
                if not (request.user.is_staff or request.user.role == 'admin'):
                    logout(request)
                    return redirect('/login/?next=/admin/')
        return self.get_response(request)


def role_based_redirect(user):
    """Foydalanuvchi roliga qarab to'g'ri sahifaga yo'naltiradi."""
    if user.is_staff or user.role == 'admin':
        return '/admin/'
    elif user.role == 'developer':
        return '/dashboard/developer/'
    else:
        return '/dashboard/client/'


def login_view(request):
    """
    Login bo'lgandan so'ng rolga qarab yo'naltiradi.
    Admin bo'lsa /admin/ ga, boshqalar o'z dashboard'iga.
    """
    if request.user.is_authenticated:
        return redirect(role_based_redirect(request.user))

    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        user = authenticate(request, username=email, password=password)
        if user:
            login(request, user)
            next_url = request.GET.get('next')
            # 'next' parametri bo'lsa lekin admin bo'lmasa, xavfsizlik uchun tekshir
            if next_url and next_url.startswith('/admin/') and not user.is_staff:
                return redirect('/')
            return redirect(next_url or role_based_redirect(user))

    # GET yoki login xato bo'lsa
    from django.shortcuts import render
    return render(request, 'auth/login.html', {})


def logout_view(request):
    """
    Logout bo'lgandan so'ng session'ni tozalaydi va login sahifasiga yo'naltiradi.
    Admin panel session ham tozalanadi.
    """
    logout(request)
    return redirect('/login/')


# ──────────────────────────────────────────────
# 3. Registration view — Rol o'rnatish
# ──────────────────────────────────────────────

def register_view(request):
    from django.shortcuts import render
    from .models import User

    if request.method == 'POST':
        role = request.POST.get('role', 'client')  # form'dan keladi

        # Faqat ruxsat etilgan rollar
        if role not in ['client', 'developer']:
            role = 'client'

        user = User.objects.create_user(
            email=request.POST.get('email'),
            username=request.POST.get('email'),  # yoki alohida username
            password=request.POST.get('password'),
            first_name=request.POST.get('first_name', ''),
            last_name=request.POST.get('last_name', ''),
            role=role,  # ← ROL SHU YERDA O'RNATILADI
        )
        login(request, user)
        return redirect(role_based_redirect(user))

    return render(request, 'auth/register.html', {})


# ──────────────────────────────────────────────
# 4. Middleware — Admin panelga faqat admin kira olsin
# ──────────────────────────────────────────────

class AdminAccessMiddleware:
    """
    /admin/ yo'liga faqat is_staff=True yoki role='admin' bo'lgan
    foydalanuvchilar kira oladi.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith('/admin/'):
            if request.user.is_authenticated:
                if not (request.user.is_staff or request.user.role == 'admin'):
                    # Admin bo'lmagan foydalanuvchi /admin/ ga kirmoqchi
                    logout(request)
                    return redirect('/login/?next=/admin/')
        return self.get_response(request)


# ──────────────────────────────────────────────
# 5. Decorator — Developer bo'lishi shart bo'lgan view'lar uchun
# ──────────────────────────────────────────────

def developer_required(view_func):
    """Faqat developer role'idagi foydalanuvchilar uchun."""
    @login_required
    def wrapper(request, *args, **kwargs):
        if request.user.role != 'developer':
            return HttpResponseForbidden('Bu sahifa faqat dasturchilarga mo\'ljallangan.')
        return view_func(request, *args, **kwargs)
    return wrapper


def client_required(view_func):
    """Faqat client role'idagi foydalanuvchilar uchun."""
    @login_required
    def wrapper(request, *args, **kwargs):
        if request.user.role != 'client':
            return HttpResponseForbidden('Bu sahifa faqat mijozlarga mo\'ljallangan.')
        return view_func(request, *args, **kwargs)
    return wrapper


# ──────────────────────────────────────────────
# 6. settings.py ga middleware qo'shing:
# ──────────────────────────────────────────────
#
# MIDDLEWARE = [
#     ...
#     'core.views.AdminAccessMiddleware',   # ← shu qatorni qo'shing
#     ...
# ]
#
# Yoki middleware alohida fayl bo'lsa:
# MIDDLEWARE = [
#     ...
#     'core.middleware.AdminAccessMiddleware',
#     ...
# ]