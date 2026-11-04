import re
from functools import lru_cache
from django.utils.translation import get_language
from opencc import OpenCC
from .translations import EN

@lru_cache(maxsize=1)
def hk_converter():return OpenCC('s2hk')

def translate(value):
    if value is None:return ''
    text=str(value)
    language=get_language() or 'zh-hans'
    if language.startswith('zh-hant'):
        result=hk_converter().convert(text)
        for old,new in [('個人信息','個人資料'),('默認','預設'),('短信','短訊'),('登錄','登入'),('註銷','登出'),('電子郵箱','電郵地址'),('手機號','手提電話號碼'),('發貨','出貨'),('快遞','速遞'),('物流跟蹤','物流追蹤')]:
            result=result.replace(old,new)
        return result
    if language.startswith('en'):
        stripped=text.strip()
        translated=EN.get(stripped)
        if translated is None and stripped.endswith(" 已下架或库存不足，请调整购物车。"):
            name=stripped.removesuffix(" 已下架或库存不足，请调整购物车。")
            translated=EN.get(name,name)+" is unavailable or has insufficient stock. Adjust your cart."
        if translated is not None:return text.replace(stripped,translated) if stripped else text
    return text
