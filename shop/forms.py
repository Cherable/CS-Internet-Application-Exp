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


class CheckoutForm(forms.Form):
    token = forms.UUIDField(widget=forms.HiddenInput)
    recipient = forms.CharField(label="收件人", max_length=80)
    email = forms.EmailField(label="发货通知邮箱")
    address = forms.CharField(label="收货地址", max_length=300, widget=forms.Textarea(attrs={"rows": 3}))
