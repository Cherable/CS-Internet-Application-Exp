from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User


class RegistrationForm(UserCreationForm):
    email = forms.EmailField(label="电子邮箱", required=True)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email")


class QuantityForm(forms.Form):
    quantity = forms.IntegerField(label="数量", min_value=1, max_value=999)
