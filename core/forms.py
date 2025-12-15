from allauth.account.forms import SignupForm
from django import forms
from django.db.models import Q
from django.contrib.auth.models import User
from django.contrib.auth.forms import PasswordChangeForm
from .models import Room, RoomTenant, Payment, AddOn


class TenantSignupForm(SignupForm):
    first_name = forms.CharField(max_length=30, required=True, label='First name')
    last_name = forms.CharField(max_length=30, required=True, label='Last name')

    def save(self, request):
        user = super().save(request)
        user.first_name = self.cleaned_data.get('first_name', '').strip()
        user.last_name = self.cleaned_data.get('last_name', '').strip()
        user.save()
        return user

class RoomForm(forms.ModelForm):
    class Meta:
        model = Room
        fields = ['room_number', 'capacity']
        widgets = {
            'room_number': forms.TextInput(attrs={'class': 'form-control'}),
            'capacity': forms.NumberInput(attrs={'class': 'form-control'}),
        }


class RoomTenantForm(forms.ModelForm):
    tenant = forms.ModelChoiceField(
        queryset=User.objects.filter(is_staff=False).order_by('first_name', 'last_name', 'username'),
        required=True,
        label='Tenant',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    room = forms.ModelChoiceField(
        queryset=Room.objects.all().order_by('room_number'),
        required=True,
        label='Room',
        help_text='Select a room for this tenant. You can move the tenant to a different room.',
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta:
        model = RoomTenant
        fields = ['tenant', 'room', 'move_in_date']
        widgets = {
            'tenant': forms.Select(attrs={'class': 'form-select'}),
            'room': forms.Select(attrs={'class': 'form-select'}),
            'move_in_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filter rooms to show only available ones (not full) or the current room
        if self.instance and self.instance.pk:
            # When editing, include the current room even if it's full
            current_room = self.instance.room
            available_rooms = Room.objects.filter(
                Q(status='vacant') | Q(id=current_room.id)
            ).order_by('room_number')
        else:
            # When adding, only show available rooms
            available_rooms = Room.objects.filter(status='vacant').order_by('room_number')
        
        self.fields['room'].queryset = available_rooms


class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ['amount', 'payment_month', 'payment_date', 'status']
        widgets = {
            'amount': forms.NumberInput(attrs={'class': 'form-control'}),
            'payment_month': forms.DateInput(attrs={'class': 'form-control', 'type': 'month'}),
            'payment_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }

class AddOnForm(forms.ModelForm):
    class Meta:
        model = AddOn
        fields = ['description', 'amount']
        widgets = {
            'description': forms.TextInput(attrs={'placeholder': 'e.g., Rice Cooker', 'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control'}),
        }


class TenantCreationForm(forms.ModelForm):
    """
    Landlord-only form for creating tenant accounts with an initial password.
    Only username and password are captured; tenant fills in their profile later.
    """
    USERNAME_PREFIX = "Tenant_"
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Initial password'}),
        label='Initial Password',
        help_text='Share this with the tenant. They must change it at first login.',
    )

    class Meta:
        model = User
        fields = ['username', 'password']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'password': forms.PasswordInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Ensure ui classes on password and form fields
        for field_name, field in self.fields.items():
            if 'class' not in field.widget.attrs:
                if isinstance(field.widget, forms.PasswordInput) or isinstance(field.widget, forms.TextInput) or isinstance(field.widget, forms.EmailInput):
                    field.widget.attrs.update({'class': 'form-control'})
        # Pre-fill the username field with the required prefix for convenience.
        if not self.initial.get('username'):
            self.initial['username'] = self.USERNAME_PREFIX
        self.fields['username'].widget.attrs.setdefault('placeholder', f'{self.USERNAME_PREFIX}Benjie')

    def clean_username(self):
        username = self.cleaned_data['username']
        # Ensure the prefix is present even if the landlord omits it
        if not username.startswith(self.USERNAME_PREFIX):
            username = f"{self.USERNAME_PREFIX}{username}"
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError('This username is already taken.')
        return username

    def save(self, commit=True):
        user = super().save(commit=False)
        user.is_staff = False
        user.is_active = True
        # first/last names intentionally left blank for tenant to fill later
        password = self.cleaned_data['password']
        user.set_password(password)
        if commit:
            user.save()
        return user


class TenantFirstLoginForm(PasswordChangeForm):
    """
    Collect first/last name, email plus enforce password change on first login.
    """
    first_name = forms.CharField(max_length=30, required=True, label='First name')
    last_name = forms.CharField(max_length=30, required=True, label='Last name')
    email = forms.EmailField(required=True, label='Email')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data['first_name'].strip()
        user.last_name = self.cleaned_data['last_name'].strip()
        user.email = self.cleaned_data['email'].strip()
        if commit:
            user.save()
        return user


