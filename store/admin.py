from django.contrib import admin
from .models import Product, Order, Wallet, WalletTransaction, PayoutBatch
from .payouts import send_payout, check_status, restore_funds


@admin.action(description='Approve and send selected payouts via Paystack')
def approve_and_send(modeladmin, request, queryset):
    for batch in queryset:
        msg = send_payout(batch)
        modeladmin.message_user(request, f'Payout #{batch.id} ({batch.user}): {msg}')


@admin.action(description='Check Paystack status of selected payouts')
def refresh_status(modeladmin, request, queryset):
    for batch in queryset.filter(status='approved'):
        msg = check_status(batch)
        modeladmin.message_user(request, f'Payout #{batch.id} ({batch.user}): {msg}')


@admin.action(description='Reject selected payouts (return money to user)')
def reject_payouts(modeladmin, request, queryset):
    count = 0
    for batch in queryset.filter(status='pending'):
        restore_funds(batch, 'rejected')
        count += 1
    modeladmin.message_user(request, f'Rejected {count} payout(s). Only Pending payouts can be rejected.')


class PayoutBatchAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'gross_amount', 'commission_deducted', 'net_amount', 'status', 'created_at', 'paid_at')
    list_filter = ('status',)
    readonly_fields = ('user', 'gross_amount', 'commission_deducted', 'net_amount',
                       'status', 'paystack_transfer_code', 'created_at', 'paid_at')
    actions = [approve_and_send, refresh_status, reject_payouts]


admin.site.register(Product)
admin.site.register(Order)
admin.site.register(Wallet)
admin.site.register(WalletTransaction)
admin.site.register(PayoutBatch, PayoutBatchAdmin)