from django.db.models.signals import post_save
from django.dispatch import receiver
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
    Order.objects.filter(pk=instance.pk).update(cashback_processed=True)