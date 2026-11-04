"""Time-based demo timeline, independent from actual shipping and emails."""
from datetime import timedelta
from django.utils import timezone

def tracking_for(order, now=None):
    if not order.paid_at or order.status not in ('paid','shipped'):return None
    now=now or timezone.now()
    transit=max(24,order.simulated_transit_hours)
    total=max(48,order.simulated_dispatch_hours+transit)
    overseas=total>96
    checkpoints=[(0,'商家已发货','包裹已完成出库，等待快递员揽收。'),(1,'快递已揽收','揽收完成，包裹即将发往分拨中心。'),(12,'已到达始发分拨中心','完成分拣，等待干线运输。')]
    if overseas:checkpoints.append((total*.35,'跨境运输与清关处理中','海外段转运与模拟清关，等待进入目的地配送网络。'))
    checkpoints.extend([(max(24,total*.45),'干线运输中','包裹正运往收件地区的转运中心。'),(total-12,'已到达目的地分拨中心','目的地分拣完成，转交本地配送站。'),(total-4,'派送中','配送员已出发，请留意收货通知。'),(total,'已签收','模拟送达完成，建议按商品标签安排保存与赏味。')])
    events=[{'at':order.paid_at+timedelta(hours=hours),'title':title,'text':text,'done':now>=order.paid_at+timedelta(hours=hours)} for hours,title,text in sorted(checkpoints)]
    done=[e for e in events if e['done']]
    return {'number':'SIM'+order.pk.hex[:16].upper(),'events':events,'latest':done[-1]['title'],'eta':order.paid_at+timedelta(hours=total),'arrived':events[-1]['done']}
