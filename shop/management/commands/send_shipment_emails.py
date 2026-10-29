"""Run periodically; only SMTP acceptance is recorded, never inbox delivery."""
from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from shop.models import ShipmentEmail


class Command(BaseCommand):
    help = "Process shipment outbox; retry pending/failed messages (console backend previews only)."

    def handle(self, *args, **options):
        ids = list(ShipmentEmail.objects.filter(status__in=["pending", "failed"]).values_list("pk", flat=True)[:100])
        for pk in ids:
            with transaction.atomic():
                message = ShipmentEmail.objects.select_for_update().select_related("order").get(pk=pk)
                if message.status not in ("pending", "failed"):
                    continue
                order = message.order
                message.attempts += 1
                try:
                    sent = send_mail(f"orangible 发货通知 · {order.pk}",
                        f"{order.recipient}，您好！\n订单 {order.pk} 已标记发货。\n"
                        f"订单金额：￥{order.total}\n本订单使用演示支付，未真实扣款。\n"
                        "这是课程实验通知，发货状态由实验管理员维护。",
                        settings.DEFAULT_FROM_EMAIL, [order.email], fail_silently=False)
                    if sent != 1:
                        raise RuntimeError("Backend did not accept message")
                except Exception as exc:
                    message.status = "failed"
                    # Avoid persisting SMTP responses or credentials in public logs.
                    message.last_error = type(exc).__name__
                else:
                    message.status = "accepted" if settings.EMAIL_BACKEND == "django.core.mail.backends.smtp.EmailBackend" else "preview"
                    message.last_error = ""
                message.processed_at = timezone.now()
                message.save()
                self.stdout.write(f"outbox {pk}: {message.status}, attempts={message.attempts}")
