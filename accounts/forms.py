from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm

class UserRegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + ('email',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        placeholders = {
            'username': 'Choose a unique username',
            'email': 'Enter your email address',
            'password1': 'Create a strong password',
            'password2': 'Repeat your password'
        }
        for field in self.fields:
            if field in placeholders:
                self.fields[field].widget.attrs.update({'placeholder': placeholders[field]})
            self.fields[field].widget.attrs.update({'class': 'input-control'})

class UserUpdateForm(forms.ModelForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ['username', 'email']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        placeholders = {
            'username': 'Enter your username',
            'email': 'Enter your email address'
        }
        for field in self.fields:
            if field in placeholders:
                self.fields[field].widget.attrs.update({'placeholder': placeholders[field]})
            self.fields[field].widget.attrs.update({'class': 'input-control'})
