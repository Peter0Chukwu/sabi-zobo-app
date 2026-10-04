import requests
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from .models import Product, Order


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
        order.status = 'paid'
        order.save()
        return render(request, 'store/payment_success.html', {'order': order})

    return render(request, 'store/payment_failed.html', {'order': order})

@login_required
def dashboard(request):
    orders = Order.objects.filter(buyer=request.user).order_by('-created_at')
    referral_link = request.build_absolute_uri(f'/accounts/signup/?ref={request.user.referral_code}')
    referral_count = request.user.referrals.count()

    return render(request, 'store/dashboard.html', {
        'orders': orders,
        'referral_link': referral_link,
        'referral_count': referral_count,
    })