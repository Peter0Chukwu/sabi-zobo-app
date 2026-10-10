from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from .models import Order, Wallet, WalletTransaction

@receiver(post_save, sender=Order)
def credit_cashback_on_delivery(sender, instance, **kwargs):
    if instance.status != 'delivered' or instance.cashback_processed:
        return

    product = instance.product
    buyer = instance.buyer

    # Credit the buyer's cashback
    if product.cashback_amount > 0:
        buyer_wallet, _ = Wallet.objects.get_or_create(user=buyer)
        buyer_wallet.pending_balance += product.cashback_amount
        buyer_wallet.save()

        WalletTransaction.objects.create(
            user=buyer,
            order=instance,
            type='cashback',
            amount=product.cashback_amount,
            status='pending',
        )

    # Credit the referrer's commission, if the buyer was referred
    if buyer.referred_by and product.referral_amount > 0:
        referrer_wallet, _ = Wallet.objects.get_or_create(user=buyer.referred_by)
        referrer_wallet.pending_balance += product.referral_amount
        referrer_wallet.save()

        WalletTransaction.objects.create(
            user=buyer.referred_by,
            order=instance,
            type='referral',
            amount=product.referral_amount,
            status='pending',
        )

    # Mark as processed WITHOUT triggering this signal again
    Order.objects.filter(pk=instance.pk).update(
        cashback_processed=True,
        delivered_at=timezone.now(),
    )

@receiver(post_save, sender=Order)
def reverse_earnings_on_refund(sender, instance, **kwargs):
    if instance.status != 'refunded':
        return

    pending = WalletTransaction.objects.filter(
        order=instance,
        status='pending',
        type__in=['cashback', 'referral'],
    )

    for tx in pending:
        with transaction.atomic():
            wallet = Wallet.objects.select_for_update().get(user=tx.user)
            wallet.pending_balance -= tx.amount
            wallet.save()
            tx.status = 'reversed'
            tx.save()