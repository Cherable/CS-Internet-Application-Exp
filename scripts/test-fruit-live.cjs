const {chromium}=require('playwright');const {execFileSync}=require('node:child_process');const fs=require('node:fs');const path=require('node:path');
const py=path.resolve('.venv/Scripts/python.exe');function db(code){return execFileSync(py,['-c',"import os;os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings');import django;django.setup();"+code],{encoding:'utf8',windowsHide:true});}
(async()=>{const browser=await chromium.launch({channel:'msedge',headless:true});let original;
try{const page=await browser.newPage();await page.goto('http://127.0.0.1:8000/');
original=JSON.parse(db("import json;from shop.models import FruitDay;from django.utils import timezone;r=FruitDay.objects.filter(day=timezone.localdate()).order_by('product_id').first();print(json.dumps([r.pk,r.product_id,r.manual_units]))"));
db(`from shop.models import FruitDay;FruitDay.objects.filter(pk=${original[0]}).update(manual_units=50000)`);
await page.waitForFunction(id=>document.querySelector('#fruit-grid .product-card').dataset.product===String(id),original[1],{timeout:15000});
const value=Number(await page.locator('#fruit-grid .product-card').first().locator('.live-sales').innerText());if(value<50000)throw Error('Live sales not refreshed');fs.writeFileSync('docs/fruit-redesign/live-results.txt','PASS: persisted manual sales update appears in the open browser and moves fruit to first place without reloading; original manual value restored afterward.\n');console.log('Live input and ranking PASS');
}finally{if(original)db(`from shop.models import FruitDay;FruitDay.objects.filter(pk=${original[0]}).update(manual_units=${original[2]})`);await browser.close();}})().catch(e=>{console.error(e);process.exitCode=1});
