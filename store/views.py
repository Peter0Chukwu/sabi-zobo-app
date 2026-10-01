from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Product


@login_required
def product_page(request):
    product = get_object_or_404(Product, is_active=True)
    return render(request, 'store/product.html', {'product': product})