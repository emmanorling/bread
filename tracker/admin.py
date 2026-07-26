from datetime import timedelta
from django import forms
from django.contrib import admin
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


# 3. REGISTER THE ADMIN CLASSES (THIS WAS MISSING)
@admin.register(BreadMachine)
class BreadMachineAdmin(admin.ModelAdmin):
    list_display = ('name',)


@admin.register(Loaf)
class LoafAdmin(admin.ModelAdmin):
    form = LoafAdminForm
    list_display = ('bread_type', 'machine', 'ready_at', 'is_active')
    list_filter = ('machine',)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "machine":
            last_machine_id = request.session.get('last_used_machine_id')
            if last_machine_id and BreadMachine.objects.filter(id=last_machine_id).exists():
                kwargs['initial'] = last_machine_id
            else:
                first_machine = BreadMachine.objects.first()
                if first_machine:
                    kwargs['initial'] = first_machine.id
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        duration = form.cleaned_data.get('ready_in')
        if duration:
            obj.ready_at = timezone.now() + duration
            
        request.session['last_used_machine_id'] = obj.machine.id
        super().save_model(request, obj, form, change)
