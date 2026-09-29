from django.contrib import admin
from .models import Product, Order, Wallet, WalletTransaction, PayoutBatch

admin.site.register(Product)
admin.site.register(Order)
admin.site.register(Wallet)
admin.site.register(WalletTransaction)
admin.site.register(PayoutBatch)