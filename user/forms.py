from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.contrib.auth.models import User
from django import forms


class SignUpForm(UserCreationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # kept if altered to use email instead of username as user key to ensure password reset via email is possible
        # self.fields['username'].required = False
        # self.fields['email'].required = True

        # since django does not support placeholders for password input fields
        self.fields['password1'].widget.attrs['placeholder'] = '••••••••'
        self.fields['password2'].widget.attrs.update({'placeholder': '••••••••'})

    class Meta:
        model = User
        fields = ['username', 'password1', 'password2']
        widgets = {
            'email': forms.EmailInput(attrs={'placeholder': 'example@gmail.com'}),
            'username': forms.TextInput(attrs={'placeholder': 'Username'})
        }


class MinUserChangeForm(UserChangeForm):
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']
        widgets = {
            'username': forms.TextInput(attrs={'placeholder': 'Username'}),
            'email': forms.EmailInput(attrs={'placeholder': 'example@gmail.com', 'required': False}),
        }
