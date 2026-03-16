import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import MinValueValidator



class User(AbstractUser):
    ROLE_CLIENT    = 'client'
    ROLE_DEVELOPER = 'developer'
    ROLE_ADMIN     = 'admin'
    ROLE_CHOICES   = [
        (ROLE_CLIENT,    'Mijoz'),
        (ROLE_DEVELOPER, 'Dasturchi'),
        (ROLE_ADMIN,     'Admin'),
    ]

    email         = models.EmailField(unique=True, verbose_name='Email')
    role          = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_CLIENT)
    avatar        = models.ImageField(upload_to='avatars/', blank=True, null=True)
    phone         = models.CharField(max_length=20, blank=True, null=True)
    company       = models.CharField(max_length=200, blank=True, null=True)
    bio           = models.TextField(max_length=1000, blank=True, null=True)
    portfolio_url = models.URLField(blank=True, null=True)
    skills        = models.JSONField(default=list, blank=True, null=True)
    contact_public = models.BooleanField(default=True)
    is_verified   = models.BooleanField(default=False)
    is_blocked    = models.BooleanField(default=False)
    block_reason  = models.TextField(blank=True, null=True)
    created_at    = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)

    USERNAME_FIELD  = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    class Meta:
        verbose_name = 'Foydalanuvchi'
        verbose_name_plural = 'Foydalanuvchilar'

    def __str__(self):
        return f'{self.get_full_name()} <{self.email}>'

    # helper properties
    @property
    def is_client(self):    return self.role == self.ROLE_CLIENT
    @property
    def is_developer(self): return self.role == self.ROLE_DEVELOPER
    @property
    def is_admin_role(self): return self.role == self.ROLE_ADMIN or self.is_staff



class PlatformSettings(models.Model):
    commission_rate  = models.DecimalField(max_digits=5, decimal_places=2, default=10.00)
    min_withdrawal   = models.DecimalField(max_digits=12, decimal_places=2, default=50000.00)
    maintenance_mode = models.BooleanField(default=False)
    support_email    = models.EmailField(blank=True, null=True)
    terms_of_service = models.TextField(blank=True, null=True)
    updated_at       = models.DateTimeField(auto_now=True)
    updated_by       = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='settings_updates'
    )

    class Meta:
        verbose_name = 'Platform sozlamalari'
        verbose_name_plural = 'Platform sozlamalari'

    def __str__(self):
        return f'Sozlamalar (komissiya {self.commission_rate}%)'

    @classmethod
    def get_settings(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)



class Category(models.Model):
    name       = models.CharField(max_length=100, unique=True)
    slug       = models.SlugField(max_length=120, unique=True)
    icon       = models.CharField(max_length=50, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    is_active  = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Kategoriya'
        verbose_name_plural = 'Kategoriyalar'
        ordering = ['name']

    def __str__(self):
        return self.name


class Service(models.Model):
    developer    = models.ForeignKey(User, on_delete=models.CASCADE, related_name='services')
    category     = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='services')
    title        = models.CharField(max_length=200)
    description  = models.TextField(max_length=3000)
    price        = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(1000)])
    duration_days = models.PositiveIntegerField(default=7)
    is_active    = models.BooleanField(default=True)
    views_count  = models.PositiveIntegerField(default=0)
    orders_count = models.PositiveIntegerField(default=0)
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Xizmat'
        verbose_name_plural = 'Xizmatlar'
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    @property
    def avg_rating(self):
        from django.db.models import Avg
        result = self.orders.filter(status='completed').aggregate(avg=Avg('review__rating'))
        return round(result['avg'] or 0, 1)

    def increment_views(self):
        Service.objects.filter(pk=self.pk).update(views_count=models.F('views_count') + 1)

    def has_active_orders(self):
        return self.orders.filter(status__in=['pending', 'active', 'delivered', 'revision', 'dispute']).exists()



class Order(models.Model):
    STATUS_PENDING   = 'pending'
    STATUS_ACTIVE    = 'active'
    STATUS_DELIVERED = 'delivered'
    STATUS_COMPLETED = 'completed'
    STATUS_REVISION  = 'revision'
    STATUS_DISPUTE   = 'dispute'
    STATUS_CANCELLED = 'cancelled'
    STATUS_REFUNDED  = 'refunded'

    STATUS_CHOICES = [
        (STATUS_PENDING,   'Kutilmoqda'),
        (STATUS_ACTIVE,    'Faol'),
        (STATUS_DELIVERED, 'Topshirildi'),
        (STATUS_COMPLETED, 'Tugallandi'),
        (STATUS_REVISION,  'Tuzatish'),
        (STATUS_DISPUTE,   'Nizoli'),
        (STATUS_CANCELLED, 'Bekor qilindi'),
        (STATUS_REFUNDED,  'Qaytarildi'),
    ]

    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='client_orders')
    developer    = models.ForeignKey(User, on_delete=models.CASCADE, related_name='developer_orders')
    service      = models.ForeignKey(Service, on_delete=models.PROTECT, related_name='orders')
    status       = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    requirements = models.TextField(max_length=3000, blank=True, null=True)
    price        = models.DecimalField(max_digits=12, decimal_places=2)
    deadline     = models.DateField(blank=True, null=True)
    accepted_at  = models.DateTimeField(blank=True, null=True)
    delivered_at = models.DateTimeField(blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    cancelled_at = models.DateTimeField(blank=True, null=True)
    cancel_reason  = models.TextField(blank=True, null=True)
    revision_reason = models.TextField(blank=True, null=True)
    dispute_reason  = models.TextField(blank=True, null=True)
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Buyurtma'
        verbose_name_plural = 'Buyurtmalar'
        ordering = ['-created_at']

    def __str__(self):
        return f'Buyurtma #{str(self.id)[:8]} — {self.service.title}'

    # ── State machine metodlari ──
    def accept(self, days: int):
        from django.utils import timezone
        import datetime
        self.status = self.STATUS_ACTIVE
        self.accepted_at = timezone.now()
        self.deadline = timezone.now().date() + datetime.timedelta(days=days)
        self.save()

    def reject(self, reason: str):
        self.status = self.STATUS_CANCELLED
        self.cancel_reason = reason
        self.cancelled_at = __import__('django.utils.timezone', fromlist=['timezone']).timezone.now()
        self.save()

    def deliver(self):
        from django.utils import timezone
        self.status = self.STATUS_DELIVERED
        self.delivered_at = timezone.now()
        self.save()

    def complete(self):
        from django.utils import timezone
        self.status = self.STATUS_COMPLETED
        self.completed_at = timezone.now()
        self.save()

    def request_revision(self, reason: str):
        self.status = self.STATUS_REVISION
        self.revision_reason = reason
        self.save()

    def open_dispute(self, reason: str):
        self.status = self.STATUS_DISPUTE
        self.dispute_reason = reason
        self.save()

    def cancel(self, reason: str):
        from django.utils import timezone
        self.status = self.STATUS_CANCELLED
        self.cancel_reason = reason
        self.cancelled_at = timezone.now()
        self.save()



class Delivery(models.Model):
    order         = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='deliveries')
    developer     = models.ForeignKey(User, on_delete=models.CASCADE, related_name='deliveries')
    delivery_file = models.FileField(upload_to='deliveries/', blank=True, null=True)
    delivery_url  = models.URLField(blank=True, null=True)
    message       = models.TextField(max_length=2000, blank=True, null=True)
    version       = models.PositiveIntegerField(default=1)
    created_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Topshiriq'
        verbose_name_plural = 'Topshiriqlar'
        ordering = ['-created_at']

    def __str__(self):
        return f'Topshiriq v{self.version} — {self.order}'

    def clean(self):
        from django.core.exceptions import ValidationError
        if not self.delivery_file and not self.delivery_url:
            raise ValidationError('Fayl yoki URL dan biri majburiy.')



class Payment(models.Model):
    STATUS_HOLD     = 'hold'
    STATUS_RELEASED = 'released'
    STATUS_REFUNDED = 'refunded'
    STATUS_DISPUTED = 'disputed'
    STATUS_CHOICES  = [
        (STATUS_HOLD,     'Ushlab turilgan'),
        (STATUS_RELEASED, 'O\'tkazildi'),
        (STATUS_REFUNDED, 'Qaytarildi'),
        (STATUS_DISPUTED, 'Nizoli'),
    ]

    PAYMENT_METHOD_CHOICES = [
        ('payme',  'Payme'),
        ('click',  'Click'),
        ('uzcard', 'UzCard'),
        ('mock',   'Test (Mock)'),
    ]

    id                = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order             = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='payment')
    client            = models.ForeignKey(User, on_delete=models.CASCADE, related_name='client_payments')
    developer         = models.ForeignKey(User, on_delete=models.CASCADE, related_name='developer_payments')
    amount            = models.DecimalField(max_digits=12, decimal_places=2)
    commission_rate   = models.DecimalField(max_digits=5, decimal_places=2)
    commission_amount = models.DecimalField(max_digits=12, decimal_places=2)
    developer_amount  = models.DecimalField(max_digits=12, decimal_places=2)
    status            = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_HOLD)
    payment_method    = models.CharField(max_length=50, choices=PAYMENT_METHOD_CHOICES, default='mock')
    external_id       = models.CharField(max_length=200, blank=True, null=True)
    paid_at           = models.DateTimeField(blank=True, null=True)
    released_at       = models.DateTimeField(blank=True, null=True)
    refunded_at       = models.DateTimeField(blank=True, null=True)
    admin_note        = models.TextField(blank=True, null=True)
    handled_by        = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='handled_payments'
    )
    created_at        = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'To\'lov'
        verbose_name_plural = 'To\'lovlar'
        ordering = ['-created_at']

    def __str__(self):
        return f'To\'lov {self.amount} — {self.get_status_display()}'

    @classmethod
    def create_for_order(cls, order):
        settings = PlatformSettings.get_settings()
        commission_rate   = settings.commission_rate
        commission_amount = (order.price * commission_rate / 100).quantize(__import__('decimal').Decimal('0.01'))
        developer_amount  = order.price - commission_amount
        return cls.objects.create(
            order=order,
            client=order.client,
            developer=order.developer,
            amount=order.price,
            commission_rate=commission_rate,
            commission_amount=commission_amount,
            developer_amount=developer_amount,
            status=cls.STATUS_HOLD,
        )

    def release_to_developer(self, admin=None):
        from django.utils import timezone
        self.status = self.STATUS_RELEASED
        self.released_at = timezone.now()
        if admin:
            self.handled_by = admin
        self.save()

    def refund_to_client(self, admin=None, note=''):
        from django.utils import timezone
        self.status = self.STATUS_REFUNDED
        self.refunded_at = timezone.now()
        if admin:
            self.handled_by = admin
        if note:
            self.admin_note = note
        self.save()



class Review(models.Model):
    order      = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='review')
    client     = models.ForeignKey(User, on_delete=models.CASCADE, related_name='given_reviews')
    developer  = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_reviews')
    rating     = models.PositiveSmallIntegerField()
    comment    = models.TextField(max_length=1500, blank=True, null=True)
    is_edited  = models.BooleanField(default=False)
    edited_at  = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Sharh'
        verbose_name_plural = 'Sharhlar'
        ordering = ['-created_at']
        unique_together = [['order', 'client']]

    def __str__(self):
        return f'{self.rating}⭐ — {self.client} → {self.developer}'

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.order.status != Order.STATUS_COMPLETED:
            raise ValidationError('Faqat tugallangan buyurtmaga sharh qoldirish mumkin.')
        if not (1 <= self.rating <= 5):
            raise ValidationError('Reyting 1 dan 5 gacha bo\'lishi kerak.')



class ChatRoom(models.Model):
    order      = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='chatroom')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Chat xonasi'
        verbose_name_plural = 'Chat xonalari'

    def __str__(self):
        return f'Chat — {self.order}'


class Message(models.Model):
    room       = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='messages')
    sender     = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    text       = models.TextField(max_length=3000, blank=True, null=True)
    file       = models.FileField(upload_to='chat_files/', blank=True, null=True)
    is_read    = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Xabar'
        verbose_name_plural = 'Xabarlar'
        ordering = ['created_at']

    def __str__(self):
        return f'{self.sender} → {self.room} | {self.created_at:%H:%M}'



class Notification(models.Model):
    TYPE_CHOICES = [
        ('order_new',       'Yangi buyurtma'),
        ('order_accepted',  'Buyurtma qabul qilindi'),
        ('order_rejected',  'Buyurtma rad etildi'),
        ('order_delivered', 'Ish topshirildi'),
        ('order_completed', 'Buyurtma tugallandi'),
        ('order_revision',  'Tuzatish so\'raldi'),
        ('order_dispute',   'Nizo ochildi'),
        ('order_cancelled', 'Buyurtma bekor qilindi'),
        ('payment_hold',    'To\'lov ushlab qolindi'),
        ('payment_released','To\'lov o\'tkazildi'),
        ('payment_refunded','To\'lov qaytarildi'),
        ('review_new',      'Yangi sharh'),
        ('complaint_new',   'Yangi shikoyat'),
        ('account_blocked', 'Akkaunt bloklandi'),
        ('account_verified','Akkaunt tasdiqlandi'),
    ]

    recipient  = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    type       = models.CharField(max_length=50, choices=TYPE_CHOICES)
    title      = models.CharField(max_length=200)
    message    = models.TextField(max_length=500)
    order      = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True, related_name='notifications')
    is_read    = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Bildirishnoma'
        verbose_name_plural = 'Bildirishnomalar'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.recipient} — {self.title}'

    @classmethod
    def send(cls, recipient, type, title, message, order=None):
        return cls.objects.create(
            recipient=recipient,
            type=type,
            title=title,
            message=message,
            order=order,
        )



class Complaint(models.Model):
    REASON_CHOICES = [
        ('scam',         'Firibgarlik'),
        ('spam',         'Spam'),
        ('poor_quality', 'Past sifat'),
        ('abuse',        'Haqorat'),
        ('rules',        'Qoidabuzarlik'),
        ('other',        'Boshqa'),
    ]
    STATUS_CHOICES = [
        ('pending',    'Kutilmoqda'),
        ('reviewing',  'Ko\'rib chiqilmoqda'),
        ('resolved',   'Hal qilindi'),
        ('dismissed',  'Rad etildi'),
    ]
    DECISION_CHOICES = [
        ('blocked',   'Bloklandi'),
        ('warned',    'Ogohlantirish'),
        ('refunded',  'Qaytarildi'),
        ('dismissed', 'Rad etildi'),
    ]

    reporter      = models.ForeignKey(User, on_delete=models.CASCADE, related_name='filed_complaints')
    reported_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_complaints')
    order         = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True, related_name='complaints')
    reason        = models.CharField(max_length=50, choices=REASON_CHOICES)
    description   = models.TextField(max_length=3000)
    status        = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    admin         = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_complaints'
    )
    decision      = models.CharField(max_length=20, choices=DECISION_CHOICES, blank=True, null=True)
    admin_note    = models.TextField(blank=True, null=True)
    resolved_at   = models.DateTimeField(blank=True, null=True)
    created_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Shikoyat'
        verbose_name_plural = 'Shikoyatlar'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.reporter} → {self.reported_user} ({self.get_reason_display()})'

    def resolve(self, admin, decision: str, note: str = ''):
        from django.utils import timezone
        self.status = 'resolved'
        self.admin = admin
        self.decision = decision
        self.admin_note = note
        self.resolved_at = timezone.now()
        self.save()

    def dismiss(self, admin, note: str = ''):
        from django.utils import timezone
        self.status = 'dismissed'
        self.admin = admin
        self.decision = 'dismissed'
        self.admin_note = note
        self.resolved_at = timezone.now()
        self.save()



class PortfolioItem(models.Model):
    developer    = models.ForeignKey(User, on_delete=models.CASCADE, related_name='portfolio_items')
    title        = models.CharField(max_length=200)
    description  = models.TextField(max_length=2000, blank=True, null=True)
    image        = models.ImageField(upload_to='portfolio/', blank=True, null=True)
    project_url  = models.URLField(blank=True, null=True)
    github_url   = models.URLField(blank=True, null=True)
    technologies = models.JSONField(default=list, blank=True, null=True)
    order        = models.PositiveIntegerField(default=0)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Portfolio'
        verbose_name_plural = 'Portfolio elementlari'
        ordering = ['order', '-created_at']

    def __str__(self):
        return f'{self.developer.get_full_name()} — {self.title}'