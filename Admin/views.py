from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views import View
from django.db.models import Q, Count, Sum, Avg
from django.core.paginator import Paginator
from django.core.exceptions import PermissionDenied
from django.utils import timezone
from django.http import JsonResponse

from Client.models import (
    User, Order, Payment, Complaint, Notification,
    Service, Review, PlatformSettings
)
from django.views.generic import ListView
from django.contrib.auth.mixins import UserPassesTestMixin, LoginRequiredMixin


class AdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_authenticated and (self.request.user.is_staff or self.request.user.role == 'admin')

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return redirect('login')
        messages.error(self.request, "Bu sahifaga kirish uchun admin huquqi kerak.")
        return redirect('dashboard')


# 1. Barcha buyurtmalar monitoringi
class AdminOrderListView(AdminRequiredMixin, ListView):
    model = Order
    template_name = 'admin_panel/order_list.html'
    context_object_name = 'orders'
    paginate_by = 10

    def get_queryset(self):
        queryset = Order.objects.all().order_by('-created_at')
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        return queryset


# 2. Xizmatlar (Gigs) ro'yxati
class AdminServiceListView(ListView):
    model = Service
    template_name = 'admin_panel/service_list.html'
    context_object_name = 'services'
    paginate_by = 12

    def get_queryset(self):
        # Faqat faol va o'chirilmagan xizmatlarni chiqarish
        return Service.objects.filter(is_active=True).order_by('-created_at')


class AdminDashboardView(View):
    def get(self, request):
        total_profit = Order.objects.filter(status='completed').aggregate(Sum('price'))['price__sum'] or 0
        active_services = Service.objects.filter(is_active=True).count()
        avg_check = Order.objects.filter(status='completed').aggregate(Avg('price'))['price__avg'] or 0
        unread_notifications = Notification.objects.filter(is_read=False).count()
        total_orders = Order.objects.count()
        clients_count = User.objects.filter(role='client').count()
        developers_count = User.objects.filter(role='developer').count()
        blocked_count = User.objects.filter(is_active=False).count()
        pending_complaints = Complaint.objects.filter(status='pending').count()
        hold_amount = Payment.objects.filter(status='held').aggregate(Sum('amount'))['amount__sum'] or 0
        dispute_orders = Order.objects.filter(status='dispute').count()
        recent_orders = Order.objects.all().order_by('-created_at')[:10]

        context = {
            'total_profit': total_profit,
            'active_services_count': active_services,
            'avg_order_value': avg_check,
            'unread_notifications': unread_notifications,
            'total_orders_count': total_orders,
            'clients_count': clients_count,
            'developers_count': developers_count,
            'blocked_count': blocked_count,
            'pending_complaints': pending_complaints,
            'hold_amount': hold_amount,
            'dispute_orders': dispute_orders,
            'recent_orders': recent_orders,
        }
        return render(request, 'admin_panel/dashboard.html', context)


class AdminUserListView(AdminRequiredMixin, View):
    def get(self, request):
        qs = User.objects.all().order_by('-created_at')

        q      = request.GET.get('q')
        role   = request.GET.get('role')
        status = request.GET.get('status')

        if q:
            qs = qs.filter(
                Q(email__icontains=q) |
                Q(first_name__icontains=q) |
                Q(last_name__icontains=q) |
                Q(username__icontains=q)
            )
        if role in [User.ROLE_CLIENT, User.ROLE_DEVELOPER, User.ROLE_ADMIN]:
            qs = qs.filter(role=role)
        if status == 'blocked':
            qs = qs.filter(is_blocked=True)
        elif status == 'active':
            qs = qs.filter(is_blocked=False, is_active=True)
        elif status == 'unverified':
            qs = qs.filter(is_verified=False)

        paginator = Paginator(qs, 20)
        page_obj  = paginator.get_page(request.GET.get('page'))
        return render(request, 'admin_panel/user_list.html', {
            'page_obj': page_obj,
            'q': q or '',
            'role_filter': role or '',
            'status_filter': status or '',
        })


class AdminUserDetailView(AdminRequiredMixin, View):
    def get(self, request, pk):
        user = get_object_or_404(User,   pk=pk)
        client_orders    = Order.objects.filter(client=user).order_by('-created_at')[:10]
        developer_orders = Order.objects.filter(developer=user).order_by('-created_at')[:10]
        payments         = Payment.objects.filter(
            Q(client=user) | Q(developer=user)
        ).order_by('-created_at')[:10]
        complaints_filed    = Complaint.objects.filter(reporter=user).order_by('-created_at')[:5]
        complaints_received = Complaint.objects.filter(reported_user=user).order_by('-created_at')[:5]

        ctx = {
            'target_user': user,
            'client_orders': client_orders,
            'developer_orders': developer_orders,
            'payments': payments,
            'complaints_filed': complaints_filed,
            'complaints_received': complaints_received,
        }
        return render(request, 'admin_panel/user_detail.html', ctx)


class AdminBlockUserView(AdminRequiredMixin, View):
    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        if user.is_staff:
            messages.error(request, 'Admin foydalanuvchini bloklash mumkin emas.')
            return redirect('admin_panel:user_detail', pk=pk)

        if user.is_blocked:
            user.is_blocked   = False
            user.block_reason = ''
            user.save(update_fields=['is_blocked', 'block_reason'])
            messages.success(request, f'{user.email} blokdan chiqarildi.')
        else:
            reason = request.POST.get('reason', '').strip()
            if not reason:
                messages.error(request, 'Bloklash sababi kiritilishi shart.')
                return redirect('admin_panel:user_detail', pk=pk)
            user.is_blocked   = True
            user.block_reason = reason
            user.save(update_fields=['is_blocked', 'block_reason'])
            Notification.send(
                recipient=user,
                type='account_blocked',
                title='Akkauntingiz bloklandi',
                message=f'Sabab: {reason}',
            )
            messages.success(request, f'{user.email} bloklandi.')
        return redirect('admin_panel:user_detail', pk=pk)


class AdminChangeRoleView(AdminRequiredMixin, View):
    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        new_role = request.POST.get('role')
        allowed  = [User.ROLE_CLIENT, User.ROLE_DEVELOPER, User.ROLE_ADMIN]
        if new_role not in allowed:
            messages.error(request, 'Noto\'g\'ri rol.')
            return redirect('admin_panel:user_detail', pk=pk)
        user.role = new_role
        user.save(update_fields=['role'])
        messages.success(request, f'Rol o\'zgartirildi: {user.get_role_display()}')
        return redirect('admin_panel:user_detail', pk=pk)



class AdminPaymentListView(AdminRequiredMixin, View):
    def get(self, request):
        qs = Payment.objects.all().select_related(
            'order', 'client', 'developer'
        ).order_by('-created_at')

        status     = request.GET.get('status')
        date_from  = request.GET.get('date_from')
        date_to    = request.GET.get('date_to')
        q          = request.GET.get('q')

        if status:
            qs = qs.filter(status=status)
        if date_from:
            qs = qs.filter(created_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(created_at__date__lte=date_to)
        if q:
            qs = qs.filter(
                Q(client__email__icontains=q) |
                Q(developer__email__icontains=q)
            )

        paginator = Paginator(qs, 20)
        page_obj  = paginator.get_page(request.GET.get('page'))
        return render(request, 'admin_panel/payment_list.html', {
            'page_obj': page_obj,
            'status_filter': status or '',
        })


class AdminReleasePaymentView(AdminRequiredMixin, View):
    def post(self, request, pk):
        payment = get_object_or_404(Payment, pk=pk, status=Payment.STATUS_HOLD)
        note    = request.POST.get('note', '')
        payment.release_to_developer(admin=request.user)
        if note:
            payment.admin_note = note
            payment.save(update_fields=['admin_note'])

        if payment.order.status != Order.STATUS_COMPLETED:
            payment.order.complete()
        messages.success(request, f'To\'lov dasturchiga o\'tkazildi: {payment.developer_amount} so\'m')
        return redirect('admin_panel:payment_list')


class AdminRefundPaymentView(AdminRequiredMixin, View):
    def post(self, request, pk):
        payment = get_object_or_404(Payment, pk=pk, status=Payment.STATUS_HOLD)
        note    = request.POST.get('note', '').strip()
        payment.refund_to_client(admin=request.user, note=note)
        Notification.send(
            recipient=payment.client,
            type='payment_refunded',
            title='To\'lov qaytarildi',
            message=f'{payment.amount} so\'m hisobingizga qaytarildi. Admin: {note}',
            order=payment.order,
        )
        messages.success(request, f'To\'lov clientga qaytarildi: {payment.amount} so\'m')
        return redirect('admin_panel:payment_list')


class AdminArbitrajView(AdminRequiredMixin, View):
    def get(self, request):
        disputes = Order.objects.filter(status=Order.STATUS_DISPUTE).select_related(
            'client', 'developer', 'service'
        ).order_by('-updated_at')
        return render(request, 'admin_panel/arbitraj.html', {'disputes': disputes})

    def post(self, request, pk):
        order   = get_object_or_404(Order, pk=pk, status=Order.STATUS_DISPUTE)
        decision = request.POST.get('decision')  # 'release' yoki 'refund'
        note    = request.POST.get('note', '').strip()

        if decision == 'release':
            order.payment.release_to_developer(admin=request.user)
            order.complete()
            Notification.send(
                recipient=order.developer,
                type='payment_released',
                title='Nizo hal qilindi — Sizning foydangizga',
                message=f'Admin qaror qildi: {note}',
                order=order,
            )
            Notification.send(
                recipient=order.client,
                type='order_completed',
                title='Nizo hal qilindi',
                message=f'Admin qaroriga ko\'ra to\'lov dasturchiga o\'tkazildi. {note}',
                order=order,
            )
            messages.success(request, 'Nizo hal qilindi: to\'lov dasturchiga o\'tkazildi.')
        elif decision == 'refund':
            order.payment.refund_to_client(admin=request.user, note=note)
            order.status = Order.STATUS_REFUNDED
            order.save(update_fields=['status'])
            Notification.send(
                recipient=order.client,
                type='payment_refunded',
                title='Nizo hal qilindi — To\'lov qaytarildi',
                message=f'Admin qaror qildi: {note}',
                order=order,
            )
            Notification.send(
                recipient=order.developer,
                type='order_cancelled',
                title='Nizo hal qilindi',
                message=f'Admin qaroriga ko\'ra to\'lov clientga qaytarildi. {note}',
                order=order,
            )
            messages.success(request, 'Nizo hal qilindi: to\'lov clientga qaytarildi.')
        else:
            messages.error(request, 'Noto\'g\'ri qaror.')

        return redirect('admin_panel:arbitraj')





class AdminComplaintListView(AdminRequiredMixin, View):
    def get(self, request):
        qs = Complaint.objects.all().select_related(
            'reporter', 'reported_user', 'order'
        ).order_by('-created_at')

        status = request.GET.get('status')
        reason = request.GET.get('reason')
        q      = request.GET.get('q')

        if status:
            qs = qs.filter(status=status)
        if reason:
            qs = qs.filter(reason=reason)
        if q:
            qs = qs.filter(
                Q(reporter__email__icontains=q) |
                Q(reported_user__email__icontains=q) |
                Q(description__icontains=q)
            )

        paginator = Paginator(qs, 20)
        page_obj  = paginator.get_page(request.GET.get('page'))
        return render(request, 'admin_panel/complaint_list.html', {
            'page_obj': page_obj,
            'status_filter': status or '',
            'reason_filter': reason or '',
        })


class AdminComplaintDetailView(AdminRequiredMixin, View):
    def get(self, request, pk):
        complaint = get_object_or_404(Complaint, pk=pk)
        reporter_orders  = Order.objects.filter(
            Q(client=complaint.reporter) | Q(developer=complaint.reporter)
        ).order_by('-created_at')[:5]
        reported_orders  = Order.objects.filter(
            Q(client=complaint.reported_user) | Q(developer=complaint.reported_user)
        ).order_by('-created_at')[:5]

        ctx = {
            'complaint': complaint,
            'reporter_orders': reporter_orders,
            'reported_orders': reported_orders,
        }
        return render(request, 'admin_panel/complaint_detail.html', ctx)


class AdminResolveComplaintView(AdminRequiredMixin, View):
    def post(self, request, pk):
        complaint = get_object_or_404(Complaint, pk=pk)
        action    = request.POST.get('action')  # 'resolve' yoki 'dismiss'
        decision  = request.POST.get('decision', 'dismissed')
        note      = request.POST.get('note', '').strip()

        if action == 'resolve':
            complaint.resolve(admin=request.user, decision=decision, note=note)

            if decision == 'blocked':
                reported = complaint.reported_user
                reported.is_blocked   = True
                reported.block_reason = f'Shikoyat asosida bloklandi: {note}'
                reported.save(update_fields=['is_blocked', 'block_reason'])
                Notification.send(
                    recipient=reported,
                    type='account_blocked',
                    title='Akkauntingiz bloklandi',
                    message=f'Sabab: {note}',
                )

            Notification.send(
                recipient=complaint.reporter,
                type='complaint_new',
                title='Shikoyatingiz ko\'rib chiqildi',
                message=f'Qaror: {complaint.get_decision_display() if complaint.decision else decision}. {note}',
            )
            messages.success(request, 'Shikoyat hal qilindi.')
        elif action == 'dismiss':
            complaint.dismiss(admin=request.user, note=note)
            Notification.send(
                recipient=complaint.reporter,
                type='complaint_new',
                title='Shikoyatingiz rad etildi',
                message=f'Admin izohi: {note}',
            )
            messages.info(request, 'Shikoyat rad etildi.')
        else:
            messages.error(request, 'Noto\'g\'ri harakat.')

        return redirect('admin_panel:complaint_list')




class AdminSettingsView(AdminRequiredMixin, View):
    def get(self, request):
        platform_settings = PlatformSettings.get_settings()
        return render(request, 'admin_panel/settings.html', {'settings': platform_settings})

    def post(self, request):
        platform_settings = PlatformSettings.get_settings()
        commission_rate  = request.POST.get('commission_rate')
        min_withdrawal   = request.POST.get('min_withdrawal')
        maintenance_mode = request.POST.get('maintenance_mode') == 'on'
        support_email    = request.POST.get('support_email', '').strip()
        terms_of_service = request.POST.get('terms_of_service', '').strip()

        try:
            platform_settings.commission_rate  = float(commission_rate)
            platform_settings.min_withdrawal   = float(min_withdrawal)
            platform_settings.maintenance_mode = maintenance_mode
            platform_settings.support_email    = support_email or None
            platform_settings.terms_of_service = terms_of_service or None
            platform_settings.updated_by       = request.user
            platform_settings.save()
            messages.success(request, 'Sozlamalar saqlandi.')
        except (ValueError, TypeError) as e:
            messages.error(request, f'Xato: {e}')

        return redirect('admin_panel:settings')