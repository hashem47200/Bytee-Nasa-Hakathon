from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError

User = get_user_model()


class CrewLoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'input', 'placeholder': 'Commander handle or callsign', 'autofocus': True})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'input', 'placeholder': '••••••••••••'})
    )


class CrewRegisterForm(forms.ModelForm):
    username = forms.CharField(
        max_length=150,
        help_text="Choose an explorer handle (at least 3 characters).",
        widget=forms.TextInput(attrs={'placeholder': 'e.g. CommanderShepard'})
    )
    email = forms.EmailField(
        required=True,
        help_text="Required for official certificate verification records.",
        widget=forms.EmailInput(attrs={'placeholder': 'astronaut@nasa.gov'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Minimum 6 characters'}),
        help_text="At least 6 characters."
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Repeat your password'}),
        label="Confirm Password"
    )

    class Meta:
        model = User
        fields = ['username', 'email']

    def clean_username(self):
        username = self.cleaned_data['username'].strip()
        if len(username) < 3:
            raise ValidationError("Explorer handle must be at least 3 characters.")
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError("This callsign is already claimed. Please choose another.")
        return username

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('password')
        p2 = cleaned_data.get('confirm_password')
        if p1 and p2 and p1 != p2:
            self.add_error('confirm_password', "Telemetry mismatch: passwords do not match.")
        if p1 and len(p1) < 6:
            self.add_error('password', "Password must be at least 6 characters.")
        return cleaned_data
