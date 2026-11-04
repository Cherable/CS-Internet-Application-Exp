from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User


class RegistrationForm(UserCreationForm):
    email = forms.EmailField(label="电子邮箱", required=True)

    phone = forms.CharField(label="手机号（可选）", required=False)
    sms_code = forms.CharField(label="短信验证码", required=False, max_length=6)
    captcha = forms.CharField(label="图片验证码", max_length=5)

    def clean_phone(self):
        from .verification import normalize_phone
        from .models import UserProfile
        try: value = normalize_phone(self.cleaned_data.get("phone"))
        except ValueError as exc: raise forms.ValidationError(str(exc))
        if value and UserProfile.objects.filter(phone=value).exists(): raise forms.ValidationError("手机号已被使用。")
        return value

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


from .models import UserProfile
class ProfileForm(forms.ModelForm):
    email = forms.EmailField(label="电子邮箱")
    sms_code = forms.CharField(label="短信验证码", required=False, max_length=6)
    captcha = forms.CharField(label="图片验证码（发送短信时填写）", required=False, max_length=5)
    current_password = forms.CharField(label="当前密码（修改手机号时填写）", required=False, widget=forms.PasswordInput)
    class Meta:
        model = UserProfile
        fields = ['display_name','email','default_recipient','default_address','phone']
        labels = {'display_name':'昵称','default_recipient':'默认收件人','default_address':'默认收货地址','phone':'手机号（可选）'}
        widgets = {'default_address':forms.Textarea(attrs={'rows':3})}
    def __init__(self,*args,user,**kwargs):
        self.user=user
        self.old_phone=kwargs['instance'].phone
        super().__init__(*args,**kwargs)
        self.fields['email'].initial=user.email
    def clean_phone(self):
        from .verification import normalize_phone
        try:return normalize_phone(self.cleaned_data.get('phone')) or None
        except ValueError as exc:raise forms.ValidationError(str(exc))
    def clean(self):
        data=super().clean()
        if data.get('phone')!=self.old_phone and not self.user.check_password(data.get('current_password','')):
            self.add_error('current_password','修改或解除绑定需要正确的当前密码。')
        return data
