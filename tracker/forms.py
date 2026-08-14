import datetime
from django import forms
from django.utils import timezone
from .models import Loaf, BreadMachine, Comment
from django.contrib.auth.models import User

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

class LoafForm(forms.ModelForm):
    ready_in = forms.CharField(
        label="Ready in (HH:MM)",
        initial="03:00",
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
        fields = ['machine', 'bread_type']
        widgets = {
            'bread_type': forms.TextInput(attrs={'placeholder': 'e.g., Sourdough Boule', 'class': 'form-control'}),
            'machine': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
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

class LoafEditForm(forms.ModelForm):
    class Meta:
        model = Loaf
        fields = ['machine', 'bread_type', 'started_at', 'ready_at']
        widgets = {
            'bread_type': forms.TextInput(attrs={'placeholder': 'e.g., Sourdough Boule', 'class': 'form-control'}),
            'machine': forms.Select(attrs={'class': 'form-control'}),
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
        # Format existing datetime objects so browser inputs can display them properly
        if self.instance and self.instance.started_at:
            self.initial['started_at'] = self.instance.started_at.strftime('%Y-%m-%dT%H:%M')
        if self.instance and self.instance.ready_at:
            self.initial['ready_at'] = self.instance.ready_at.strftime('%Y-%m-%dT%H:%M')

class BreadMachineForm(forms.ModelForm):
    class Meta:
        model = BreadMachine
        # Included 'image' and 'notes' from the BreadMachine model
        fields = ['name', 'image', 'notes']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'e.g., Panasonic SD-2500', 'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Machine details or manual notes...', 'class': 'form-control'}),
        }

class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['text']
        widgets = {
            'text': forms.Textarea(attrs={'rows': 3, 'placeholder': 'How did this loaf turn out?', 'class': 'form-control'}),
        }
