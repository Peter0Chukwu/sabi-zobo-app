from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator


class Product(models.Model):
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    cost_price = models.DecimalField(max_digits=10, decimal_places=2)
    cashback_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="% of profit shared with the buyer as cashback"
    )
    referral_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="% of profit shared with the referrer, if one exists"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def profit(self):
        return self.price - self.cost_price

    @property
    def cashback_amount(self):
        return round(self.profit * (self.cashback_percent / 100), 2)

    @property
    def referral_amount(self):
        return round(self.profit * (self.referral_percent / 100), 2)

    @property
    def seller_take_home(self):
        return self.profit - self.cashback_amount - self.referral_amount

    def clean(self):
        if self.cashback_percent + self.referral_percent > 100:
            raise ValidationError(
                "Cashback % and Referral % combined cannot exceed 100% of profit — "
                "you'd be giving away more than you earned."
            )

    def __str__(self):
        return self.name


class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('delivered', 'Delivered'),
        ('refunded', 'Refunded'),
    ]
    buyer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='orders')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    price_paid = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    paystack_reference = models.CharField(max_length=100, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order #{self.id} - {self.buyer} - {self.status}"


class Wallet(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='wallet')
    pending_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    available_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.user}'s wallet"


class WalletTransaction(models.Model):
    TYPE_CHOICES = [
        ('cashback', 'Cashback'),
        ('referral', 'Referral Commission'),
        ('withdrawal', 'Withdrawal'),
        ('reversal', 'Reversal'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('available', 'Available'),
        ('paid_out', 'Paid Out'),
        ('reversed', 'Reversed'),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='wallet_transactions')
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.type} - {self.amount} - {self.user}"


class PayoutBatch(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='payouts')
    gross_amount = models.DecimalField(max_digits=10, decimal_places=2)
    commission_deducted = models.DecimalField(max_digits=10, decimal_places=2)
    net_amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, default='pending')
    paystack_transfer_code = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Payout to {self.user} - {self.net_amount}"