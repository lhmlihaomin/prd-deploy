from django.contrib import admin

from .models import AWSProfile, AWSRegion

class AWSProfileAdmin(admin.ModelAdmin):
    list_display = ('name', 'account_id')

admin.site.register(AWSProfile, AWSProfileAdmin)
admin.site.register(AWSRegion)
