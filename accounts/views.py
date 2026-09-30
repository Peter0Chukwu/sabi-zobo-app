from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import AuthenticationForm
from .forms import SignUpForm
from .models import User


def signup_view(request):
    ref_code = request.GET.get('ref') or request.POST.get('ref_code')

    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            if ref_code:
                referrer = User.objects.filter(referral_code=ref_code).first()
                if referrer:
                    user.referred_by = referrer
            user.save()
            login(request, user)
            return redirect('product_page')
    else:
        form = SignUpForm()

    return render(request, 'accounts/signup.html', {'form': form, 'ref_code': ref_code})


def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('product_page')
    else:
        form = AuthenticationForm()

    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('login')