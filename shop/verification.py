"""Session captcha and rate-limited, single-use phone verification."""
import hashlib, hmac, json, secrets, time, re
from datetime import timedelta
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from .models import PhoneChallenge, VerificationThrottle

def normalize_phone(value):
    value = re.sub(r"[\s()-]", "", value or "")
    if re.fullmatch(r"1[3-9]\d{9}", value): value = "+86" + value
    if value and not re.fullmatch(r"\+861[3-9]\d{9}", value):
        raise ValueError("目前短信绑定支持中国大陆手机号（+86）。")
    return value

def new_captcha(session):
    answer = "".join(secrets.choice("23456789ABCDEFGHJKLMNPQRSTUVWXYZ") for _ in range(5))
    session["captcha"] = {"answer": answer, "expires": time.time()+300, "attempts": 0}
    return answer

def check_captcha(session, answer, consume=False):
    row = session.get("captcha", {})
    valid = bool(row and row.get("expires", 0)>time.time() and row.get("attempts", 5)<5 and hmac.compare_digest(row.get("answer", ""), (answer or "").upper().strip()))
    row["attempts"] = row.get("attempts", 0)+1
    if consume or not valid and row["attempts"]>=5: session.pop("captcha", None)
    else: session["captcha"] = row
    return valid

def code_hash(code):
    return hmac.new(settings.SECRET_KEY.encode(), str(code).encode(), hashlib.sha256).hexdigest()

@transaction.atomic
def throttle(phone, ip):
    now = timezone.now()
    for label, maximum in sorted([(phone,5),("ip:"+ip,10)]):
        key = code_hash(label)
        VerificationThrottle.objects.get_or_create(key=key, defaults={"window_started":now})
        row = VerificationThrottle.objects.select_for_update().get(pk=key)
        if row.window_started < now-timedelta(hours=1): row.window_started=now;row.count=0
        if row.count>=maximum or label==phone and row.last_sent and row.last_sent>now-timedelta(seconds=60):
            raise ValueError("验证码请求过于频繁，请稍后再试。")
        row.count+=1;row.last_sent=now;row.save()

def send_phone_code(session, phone, ip):
    backend = settings.SMS_BACKEND
    demo = backend=="demo" and settings.DEBUG
    if not demo and backend!="aliyun": raise ValueError("短信服务尚未配置，可不绑定手机号完成注册。")
    throttle(phone, ip)
    if not session.session_key: session.create()
    code = str(secrets.randbelow(900000)+100000)
    if not demo:
        if not all([settings.ALIYUN_SMS_ACCESS_KEY_ID,settings.ALIYUN_SMS_ACCESS_KEY_SECRET,settings.ALIYUN_SMS_SIGN_NAME,settings.ALIYUN_SMS_TEMPLATE_CODE]):
            raise ValueError("短信服务尚未配置，可不绑定手机号完成注册。")
        try:
            from alibabacloud_dysmsapi20170525.client import Client
            from alibabacloud_dysmsapi20170525.models import SendSmsRequest
            from alibabacloud_tea_openapi.models import Config
            client=Client(Config(access_key_id=settings.ALIYUN_SMS_ACCESS_KEY_ID,access_key_secret=settings.ALIYUN_SMS_ACCESS_KEY_SECRET,endpoint="dysmsapi.aliyuncs.com",connect_timeout=5000,read_timeout=5000))
            result=client.send_sms(SendSmsRequest(phone_numbers=phone[3:],sign_name=settings.ALIYUN_SMS_SIGN_NAME,template_code=settings.ALIYUN_SMS_TEMPLATE_CODE,template_param=json.dumps({"code":code})))
            if result.body.code!="OK": raise ValueError("provider rejected")
        except Exception:
            raise ValueError("短信发送失败，请稍后重试。") from None
    PhoneChallenge.objects.filter(session_key=session.session_key,phone=phone,consumed=False).update(consumed=True)
    row=PhoneChallenge.objects.create(session_key=session.session_key,phone=phone,code_hash=code_hash(code),expires_at=timezone.now()+timedelta(minutes=5),demo=demo)
    session["phone_challenge"] = row.pk
    return code if demo else None

def validate_phone(session, phone, code, consume=False):
    with transaction.atomic():
        row=PhoneChallenge.objects.select_for_update().filter(pk=session.get("phone_challenge"),session_key=session.session_key,phone=phone,consumed=False).first()
        if not row or row.expires_at<=timezone.now() or row.attempts>=5:
            valid=False;expired=True;demo=False
        else:
            expired=False;demo=row.demo
            valid=hmac.compare_digest(row.code_hash,code_hash(code))
            if not valid:row.attempts+=1
            if valid and consume:row.consumed=True
            row.save(update_fields=["attempts","consumed"])
    if expired:raise ValueError("短信验证码已失效，请重新获取。")
    if not valid:raise ValueError("短信验证码不正确。")
    return demo
