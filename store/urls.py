from django.urls import path
from . import views

urlpatterns = [
    path('', views.product_page, name='product_page'),
    path('checkout/', views.checkout_view, name='checkout'),
    path('payment/callback/', views.payment_callback, name='payment_callback'),
    path('dashboard/', views.dashboard, name='dashboard'),
]