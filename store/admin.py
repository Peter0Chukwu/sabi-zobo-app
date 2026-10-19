from django.contrib import admin
from .models import Product, Order, Wallet, WalletTransaction, PayoutBatch


class PayoutBatchAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'gross_amount', 'commission_deducted', 'net_amount', 'status', 'created_at')
    list_filter = ('status',)


admin.site.register(Product)
admin.site.register(Order)
admin.site.register(Wallet)
admin.site.register(WalletTransaction)
admin.site.register(PayoutBatch, PayoutBatchAdmin)