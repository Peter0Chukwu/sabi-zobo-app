import requests
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from .models import Product, Order, Wallet, WalletTransaction
from .forms import BankDetailsForm
from .banks import get_banks, resolve_account


@login_required
def product_page(request):
    product = get_object_or_404(Product, is_active=True)
    return render(request, 'store/product.html', {'product': product})


@login_required
def checkout_view(request):
    if request.method != 'POST':
        return redirect('product_page')

    product_id = request.POST.get('product_id')
    product = get_object_or_404(Product, id=product_id)

    order = Order.objects.create(
        buyer=request.user,
        product=product,
        price_paid=product.price,
        status='pending',
    )

    headers = {'Authorization': f'Bearer {settings.PAYSTACK_SECRET_KEY}'}
    data = {
        'email': request.user.email,
        'amount': int(product.price * 100),  # Paystack expects kobo, not naira
        'reference': f'zobo-order-{order.id}',
        'callback_url': request.build_absolute_uri('/payment/callback/'),
    }

    response = requests.post(
        'https://api.paystack.co/transaction/initialize',
        headers=headers,
        json=data,
    )
    res_data = response.json()

    if res_data.get('status'):
        order.paystack_reference = data['reference']
        order.save()
        return redirect(res_data['data']['authorization_url'])

    return render(request, 'store/product.html', {
        'product': product,
        'error': 'Could not start payment. Please try again.',
    })


@login_required
def payment_callback(request):
    reference = request.GET.get('reference')
    order = get_object_or_404(Order, paystack_reference=reference, buyer=request.user)

    headers = {'Authorization': f'Bearer {settings.PAYSTACK_SECRET_KEY}'}
    response = requests.get(
        f'https://api.paystack.co/transaction/verify/{reference}',
        headers=headers,
    )
    res_data = response.json()

    if res_data.get('status') and res_data['data']['status'] == 'success':
        # The amount Paystack received must match the order
        paid_kobo = res_data['data']['amount']
        if paid_kobo != int(order.price_paid * 100):
            return render(request, 'store/payment_failed.html', {'order': order})

        # Only move forward from pending, never back from delivered/refunded
        if order.status == 'pending':
            order.status = 'paid'
            order.save()
        return render(request, 'store/payment_success.html', {'order': order})

    return render(request, 'store/payment_failed.html', {'order': order})


@login_required
def dashboard(request):
    orders = Order.objects.filter(buyer=request.user).order_by('-created_at')
    wallet, _ = Wallet.objects.get_or_create(user=request.user)
    transactions = WalletTransaction.objects.filter(user=request.user).order_by('-created_at')
    referral_link = request.build_absolute_uri(f'/accounts/signup/?ref={request.user.referral_code}')
    referral_count = request.user.referrals.count()

    return render(request, 'store/dashboard.html', {
        'orders': orders,
        'wallet': wallet,
        'transactions': transactions,
        'referral_link': referral_link,
        'referral_count': referral_count,
    })


@login_required
def bank_details(request):
    banks = get_banks()
    user = request.user

    if request.method == 'POST':
        form = BankDetailsForm(request.POST, banks=banks)
        if form.is_valid():
            code = form.cleaned_data['bank_code']
            number = form.cleaned_data['account_number']
            bank_name = dict(form.fields['bank_code'].choices).get(code, '')

            if settings.VERIFY_BANK_ACCOUNTS:
                account_name, error = resolve_account(number, code)
            else:
                account_name, error = (user.get_full_name() or user.username), None

            if error:
                form.add_error('account_number', error)
            else:
                user.bank_code = code
                user.bank_name = bank_name
                user.account_number = number
                user.account_name = account_name
                user.save(update_fields=['bank_code', 'bank_name', 'account_number', 'account_name'])
                return redirect('dashboard')
    else:
        form = BankDetailsForm(
            banks=banks,
            initial={'bank_code': user.bank_code, 'account_number': user.account_number},
        )

    return render(request, 'store/bank_details.html', {
        'form': form,
        'banks_unavailable': not banks,
    })