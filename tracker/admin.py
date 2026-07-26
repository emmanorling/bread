from django.contrib import admin
from .models import BreadMachine, Loaf

@admin.register(BreadMachine)
class BreadMachineAdmin(admin.ModelAdmin):
    list_display = ('name',)

@admin.register(Loaf)
class LoafAdmin(admin.ModelAdmin):
    list_display = ('bread_type', 'machine', 'started_at', 'ready_at', 'is_active')
    list_filter = ('machine',)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # Check if Django is loading the dropdown for the 'machine' field
        if db_field.name == "machine":
            machines = BreadMachine.objects.all()
            # If there is exactly 1 machine, set it as the default initial value
            if machines.count() == 1:
                kwargs['initial'] = machines.first().id
                
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
