from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'referral_code', 'referred_by', 'is_staff')
    fieldsets = UserAdmin.fieldsets + (
        ('Referral Info', {'fields': ('referral_code', 'referred_by', 'phone_number')}),
    )
    readonly_fields = ('referral_code',)


admin.site.register(User, CustomUserAdmin)