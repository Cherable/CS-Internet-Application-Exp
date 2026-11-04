import secrets
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction, IntegrityError
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.http import require_POST
from .models import UserProfile
from .verification import new_captcha,check_captcha,normalize_phone,send_phone_code,validate_phone

def captcha(request):
    answer=new_captcha(request.session)
    letters="".join(f'<text x="{20+i*30}" y="37" transform="rotate({secrets.randbelow(15)-7} {20+i*30} 37)">{c}</text>' for i,c in enumerate(answer))
    lines="".join(f'<path d="M0 {secrets.randbelow(55)} L190 {secrets.randbelow(55)}" stroke="#9bad8d"/>' for _ in range(5))
    body=f'<svg xmlns="http://www.w3.org/2000/svg" width="190" height="55" viewBox="0 0 190 55"><rect width="190" height="55" fill="#edf1e5"/>{lines}<g fill="#193c30" font-size="27" font-family="monospace" font-weight="bold">{letters}</g></svg>'
    response=HttpResponse(body,content_type="image/svg+xml");response['Cache-Control']='no-store';return response

@require_POST
def send_code(request):
    if not check_captcha(request.session,request.POST.get('captcha')):
        return JsonResponse({'error':'图片验证码不正确或已过期。'},status=400)
    try:
        phone=normalize_phone(request.POST.get('phone'))
        if not phone: raise ValueError('请先填写手机号。')
        demo=send_phone_code(request.session,phone,request.META.get('REMOTE_ADDR','unknown'))
        data={'message':'验证码已发送，5分钟内有效。'}
        if demo:data={'message':'本地短信演示：未真实发送。','demo_code':demo}
        return JsonResponse(data)
    except ValueError as exc:return JsonResponse({'error':str(exc)},status=400)

@login_required
def profile(request):
    from .forms import ProfileForm
    row,_=UserProfile.objects.get_or_create(user=request.user)
    form=ProfileForm(request.POST or None,instance=row,user=request.user)
    if request.method=='POST' and form.is_valid():
        phone=form.cleaned_data.get('phone') or None
        changed=phone!=form.old_phone
        if changed and phone:
            try:validate_phone(request.session,phone,form.cleaned_data.get('sms_code',''))
            except ValueError as exc:form.add_error('sms_code',str(exc))
        if not form.errors:
            try:
                with transaction.atomic():
                    obj=form.save(commit=False)
                    if changed:
                        demo=validate_phone(request.session,phone,form.cleaned_data['sms_code'],consume=True) if phone else False
                        obj.phone_demo=demo;obj.phone_verified=bool(phone and not demo)
                    obj.save()
                    request.user.email=form.cleaned_data['email'];request.user.save(update_fields=['email'])
                messages.success(request,'个人信息已保存。');return redirect('profile')
            except (IntegrityError,ValueError):form.add_error('phone','手机号已被使用或验证码失效。')
    return render(request,'shop/profile.html',{'form':form,'profile':row,'sms_demo':settings.DEBUG and settings.SMS_BACKEND=='demo'})
