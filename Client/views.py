from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views import View
from django.views.generic import ListView, DetailView
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.conf import settings
from django.db.models import Q, Avg
from django.db import transaction
from PIL import Image

from .models import (
    User, Order, Delivery, Payment, Review,
    Complaint, Notification, ChatRoom, Message,
    Service, Category, PortfolioItem
)
from .forms import (
    RegisterForm, LoginForm, ProfileUpdateForm,
    PasswordChangeForm, PasswordResetRequestForm, SetPasswordForm,
    OrderCreateForm, OrderAcceptForm, OrderRejectForm,
    OrderRevisionForm, OrderDisputeForm, OrderCancelForm,
    DeliveryForm, ReviewForm, ComplaintForm, MessageForm,
)



class RegisterView(View):
    def get(self, request):
        return render(request, 'auth/register.html', {'form': RegisterForm()})

    def post(self, request):
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            uid   = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            url   = request.build_absolute_uri(f'/verify-email/{uid}/{token}/')
            send_mail(
                'Email manzilingizni tasdiqlang',
                f'Salom {user.first_name}!\nTasdiqlash havolasi:\n{url}',
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=True,
            )
            messages.success(request, 'Ro\'yxatdan o\'tdingiz! Email tasdiqlash xabarini tekshiring.')
            return redirect('client:login')
        return render(request, 'auth/register.html', {'form': form})


class EmailVerifyView(View):
    def get(self, request, uidb64, token):
        try:
            uid  = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except Exception:
            messages.error(request, 'Noto\'g\'ri havola.')
            return redirect('client:login')
        if default_token_generator.check_token(user, token):
            user.is_verified = True
            user.is_active   = True
            user.save(update_fields=['is_verified', 'is_active'])
            messages.success(request, 'Email tasdiqlandi! Kiring.')
        else:
            messages.error(request, 'Havola eskirgan.')
        return redirect('client:login')


class LoginView(View):
    def get(self, request):
        if request.user.is_authenticated:
            return redirect('client:dashboard')
        return render(request, 'auth/login.html', {'form': LoginForm()})

    def post(self, request):
        form = LoginForm(request.POST)
        if form.is_valid():
            email    = form.cleaned_data['email']
            password = form.cleaned_data['password']
            user     = authenticate(request, username=email, password=password)
            if user:
                if user.is_blocked:
                    messages.error(request, f'Akkauntingiz bloklangan: {user.block_reason or ""}')
                    return render(request, 'auth/login.html', {'form': form})
                login(request, user)
                if not form.cleaned_data.get('remember_me'):
                    request.session.set_expiry(0)
                return redirect(request.GET.get('next', 'client:dashboard'))
            try:
                u = User.objects.get(email=email)
                if not u.is_active:
                    messages.error(request, 'Email tasdiqlanmagan.')
                else:
                    messages.error(request, 'Email yoki parol noto\'g\'ri.')
            except User.DoesNotExist:
                messages.error(request, 'Email yoki parol noto\'g\'ri.')
        return render(request, 'auth/login.html', {'form': form})


class LogoutView(View):
    def post(self, request):
        logout(request)
        return redirect('client:login')





@login_required
def dashboard(request):
    user = request.user
    ctx = {}
    if user.is_client:
        ctx['orders'] = Order.objects.filter(client=user).order_by('-created_at')[:5]
        ctx['unread'] = Notification.objects.filter(recipient=user, is_read=False).count()
    elif user.is_developer:
        ctx['orders'] = Order.objects.filter(developer=user).order_by('-created_at')[:5]
        ctx['unread'] = Notification.objects.filter(recipient=user, is_read=False).count()
    return render(request, 'dashboard.html', ctx)







class ProfileUpdateView(View):
    @staticmethod
    def get(request):
        if not request.user.is_authenticated:
            return redirect('client:login')
        return render(request, 'users/profile_edit.html', {'form': ProfileUpdateForm(instance=request.user)})

    @staticmethod
    def post(request):
        if not request.user.is_authenticated:
            return redirect('client:login')
        form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            user = form.save(commit=False)
            user.save()
            # Resize avatar
            if user.avatar:
                try:
                    img = Image.open(user.avatar.path)
                    img = img.resize((400, 400), Image.LANCZOS)
                    img.save(user.avatar.path)
                except Exception:
                    pass
            messages.success(request, 'Profil yangilandi.')
            return redirect('client:profile_edit')
        return render(request, 'users/profile_edit.html', {'form': form})


class ProfileDetailView(View):
    def get(self, request, username):
        profile = get_object_or_404(User, username=username)
        ctx = {'profile_user': profile}
        if profile.is_developer:
            ctx['services']   = Service.objects.filter(developer=profile, is_active=True)
            ctx['portfolio']  = PortfolioItem.objects.filter(developer=profile)
            ctx['reviews']    = Review.objects.filter(developer=profile).order_by('-created_at')[:10]
            ctx['avg_rating'] = Review.objects.filter(developer=profile).aggregate(avg=Avg('rating'))['avg']
        return render(request, 'users/profile_detail.html', ctx)


class PasswordChangeView(View):
    def get(self, request):
        if not request.user.is_authenticated:
            return redirect('client:login')
        return render(request, 'users/password_change.html', {'form': PasswordChangeForm(request.user)})

    def post(self, request):
        if not request.user.is_authenticated:
            return redirect('client:login')
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Parol o\'zgartirildi.')
            return redirect('client:login')
        return render(request, 'users/password_change.html', {'form': form})


class DeveloperListView(ListView):
    model = User
    template_name = 'users/developer_list.html'
    context_object_name = 'developers'
    paginate_by = 20

    def get_queryset(self):
        qs = User.objects.filter(role=User.ROLE_DEVELOPER, is_active=True, is_blocked=False)
        q = self.request.GET.get('q')
        if q:
            qs = qs.filter(
                Q(first_name__icontains=q) | Q(last_name__icontains=q) |
                Q(bio__icontains=q) | Q(skills__icontains=q)
            )
        return qs.order_by('-created_at')






class ServiceListView(ListView):
    model = Service
    template_name = 'services/list.html'
    context_object_name = 'services'
    paginate_by = 20

    def get_queryset(self):
        qs = Service.objects.filter(is_active=True).select_related('developer', 'category')
        q        = self.request.GET.get('q')
        cat      = self.request.GET.get('category')
        min_p    = self.request.GET.get('min_price')
        max_p    = self.request.GET.get('max_price')
        sort     = self.request.GET.get('sort', '-created_at')

        if q:   qs = qs.filter(Q(title__icontains=q) | Q(description__icontains=q))
        if cat: qs = qs.filter(category__slug=cat)
        if min_p:
            try: qs = qs.filter(price__gte=float(min_p))
            except ValueError: pass
        if max_p:
            try: qs = qs.filter(price__lte=float(max_p))
            except ValueError: pass
        if sort in ['-created_at', 'price', '-price', '-orders_count']:
            qs = qs.order_by(sort)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['categories'] = Category.objects.filter(is_active=True)
        return ctx


class ServiceDetailView(View):
    def get(self, request, pk):
        service = get_object_or_404(Service, pk=pk, is_active=True)
        service.increment_views()
        reviews   = Review.objects.filter(developer=service.developer).order_by('-created_at')[:5]
        portfolio = PortfolioItem.objects.filter(developer=service.developer)
        return render(request, 'services/detail.html', {
            'service': service, 'reviews': reviews, 'portfolio': portfolio
        })






class OrderCreateView(View):
    @transaction.atomic
    def post(self, request, service_id):
        if not request.user.is_authenticated:
            return redirect('client:login')
        if not request.user.is_client:
            messages.error(request, 'Faqat mijozlar buyurtma bera oladi.')
            return redirect('client:service_list')
        service = get_object_or_404(Service, pk=service_id, is_active=True)
        form    = OrderCreateForm(request.POST)
        if form.is_valid():
            order = form.save(commit=False)
            order.client    = request.user
            order.developer = service.developer
            order.service   = service
            order.price     = service.price
            order.status    = Order.STATUS_PENDING
            order.save()
            # Escrow yaratish
            Payment.create_for_order(order)
            messages.success(request, 'Buyurtma yuborildi! Dasturchi qabul qilishini kuting.')
            return redirect('client:order_detail', pk=order.pk)
        return redirect('client:service_detail', pk=service_id)

    def get(self, request, service_id):
        service = get_object_or_404(Service, pk=service_id, is_active=True)
        return render(request, 'orders/create.html', {
            'service': service, 'form': OrderCreateForm()
        })


class OrderListView(View):
    def get(self, request):
        if not request.user.is_authenticated:
            return redirect('client:login')
        user   = request.user
        status = request.GET.get('status')
        if user.is_client:
            qs = Order.objects.filter(client=user)
        elif user.is_developer:
            qs = Order.objects.filter(developer=user)
        else:
            qs = Order.objects.all()
        if status:
            qs = qs.filter(status=status)
        qs = qs.order_by('-created_at').select_related('service', 'client', 'developer')
        return render(request, 'orders/list.html', {'orders': qs, 'status_filter': status})


class OrderDetailView(View):
    def get(self, request, pk):
        if not request.user.is_authenticated:
            return redirect('client:login')
        order = get_object_or_404(Order, pk=pk)
        if request.user not in [order.client, order.developer] and not request.user.is_staff:
            messages.error(request, 'Ruxsatingiz yo\'q.')
            return redirect('client:order_list')
        deliveries = order.deliveries.order_by('-created_at')
        chat_room  = getattr(order, 'chatroom', None)
        msgs       = chat_room.messages.order_by('created_at') if chat_room else []
        has_review = hasattr(order, 'review')
        ctx = {
            'order': order, 'deliveries': deliveries,
            'messages': msgs, 'message_form': MessageForm(),
            'has_review': has_review,
            'accept_form':   OrderAcceptForm(),
            'reject_form':   OrderRejectForm(),
            'revision_form': OrderRevisionForm(),
            'dispute_form':  OrderDisputeForm(),
            'cancel_form':   OrderCancelForm(),
            'delivery_form': DeliveryForm(),
        }
        return render(request, 'orders/detail.html', ctx)


class OrderAcceptView(View):
    def post(self, request, pk):
        if not request.user.is_authenticated:
            return redirect('client:login')
        order = get_object_or_404(Order, pk=pk, developer=request.user, status=Order.STATUS_PENDING)
        form  = OrderAcceptForm(request.POST)
        if form.is_valid():
            order.accept(form.cleaned_data['deadline_days'])
            messages.success(request, 'Buyurtma qabul qilindi.')
        return redirect('client:order_detail', pk=pk)


class OrderRejectView(View):
    def post(self, request, pk):
        if not request.user.is_authenticated:
            return redirect('client:login')
        order = get_object_or_404(Order, pk=pk, developer=request.user, status=Order.STATUS_PENDING)
        form  = OrderRejectForm(request.POST)
        if form.is_valid():
            order.reject(form.cleaned_data['reason'])
            messages.info(request, 'Buyurtma rad etildi.')
        return redirect('client:order_list')


class OrderDeliverView(View):
    def post(self, request, pk):
        if not request.user.is_authenticated:
            return redirect('client:login')
        order = get_object_or_404(
            Order, pk=pk, developer=request.user,
            status__in=[Order.STATUS_ACTIVE, Order.STATUS_REVISION]
        )
        form = DeliveryForm(request.POST, request.FILES)
        if form.is_valid():
            # versiya raqami
            last_version = order.deliveries.count()
            Delivery.objects.create(
                order=order,
                developer=request.user,
                delivery_file=form.cleaned_data.get('delivery_file'),
                delivery_url=form.cleaned_data.get('delivery_url'),
                message=form.cleaned_data.get('message'),
                version=last_version + 1,
            )
            order.deliver()
            messages.success(request, 'Ish topshirildi!')
        return redirect('client:order_detail', pk=pk)


class OrderCompleteView(View):
    def post(self, request, pk):
        if not request.user.is_authenticated:
            return redirect('client:login')
        order = get_object_or_404(Order, pk=pk, client=request.user, status=Order.STATUS_DELIVERED)
        order.complete()
        messages.success(request, 'Buyurtma tugallandi. To\'lov dasturchiga o\'tkazildi.')
        return redirect('client:order_detail', pk=pk)


class OrderRevisionView(View):
    def post(self, request, pk):
        if not request.user.is_authenticated:
            return redirect('client:login')
        order = get_object_or_404(Order, pk=pk, client=request.user, status=Order.STATUS_DELIVERED)
        form  = OrderRevisionForm(request.POST)
        if form.is_valid():
            order.request_revision(form.cleaned_data['reason'])
            messages.info(request, 'Tuzatish so\'raldi.')
        return redirect('client:order_detail', pk=pk)


class OrderDisputeView(View):
    def post(self, request, pk):
        if not request.user.is_authenticated:
            return redirect('client:login')
        order = get_object_or_404(
            Order, pk=pk, client=request.user,
            status__in=[Order.STATUS_DELIVERED, Order.STATUS_REVISION]
        )
        form = OrderDisputeForm(request.POST)
        if form.is_valid():
            order.open_dispute(form.cleaned_data['reason'])
            messages.warning(request, 'Nizo ochildi. Admin ko\'rib chiqadi.')
        return redirect('client:order_detail', pk=pk)


class OrderCancelView(View):
    def post(self, request, pk):
        if not request.user.is_authenticated:
            return redirect('client:login')
        order = get_object_or_404(
            Order, pk=pk,
            status__in=[Order.STATUS_PENDING, Order.STATUS_ACTIVE]
        )
        if request.user not in [order.client, order.developer] and not request.user.is_staff:
            messages.error(request, 'Ruxsatingiz yo\'q.')
            return redirect('client:order_list')
        form = OrderCancelForm(request.POST)
        if form.is_valid():
            order.cancel(form.cleaned_data['reason'])
            messages.info(request, 'Buyurtma bekor qilindi.')
        return redirect('client:order_list')



class ChatView(View):
    def get(self, request, pk):
        if not request.user.is_authenticated:
            return redirect('client:login')
        order = get_object_or_404(Order, pk=pk)
        if request.user not in [order.client, order.developer] and not request.user.is_staff:
            messages.error(request, 'Ruxsatingiz yo\'q.')
            return redirect('client:order_list')
        room, _ = ChatRoom.objects.get_or_create(order=order)
        msgs     = room.messages.order_by('created_at')
        room.messages.filter(is_read=False).exclude(sender=request.user).update(is_read=True)
        return render(request, 'chat/chat.html', {
            'order': order, 'room': room, 'messages': msgs, 'form': MessageForm()
        })

    def post(self, request, pk):
        if not request.user.is_authenticated:
            return redirect('client:login')
        order = get_object_or_404(Order, pk=pk)
        room, _ = ChatRoom.objects.get_or_create(order=order)
        form = MessageForm(request.POST, request.FILES)
        if form.is_valid():
            Message.objects.create(
                room=room,
                sender=request.user,
                text=form.cleaned_data.get('text'),
                file=form.cleaned_data.get('file'),
            )
        return redirect('client:chat', pk=pk)



class PaymentHistoryView(View):
    def get(self, request):
        if not request.user.is_authenticated:
            return redirect('client:login')
        if request.user.is_client:
            payments = Payment.objects.filter(client=request.user)
        elif request.user.is_developer:
            payments = Payment.objects.filter(developer=request.user)
        else:
            payments = Payment.objects.all()
        status = request.GET.get('status')
        if status:
            payments = payments.filter(status=status)
        return render(request, 'payments/history.html', {'payments': payments.order_by('-created_at')})



class ReviewCreateView(View):
    def get(self, request, order_id):
        if not request.user.is_authenticated:
            return redirect('client:login')
        order = get_object_or_404(Order, pk=order_id, client=request.user, status=Order.STATUS_COMPLETED)
        if hasattr(order, 'review'):
            messages.error(request, 'Siz bu buyurtmaga allaqachon sharh qoldirgansiz.')
            return redirect('client:order_detail', pk=order_id)
        return render(request, 'reviews/create.html', {'form': ReviewForm(), 'order': order})

    def post(self, request, order_id):
        if not request.user.is_authenticated:
            return redirect('client:login')
        order = get_object_or_404(Order, pk=order_id, client=request.user, status=Order.STATUS_COMPLETED)
        if hasattr(order, 'review'):
            messages.error(request, 'Allaqachon sharh qoldirilgan.')
            return redirect('client:order_detail', pk=order_id)
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.order     = order
            review.client    = request.user
            review.developer = order.developer
            review.save()
            messages.success(request, 'Sharh qoldirildi.')
            return redirect('client:order_detail', pk=order_id)
        return render(request, 'reviews/create.html', {'form': form, 'order': order})


class ReviewUpdateView(View):
    def get(self, request, pk):
        if not request.user.is_authenticated:
            return redirect('client:login')
        review = get_object_or_404(Review, pk=pk, client=request.user)
        if review.is_edited:
            messages.error(request, 'Sharhni faqat bir marta tahrirlash mumkin.')
            return redirect('client:order_detail', pk=review.order.pk)
        return render(request, 'reviews/edit.html', {'form': ReviewForm(instance=review), 'review': review})

    def post(self, request, pk):
        if not request.user.is_authenticated:
            return redirect('client:login')
        review = get_object_or_404(Review, pk=pk, client=request.user)
        if review.is_edited:
            messages.error(request, 'Faqat bir marta tahrirlash mumkin.')
            return redirect('client:order_detail', pk=review.order.pk)
        form = ReviewForm(request.POST, instance=review)
        if form.is_valid():
            r = form.save(commit=False)
            r.is_edited = True
            from django.utils import timezone
            r.edited_at = timezone.now()
            r.save()
            messages.success(request, 'Sharh yangilandi.')
            return redirect('client:order_detail', pk=review.order.pk)
        return render(request, 'reviews/edit.html', {'form': form, 'review': review})



class ComplaintCreateView(View):
    def get(self, request):
        if not request.user.is_authenticated:
            return redirect('client:login')
        return render(request, 'complaints/create.html', {'form': ComplaintForm()})

    def post(self, request):
        if not request.user.is_authenticated:
            return redirect('client:login')
        form = ComplaintForm(request.POST)
        if form.is_valid():
            reported = form.cleaned_data['reported_user']
            if reported == request.user:
                messages.error(request, 'O\'zingizga shikoyat qila olmaysiz.')
                return render(request, 'complaints/create.html', {'form': form})
            complaint = form.save(commit=False)
            complaint.reporter = request.user
            complaint.save()
            messages.success(request, 'Shikoyat yuborildi. Admin ko\'rib chiqadi.')
            return redirect('client:dashboard')
        return render(request, 'complaints/create.html', {'form': form})


class ComplaintListView(View):
    def get(self, request):
        if not request.user.is_authenticated:
            return redirect('client:login')
        complaints = Complaint.objects.filter(reporter=request.user).order_by('-created_at')
        return render(request, 'complaints/list.html', {'complaints': complaints})



class NotificationListView(View):
    def get(self, request):
        if not request.user.is_authenticated:
            return redirect('client:login')
        notifs = Notification.objects.filter(recipient=request.user).order_by('-created_at')
        filter_type = request.GET.get('filter')
        if filter_type == 'unread':
            notifs = notifs.filter(is_read=False)
        from django.core.paginator import Paginator
        paginator = Paginator(notifs, 20)
        page = request.GET.get('page')
        page_obj = paginator.get_page(page)
        return render(request, 'notifications/list.html', {'page_obj': page_obj})


class MarkNotificationRead(View):
    def post(self, request, pk):
        if not request.user.is_authenticated:
            return redirect('client:login')
        notif = get_object_or_404(Notification, pk=pk, recipient=request.user)
        notif.is_read = True
        notif.save(update_fields=['is_read'])
        from django.http import JsonResponse
        return JsonResponse({'status': 'ok'})


class MarkAllRead(View):
    def post(self, request):
        if not request.user.is_authenticated:
            return redirect('client:login')
        Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
        messages.success(request, 'Barcha bildirishnomalar o\'qildi.')
        return redirect('client:notifications')


class UnreadCountView(View):
    def get(self, request):
        from django.http import JsonResponse
        if not request.user.is_authenticated:
            return JsonResponse({'count': 0})
        count = Notification.objects.filter(recipient=request.user, is_read=False).count()
        return JsonResponse({'count': count})