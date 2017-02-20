from django.contrib import admin

from .models import Module, UpdateStep, UpdatePlan

admin.site.register(Module)
admin.site.register(UpdateStep)
admin.site.register(UpdatePlan)
