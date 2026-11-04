"""Rebuild browser translations from the authored server catalogue."""
import hashlib,json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from opencc import OpenCC
from shop.translations import EN
phrases=set()
for name in ('account.js','exchange-rates.js','fruit-live.js'):
    source=(ROOT/'static/shop'/name).read_text('utf-8')
    phrases.update(s.strip() for s in re.findall(r"'([^'\n]*)'",source) if re.search(r'[\u3400-\u9fff]',s))
phrases.update(s for s in EN if any(word in s for word in ('验证码','手机号','短信','请求')))
missing=phrases-EN.keys()
if missing:raise ValueError('Missing browser translations: '+repr(missing))
converter=OpenCC('s2hk')
en={s:EN[s] for s in sorted(phrases)}
def hong_kong(text):
    result=converter.convert(text)
    for old,new in [('個人信息','個人資料'),('默認','預設'),('短信','短訊'),('登錄','登入'),('註銷','登出'),('電子郵箱','電郵地址'),('手機號','手提電話號碼'),('發貨','出貨'),('快遞','速遞'),('物流跟蹤','物流追蹤')]:result=result.replace(old,new)
    return result
hk={s:hong_kong(s) for s in sorted(phrases)}
script='(()=>{const en='+json.dumps(en,ensure_ascii=False)+';const hk='+json.dumps(hk,ensure_ascii=False)+";window.orangibleTranslate=s=>{const lang=document.documentElement.lang;const d=lang==='en'?en:lang==='zh-HK'?hk:{};const key=s.trim();return Object.hasOwn(d,key)?s.replace(key,d[key]):s;};})();"
asset=ROOT/'static/shop/language.js'
asset.write_text(script,encoding='utf-8')
p=ROOT/'templates/base.html'
source=p.read_text('utf-8')
source=re.sub(r"language.js' %}\?v=[a-f0-9]+", "language.js' %}?v="+hashlib.sha256(asset.read_bytes()).hexdigest()[:12],source)
p.write_text(source,encoding='utf-8')
print('Browser translation catalogue rebuilt:',len(phrases))
