from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import (
    User, PlatformSettings, Category, Service,
    Order, Delivery, Payment, Review, ChatRoom, Message,
    Complaint, Notification, PortfolioItem,
)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display  = ['email', 'get_full_name', 'role', 'is_verified', 'is_blocked', 'created_at']
    list_filter   = ['role', 'is_verified', 'is_blocked', 'is_active']
    search_fields = ['email', 'username', 'first_name', 'last_name']
    ordering      = ['-created_at']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = BaseUserAdmin.fieldsets + (
        ('Qo\'shimcha', {
            'fields': ('role', 'avatar', 'phone', 'company', 'bio',
                       'portfolio_url', 'skills', 'contact_public',
                       'is_verified', 'is_blocked', 'block_reason')
        }),
    )
    actions = ['block_users', 'unblock_users', 'verify_users']

    def block_users(self, request, queryset):
        queryset.update(is_blocked=True)
    block_users.short_description = 'Bloklash'

    def unblock_users(self, request, queryset):
        queryset.update(is_blocked=False, block_reason='')
    unblock_users.short_description = 'Blokdan chiqarish'

    def verify_users(self, request, queryset):
        queryset.update(is_verified=True, is_active=True)
    verify_users.short_description = 'Tasdiqlash'


@admin.register(PlatformSettings)
class PlatformSettingsAdmin(admin.ModelAdmin):
    list_display = ['commission_rate', 'min_withdrawal', 'maintenance_mode', 'updated_at']
    readonly_fields = ['updated_at']

    def has_add_permission(self, request):
        return not PlatformSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display  = ['name', 'slug', 'is_active', 'created_at']
    prepopulated_fields = {'slug': ('name',)}
    list_filter   = ['is_active']
    search_fields = ['name']


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display  = ['title', 'developer', 'category', 'price', 'is_active', 'orders_count']
    list_filter   = ['is_active', 'category']
    search_fields = ['title', 'developer__email']
    readonly_fields = ['views_count', 'orders_count', 'created_at', 'updated_at']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display  = ['id', 'client', 'developer', 'service', 'status', 'price', 'created_at']
    list_filter   = ['status']
    search_fields = ['client__email', 'developer__email', 'service__title']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display  = ['id', 'order', 'amount', 'commission_amount', 'developer_amount', 'status']
    list_filter   = ['status', 'payment_method']
    readonly_fields = ['id', 'created_at']
    actions = ['release_payments', 'refund_payments']

    def release_payments(self, request, queryset):
        for p in queryset.filter(status=Payment.STATUS_HOLD):
            p.release_to_developer(admin=request.user)
    release_payments.short_description = 'Dasturchiga o\'tkazish'

    def refund_payments(self, request, queryset):
        for p in queryset.filter(status=Payment.STATUS_HOLD):
            p.refund_to_client(admin=request.user)
    refund_payments.short_description = 'Clientga qaytarish'


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display  = ['client', 'developer', 'rating', 'is_edited', 'created_at']
    list_filter   = ['rating', 'is_edited']
    search_fields = ['client__email', 'developer__email']


@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):
    list_display  = ['reporter', 'reported_user', 'reason', 'status', 'created_at']
    list_filter   = ['status', 'reason']
    search_fields = ['reporter__email', 'reported_user__email']


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display  = ['recipient', 'type', 'title', 'is_read', 'created_at']
    list_filter   = ['type', 'is_read']
    search_fields = ['recipient__email', 'title']


admin.site.register(Delivery)
admin.site.register(ChatRoom)
admin.site.register(Message)
admin.site.register(PortfolioItem)