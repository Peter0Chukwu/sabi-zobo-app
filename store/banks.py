import requests
from django.conf import settings
from django.core.cache import cache

BASE = 'https://api.paystack.co'
CACHE_KEY = 'paystack_banks_ng'


def _headers():
    return {'Authorization': f'Bearer {settings.PAYSTACK_SECRET_KEY}'}


def get_banks():
    """Nigerian banks from Paystack as [{'name', 'code'}], cached for a day."""
    banks = cache.get(CACHE_KEY)
    if banks is None:
        try:
            r = requests.get(
                f'{BASE}/bank',
                headers=_headers(),
                params={'country': 'nigeria', 'currency': 'NGN', 'perPage': 200},
                timeout=20,
            )
            data = r.json()
        except (requests.RequestException, ValueError):
            return []
        if not data.get('status'):
            return []
        banks = sorted(
            ({'name': b['name'], 'code': b['code']} for b in data['data'] if b.get('active', True)),
            key=lambda b: b['name'],
        )
        cache.set(CACHE_KEY, banks, 60 * 60 * 24)
    return banks


def resolve_account(account_number, bank_code):
    """Ask Paystack who owns this account. Returns (account_name, error_message)."""
    try:
        r = requests.get(
            f'{BASE}/bank/resolve',
            headers=_headers(),
            params={'account_number': account_number, 'bank_code': bank_code},
            timeout=20,
        )
        data = r.json()
    except (requests.RequestException, ValueError):
        return None, 'Could not reach Paystack to verify the account. Please try again.'

    if data.get('status'):
        return data['data']['account_name'], None
    return None, data.get('message') or 'Could not verify this account.'