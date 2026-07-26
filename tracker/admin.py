from datetime import timedelta
from django import forms
from django.contrib import admin, messages  # <-- Included 'admin' and 'messages'
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils import timezone
from django.utils.safestring import mark_safe

from .models import BreadMachine, Loaf

# Default suggested bread recipes/types
DEFAULT_BREAD_TYPES = [
    "White Loaf",
    "White Seeded",
    "White Fruit",
    "Whole Wheat",
    "Whole Wheat Seeded",
    "Whole Wheat Fruit",
    "Sourdough",
    "Brioche",
    "French Bread",
    "Rye",
]

# 1. Custom TextInput widget with safe <datalist> rendering
class DatalistTextInput(forms.TextInput):
    def __init__(self, data_list=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._data_list = data_list or []

    def render(self, name, value, attrs=None, renderer=None):
        attrs = attrs or {}
        attrs['list'] = f'list__{name}'
        
        html = super().render(name, value, attrs, renderer)
        options = ''.join([f'<option value="{item}">' for item in self._data_list])
        datalist_html = f'<datalist id="list__{name}">{options}</datalist>'
        
        return mark_safe(html + datalist_html)


# 2. Custom Form with Datalist & Ready-in Duration
class LoafAdminForm(forms.ModelForm):
    bread_type = forms.CharField(
        label="Bread Type",
        widget=DatalistTextInput(
            data_list=DEFAULT_BREAD_TYPES,
            attrs={'placeholder': 'Select or type a bread name...'}
        ),
        required=True
    )

    ready_in = forms.CharField(
        label="Ready in (HH:MM)",
        help_text="Enter hours and minutes, e.g. 03:30",
        widget=forms.TextInput(attrs={'placeholder': '03:30', 'style': 'width: 120px;'}),
        required=True
    )

    class Meta:
        model = Loaf
        fields = ['machine', 'bread_type', 'ready_in']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # If editing an existing loaf, pre-populate 'ready_in' with remaining hours & minutes
        if self.instance and self.instance.pk and self.instance.ready_at:
            now = timezone.now()
            if self.instance.ready_at > now:
                diff = self.instance.ready_at - now
                total_minutes = int(diff.total_seconds() // 60)
                hours = total_minutes // 60
                minutes = total_minutes % 60
                self.fields['ready_in'].initial = f"{hours:02d}:{minutes:02d}"
            else:
                self.fields['ready_in'].initial = "00:00"

    def clean_ready_in(self):
        data = self.cleaned_data['ready_in'].strip()
        try:
            parts = data.split(':')
            if len(parts) != 2:
                raise ValueError
            hours, minutes = int(parts[0]), int(parts[1])
            if minutes < 0 or minutes >= 60 or hours < 0:
                raise ValueError
            return timedelta(hours=hours, minutes=minutes)
        except ValueError:
            raise forms.ValidationError("Please enter time in HH:MM format (e.g. 03:30).")


# 3. Admin Registrations
@admin.register(Loaf)
class LoafAdmin(admin.ModelAdmin):
    form = LoafAdminForm
    list_display = ('bread_type', 'machine', 'ready_at', 'is_active')
    list_filter = ('machine',)

    def add_view(self, request, form_url='', extra_context=None):
        active_machine_ids = Loaf.objects.filter(
            ready_at__gt=timezone.now()
        ).values_list('machine_id', flat=True)

        available_machines = BreadMachine.objects.exclude(id__in=active_machine_ids)

        if not available_machines.exists():
            self.message_user(
                request, 
                "You cannot add a loaf - there is no free machine right now!", 
                level=messages.ERROR
            )
            return HttpResponseRedirect(reverse('admin:tracker_loaf_changelist'))

        return super().add_view(request, form_url=form_url, extra_context=extra_context)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "machine":
            object_id = request.resolver_match.kwargs.get('object_id')
            
            active_loaves = Loaf.objects.filter(ready_at__gt=timezone.now())
            if object_id:
                active_loaves = active_loaves.exclude(pk=object_id)
                
            busy_machine_ids = active_loaves.values_list('machine_id', flat=True)

            available_machines = BreadMachine.objects.exclude(id__in=busy_machine_ids)
            kwargs['queryset'] = available_machines

            if not object_id:
                last_machine_id = request.session.get('last_used_machine_id')
                if last_machine_id and available_machines.filter(id=last_machine_id).exists():
                    kwargs['initial'] = last_machine_id
                else:
                    first_available = available_machines.first()
                    if first_available:
                        kwargs['initial'] = first_available.id

        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        duration = form.cleaned_data.get('ready_in')
        if duration:
            # Re-calculate completion target based on time of save + entered duration
            obj.ready_at = timezone.now() + duration
            
        request.session['last_used_machine_id'] = obj.machine.id
        super().save_model(request, obj, form, change)
