from decimal import Decimal
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from store.models import Wallet, WalletTransaction, PayoutBatch


class Command(BaseCommand):
    help = "Create pending payout batches for users whose available balance has reached the minimum."

    def add_arguments(self, parser):
        parser.add_argument('--minimum', type=Decimal, default=None,
                            help='Override the minimum payout amount (for testing)')
        parser.add_argument('--dry-run', action='store_true',
                            help='Show what would be created without saving anything')

    def handle(self, *args, **options):
        minimum = options['minimum'] if options['minimum'] is not None else Decimal(str(settings.MINIMUM_PAYOUT_AMOUNT))
        commission_pct = Decimal(str(settings.PAYOUT_COMMISSION_PERCENT))
        dry_run = options['dry_run']

        created = 0
        skipped_no_bank = 0

        wallets = Wallet.objects.filter(available_balance__gte=minimum).select_related('user')

        for w in wallets:
            user = w.user

            if not (user.bank_code and user.account_number and user.account_name):
                skipped_no_bank += 1
                self.stdout.write(f'Skipped {user.username}: bank details incomplete.')
                continue

            if PayoutBatch.objects.filter(user=user, status__in=['pending', 'approved']).exists():
                self.stdout.write(f'Skipped {user.username}: a payout is already waiting.')
                continue

            with transaction.atomic():
                wallet = Wallet.objects.select_for_update().get(pk=w.pk)
                if wallet.available_balance < minimum:
                    continue

                gross = wallet.available_balance
                commission = (gross * commission_pct / 100).quantize(Decimal('0.01'))
                net = gross - commission

                if dry_run:
                    self.stdout.write(
                        f'[DRY RUN] {user.username}: gross {gross}, commission {commission}, net {net}'
                    )
                    created += 1
                    continue

                batch = PayoutBatch.objects.create(
                    user=user,
                    gross_amount=gross,
                    commission_deducted=commission,
                    net_amount=net,
                    status='pending',
                )
                WalletTransaction.objects.filter(
                    user=user,
                    status='available',
                    type__in=['cashback', 'referral'],
                ).update(status='processing', payout=batch)

                wallet.available_balance -= gross
                wallet.save()
                created += 1

        label = 'Would create' if dry_run else 'Created'
        self.stdout.write(self.style.SUCCESS(
            f'{label} {created} payout batch(es). Skipped {skipped_no_bank} for missing bank details.'
        ))