from datetime import timedelta
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from store.models import Wallet, WalletTransaction


class Command(BaseCommand):
    help = "Move cashback/referral earnings from pending to available after the hold period."

    def add_arguments(self, parser):
        parser.add_argument(
            '--days', type=int, default=None,
            help='Override the hold period in days (use 0 for testing)',
        )

    def handle(self, *args, **options):
        days = options['days'] if options['days'] is not None else settings.HOLD_PERIOD_DAYS
        cutoff = timezone.now() - timedelta(days=days)

        due = list(
            WalletTransaction.objects.filter(
                status='pending',
                type__in=['cashback', 'referral'],
                created_at__lte=cutoff,
            ).exclude(order__status='refunded')
        )

        released = 0
        for tx in due:
            with transaction.atomic():
                wallet = Wallet.objects.select_for_update().get(user=tx.user)
                wallet.pending_balance -= tx.amount
                wallet.available_balance += tx.amount
                wallet.save()
                tx.status = 'available'
                tx.save()
            released += 1

        self.stdout.write(self.style.SUCCESS(f'Released {released} transaction(s).'))