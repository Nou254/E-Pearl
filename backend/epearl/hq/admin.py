from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import PlatformSetting, SMSCredit, APIKey

@admin.register(PlatformSetting)
class PlatformSettingAdmin(admin.ModelAdmin):
    list_display = ['setting_key', 'setting_value', 'setting_type', 'is_active']

@admin.register(SMSCredit)
class SMSCreditAdmin(admin.ModelAdmin):
    list_display = ['venue', 'credits_remaining', 'last_top_up']

@admin.register(APIKey)
class APIKeyAdmin(admin.ModelAdmin):
    list_display = ['name', 'venue', 'is_active', 'last_used']