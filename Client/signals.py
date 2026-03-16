from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Order, Payment, ChatRoom, Notification, Review, Service


@receiver(post_save, sender=Order)
def order_post_save(sender, instance, created, **kwargs):

    order = instance


    if created:
        ChatRoom.objects.get_or_create(order=order)
        Notification.send(
            recipient=order.developer,
            type='order_new',
            title='Yangi buyurtma!',
            message=f'{order.client.get_full_name()} sizga "{order.service.title}" xizmati bo\'yicha buyurtma berdi.',
            order=order,
        )
        return


    status = order.status

    if status == Order.STATUS_ACTIVE:
        Notification.send(
            recipient=order.client,
            type='order_accepted',
            title='Buyurtmangiz qabul qilindi',
            message=f'{order.developer.get_full_name()} buyurtmangizni qabul qildi. Muddat: {order.deadline}.',
            order=order,
        )
        # orders_count +1
        Service.objects.filter(pk=order.service_id).update(
            orders_count=__import__('django.db.models', fromlist=['F']).F('orders_count') + 1
        )

    elif status == Order.STATUS_DELIVERED:
        Notification.send(
            recipient=order.client,
            type='order_delivered',
            title='Ish topshirildi!',
            message=f'{order.developer.get_full_name()} ishni topshirdi. Tekshirib, qabul qiling yoki tuzatish so\'rang.',
            order=order,
        )

    elif status == Order.STATUS_COMPLETED:

        try:
            order.payment.release_to_developer()
        except Payment.DoesNotExist:
            pass
        Notification.send(
            recipient=order.developer,
            type='payment_released',
            title='To\'lov o\'tkazildi!',
            message=f'Buyurtma tugallandi. {order.payment.developer_amount} so\'m hisobingizga o\'tkazildi.',
            order=order,
        )
        Notification.send(
            recipient=order.client,
            type='order_completed',
            title='Buyurtma tugallandi',
            message=f'Buyurtma muvaffaqiyatli yakunlandi. Sharh qoldiring!',
            order=order,
        )

    elif status == Order.STATUS_CANCELLED:

        try:
            if order.payment.status == Payment.STATUS_HOLD:
                order.payment.refund_to_client()
        except Payment.DoesNotExist:
            pass
        Notification.send(
            recipient=order.client,
            type='order_cancelled',
            title='Buyurtma bekor qilindi',
            message=f'Buyurtmangiz bekor qilindi. To\'lov qaytarildi.',
            order=order,
        )

    elif status == Order.STATUS_REVISION:
        Notification.send(
            recipient=order.developer,
            type='order_revision',
            title='Tuzatish so\'raldi',
            message=f'{order.client.get_full_name()} tuzatish so\'radi: {order.revision_reason or ""}',
            order=order,
        )

    elif status == Order.STATUS_DISPUTE:
        Notification.send(
            recipient=order.developer,
            type='order_dispute',
            title='Nizo ochildi',
            message=f'{order.client.get_full_name()} nizo ochdi. Admin ko\'rib chiqadi.',
            order=order,
        )

        from django.contrib.auth import get_user_model
        User = get_user_model()
        admins = User.objects.filter(is_staff=True)
        for admin_user in admins:
            Notification.send(
                recipient=admin_user,
                type='order_dispute',
                title='Yangi nizo!',
                message=f'Buyurtma #{str(order.id)[:8]} bo\'yicha nizo ochildi.',
                order=order,
            )


@receiver(post_save, sender=Review)
def review_post_save(sender, instance, created, **kwargs):

    if created:
        Notification.send(
            recipient=instance.developer,
            type='review_new',
            title='Yangi sharh!',
            message=f'{instance.client.get_full_name()} {instance.rating}⭐ baho qoldirdi.',
            order=instance.order,
        )