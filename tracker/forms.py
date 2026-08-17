"""
forms.py = python script for handling all the forms, all in one place, including:
    * UserProfileForm
    * AccountRequestForm
    * LoafForm
    * LoafEditForm
    * BreadMachineForm
    * CommentForm
"""


import datetime
from django import forms
from django.utils import timezone
from .models import Loaf, BreadMachine, Comment, SiteSetting
from django.contrib.auth.models import User

# Form to allow user to update personal information
class UserProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }

# Form to request a new account (leads to account creation but not activation)
class AccountRequestForm(forms.ModelForm):
    first_name = forms.CharField(required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-control'}))

    # Get them to explain why they want an account, to filter random signups
    reason = forms.CharField(
        label="Please explain who you are / why you need an account",
        required=True,
        widget=forms.Textarea(attrs={
            'rows': 3,
            'class': 'form-control',
            'placeholder': 'e.g., I am a member of the GoBM and want to log my breadmaking.'
        })
    )
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        if password and confirm_password and password != confirm_password:
            raise forms.ValidationError("Passwords do not match.")
        return cleaned_data

# Form to create a new loaf
class LoafForm(forms.ModelForm):
    ready_in = forms.CharField(
        label="Ready in",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g. 03:30 or 3:30'
        })
    )
    initial_note = forms.CharField(
        required=False,
        label="Note / Recipe (Optional)",
        widget=forms.Textarea(attrs={
            'rows': 3,
            'placeholder': 'e.g. 50% whole wheat, added sunflower seeds...',
            'class': 'form-control'
        })
    )

    class Meta:
        model = Loaf
        fields = ['bread_type', 'machine', 'is_dough_only']
        widgets = {
            'bread_type': forms.TextInput(attrs={'placeholder': 'e.g., White loaf', 'class': 'form-control'}),
            'machine': forms.Select(attrs={'class': 'form-control'}),
            'is_dough_only': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Check global site settings
        settings, _ = SiteSetting.objects.get_or_create(id=1)
        
        # If dough mode is disabled, strip the field from the form
        if not settings.show_dough_section and 'is_dough_only' in self.fields:
            del self.fields['is_dough_only']

        self.label_suffix = ""
        # Exclude machines currently running an active loaf
        now = timezone.now()
        self.fields['machine'].queryset = BreadMachine.objects.exclude(loaves__ready_at__gt=now)

    def clean_ready_in(self):
        """Validates that the input is in valid HH:MM format."""
        data = self.cleaned_data['ready_in'].strip()
        try:
            parts = data.split(':')
            if len(parts) != 2:
                raise ValueError
            hours, minutes = int(parts[0]), int(parts[1])
            if hours < 0 or minutes < 0 or minutes > 59:
                raise ValueError
            return hours, minutes
        except (ValueError, TypeError):
            raise forms.ValidationError("Enter time in HH:MM format (e.g. 03:30 or 3:30).")

    def save(self, commit=True):
        instance = super().save(commit=False)
        hours, minutes = self.cleaned_data['ready_in']
        
        # Calculate ready_at timestamp based on current time + duration
        instance.ready_at = timezone.now() + datetime.timedelta(hours=hours, minutes=minutes)
        
        if commit:
            instance.save()
        return instance

# Form to edit an existing loaf (gives warning if user wasn't the one who started the loaf,
# but still permits editing)
class LoafEditForm(forms.ModelForm):
    minutes_proving = forms.IntegerField(
        required=False,
        min_value=0,
        label="Proving Time (minutes)",
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    minutes_baking = forms.IntegerField(
        required=False,
        min_value=0,
        label="Oven Bake Time (minutes)",
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = Loaf
        fields = ['machine', 'bread_type', 'is_dough_only', 'started_at', 'ready_at']
        widgets = {
            'bread_type': forms.TextInput(attrs={'placeholder': 'e.g., White loaf', 'class': 'form-control'}),
            'machine': forms.Select(attrs={'class': 'form-control'}),
            'is_dough_only': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
            'started_at': forms.DateTimeInput(
                format='%Y-%m-%dT%H:%M',
                attrs={'type': 'datetime-local', 'class': 'form-control'}
            ),
            'ready_at': forms.DateTimeInput(
                format='%Y-%m-%dT%H:%M',
                attrs={'type': 'datetime-local', 'class': 'form-control'}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.label_suffix = ""
        
        # Tell Django to accept ISO format input on submission
        self.fields['started_at'].input_formats = ['%Y-%m-%dT%H:%M']
        self.fields['ready_at'].input_formats = ['%Y-%m-%dT%H:%M']

        # Convert stored UTC datetimes to local time before formatting for the browser input
        if self.instance and self.instance.pk:
            if self.instance.started_at:
                local_start = timezone.localtime(self.instance.started_at)
                self.initial['started_at'] = local_start.strftime('%Y-%m-%dT%H:%M')
            if self.instance.ready_at:
                local_ready = timezone.localtime(self.instance.ready_at)
                self.initial['ready_at'] = local_ready.strftime('%Y-%m-%dT%H:%M')

            # Populate proving and baking minutes
            if self.instance.is_dough_only:
                self.initial['minutes_proving'] = self.instance.minutes_proving
                self.initial['minutes_baking'] = self.instance.minutes_baking

    def save(self, commit=True):
        instance = super().save(commit=False)

        # Recalculate underlying timestamps if dough-only fields were modified
        if instance.is_dough_only and instance.ready_at:
            bake_mins = self.cleaned_data.get('minutes_baking')
            prov_mins = self.cleaned_data.get('minutes_proving')

            if bake_mins is not None:
                instance.started_oven_bake_at = instance.ready_at - datetime.timedelta(minutes=bake_mins)

            if prov_mins is not None and instance.started_oven_bake_at:
                instance.removed_from_machine_at = instance.started_oven_bake_at - datetime.timedelta(minutes=prov_mins)

        if commit:
            instance.save()
        return instance

# Form to add an additional bread machine to the database
class BreadMachineForm(forms.ModelForm):
    class Meta:
        model = BreadMachine
        # Included 'image' and 'notes' from the BreadMachine model
        fields = ['name', 'image', 'notes']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'e.g., Panasonic SD-2500', 'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Machine details or manual notes...', 'class': 'form-control'}),
        }

# Form to add comments to a loaf
class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['text']
        widgets = {
            'text': forms.Textarea(attrs={'rows': 3, 'placeholder': 'How did this loaf turn out?', 'class': 'form-control'}),
        }
