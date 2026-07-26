from django.contrib import admin
from .models import BreadMachine, Loaf

@admin.register(BreadMachine)
class BreadMachineAdmin(admin.ModelAdmin):
    list_display = ('name',)

@admin.register(Loaf)
class LoafAdmin(admin.ModelAdmin):
    list_display = ('bread_type', 'machine', 'started_at', 'ready_at', 'is_active')
    list_filter = ('machine',)
