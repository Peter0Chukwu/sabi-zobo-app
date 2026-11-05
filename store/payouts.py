import requests
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from .models import Wallet, WalletTransaction, PayoutBatch

BASE = 'https://api.paystack.co'


def _headers():
    return {'Authorization': f'Bearer {settings.PAYSTACK_SECRET_KEY}'}


def payout_reference(batch):
    # Paystack references must be 16-50 characters, so the id is zero-padded
    return f'zobo-payout-{batch.id:06d}'


def restore_funds(batch, new_status):
    """Give a payout's money back to the user's available balance."""
    with transaction.atomic():
        b = PayoutBatch.objects.select_for_update().get(pk=batch.pk)
        if b.status not in ('pending', 'approved'):
            return
        wallet = Wallet.objects.select_for_update().get(user=b.user)
        wallet.available_balance += b.gross_amount
        wallet.save()
        WalletTransaction.objects.filter(payout=b, status='processing').update(
            status='available', payout=None
        )
        b.status = new_status
        b.save()


def mark_paid(batch):
    with transaction.atomic():
        b = PayoutBatch.objects.select_for_update().get(pk=batch.pk)
        if b.status == 'paid':
            return
        WalletTransaction.objects.filter(payout=b, status='processing').update(status='paid_out')
        b.status = 'paid'
        b.paid_at = timezone.now()
        b.save()


def send_payout(batch):
    # Claim the batch first, so a double-click can't send it twice
    with transaction.atomic():
        b = PayoutBatch.objects.select_for_update().get(pk=batch.pk)
        if b.status != 'pending':
            return 'Skipped: not in Pending status.'
        b.status = 'approved'
        b.save()

    user = batch.user
    reference = payout_reference(batch)

    try:
        r = requests.post(f'{BASE}/transferrecipient', headers=_headers(), timeout=30, json={
            'type': 'nuban',
            'name': user.account_name,
            'account_number': user.account_number,
            'bank_code': user.bank_code,
            'currency': 'NGN',
        })
        res = r.json()
        if not res.get('status'):
            PayoutBatch.objects.filter(pk=batch.pk).update(status='pending')
            return f"Paystack rejected the bank details: {res.get('message')}"
        recipient_code = res['data']['recipient_code']

        t = requests.post(f'{BASE}/transfer', headers=_headers(), timeout=30, json={
            'source': 'balance',
            'amount': int((batch.net_amount * 100).to_integral_value()),  # kobo
            'recipient': recipient_code,
            'reference': reference,
            'reason': 'Zobo cashback payout',
        })
        tres = t.json()
    except (requests.RequestException, ValueError):
        return ('Network problem, so the result is uncertain. Left as Approved. '
                'Use "Check status" before doing anything else.')

    if not tres.get('status'):
        PayoutBatch.objects.filter(pk=batch.pk).update(status='pending')
        return f"Paystack refused the transfer: {tres.get('message')}"

    data = tres['data']
    PayoutBatch.objects.filter(pk=batch.pk).update(paystack_transfer_code=data.get('transfer_code', ''))

    if data.get('status') == 'success':
        mark_paid(batch)
        return 'Sent and confirmed.'
    if data.get('status') == 'otp':
        return ('Paystack is waiting for an OTP, so nothing has been sent yet. '
                'Left as Approved. Turn off OTP in Paystack, or finalize it there.')
    return 'Transfer queued. Left as Approved. Use "Check status" in a few minutes.'


def check_status(batch):
    try:
        r = requests.get(f'{BASE}/transfer/verify/{payout_reference(batch)}',
                         headers=_headers(), timeout=30)
        res = r.json()
    except (requests.RequestException, ValueError):
        return 'Could not reach Paystack. Try again shortly.'

    if not res.get('status'):
        msg = res.get('message', '')
        if 'not found' in msg.lower():
            PayoutBatch.objects.filter(pk=batch.pk, status='approved').update(status='pending')
            return 'Paystack has no record of this transfer. Returned to Pending so you can retry.'
        return f'Could not check: {msg}'

    st = res['data']['status']
    if st == 'success':
        mark_paid(batch)
        return 'Confirmed paid.'
    if st in ('failed', 'reversed'):
        restore_funds(batch, 'failed')
        return "Transfer failed. Money returned to the user's available balance."
    return f'Still in progress (Paystack status: {st}).'