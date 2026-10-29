/* Actual local browser acceptance test using an isolated database and random credentials.
   Requires playwright + Edge. Run: node scripts/capture-stage2.cjs */
const { chromium } = require('playwright');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { spawn, spawnSync } = require('node:child_process');
const root = path.resolve(__dirname, '..');
const output = path.join(root, 'docs/stages/stage-02');
const shots = path.join(output, 'screenshots');
const runId = crypto.randomBytes(5).toString('hex');
const py = process.env.PYTHON || path.join(root, '.venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python');
const password = crypto.randomBytes(24).toString('base64url');
const username = 'buyer_' + runId;
const env = { ...process.env, DJANGO_DEBUG: 'true', DB_ENGINE: 'sqlite',
  SQLITE_PATH: path.join(root, '.runtime', 'browser-' + runId + '.sqlite3'),
  DEMO_PAYMENT_ENABLED: 'true', EMAIL_BACKEND: 'django.core.mail.backends.console.EmailBackend',
  STAGE2_ADMIN_USER: 'seller_' + runId, STAGE2_ADMIN_PASSWORD: password, PYTHONIOENCODING: 'utf-8' };
function django(args) {
  const result = spawnSync(py, ['manage.py', ...args], { cwd: root, env, encoding: 'utf8', windowsHide: true });
  if (result.status !== 0) throw new Error(result.stdout + result.stderr);
  return result.stdout;
}
(async () => {
  fs.mkdirSync(shots, { recursive: true }); fs.mkdirSync(path.join(root, '.runtime'), { recursive: true });
  django(['migrate', '--noinput']); django(['seed_demo']);
  django(['shell', '-c', "import os; from django.contrib.auth.models import User; User.objects.create_superuser(os.environ['STAGE2_ADMIN_USER'],'seller@example.com',os.environ['STAGE2_ADMIN_PASSWORD'])"]);
  const serverLog = fs.openSync(path.join(root, '.runtime', 'browser-server-' + runId + '.log'), 'w');
  const server = spawn(py, ['manage.py', 'runserver', '127.0.0.1:8002', '--noreload'], { cwd: root, env, stdio: ['ignore', serverLog, serverLog], windowsHide: true });
  let browser;
  try {
    const base = 'http://127.0.0.1:8002';
    let ready = false;
    for (let i=0;i<60;i++) {
      try { if ((await fetch(base)).ok) { ready = true; break; } } catch {}
      await new Promise(r => setTimeout(r, 250));
    }
    if (!ready) throw new Error('Local server did not start');
    browser = await chromium.launch({ channel: 'msedge', headless: true });
    const customer = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
    const page = await customer.newPage();
    const errors = []; page.on('pageerror', e => errors.push(e.message));
    await page.goto(base + '/accounts/register/');
    await page.locator('#id_username').fill(username);
    await page.locator('#id_email').fill('buyer@example.com');
    await page.locator('#id_password1').fill(password);
    await page.locator('#id_password2').fill(password);
    await page.getByRole('button', { name: '创建账户' }).click();
    await page.waitForURL(base + '/');
    await page.getByRole('heading', { name: '点阵学习笔记本' }).getByRole('link').click();
    await page.getByLabel('数量', { exact: true }).fill('2');
    await page.getByRole('button', { name: '加入购物车' }).click();
    await page.getByRole('link', { name: '去结算' }).click();
    await page.getByLabel('收件人').fill('课程演示同学');
    await page.getByLabel('收货地址').fill('校园教学楼实验室（本地演示）');
    await page.screenshot({ path: path.join(shots, '01-checkout.png'), fullPage: true });
    await page.getByRole('button', { name: '提交订单' }).click();
    await page.waitForURL(/\/orders\/[0-9a-f-]+\/$/);
    const orderUrl = page.url();
    if (!(await page.locator('.summary').innerText()).includes('37.80')) throw new Error('Incorrect order amount');
    await page.screenshot({ path: path.join(shots, '02-pending-order.png'), fullPage: true });
    await page.getByRole('button', { name: '确认演示付款（不扣款）' }).click();
    await page.getByRole('heading', { name: '已付款（演示）', exact: true }).waitFor();
    await page.screenshot({ path: path.join(shots, '03-demo-paid.png'), fullPage: true });
    const staff = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
    const admin = await staff.newPage(); admin.on('pageerror', e => errors.push(e.message));
    await admin.goto(base + '/admin/login/');
    await admin.locator('#id_username').fill(env.STAGE2_ADMIN_USER);
    await admin.locator('#id_password').fill(password);
    await admin.locator('input[type=submit]').click();
    await admin.waitForURL(base + '/admin/');
    await admin.goto(base + '/sales/');
    if ((await admin.locator('.sales-stats .price').first().innerText()) !== '￥37.80') throw new Error('Incorrect sales revenue or currency format');
    await admin.screenshot({ path: path.join(shots, '04-sales.png'), fullPage: true });
    await admin.getByRole('button', { name: '确认发货' }).click();
    await admin.getByText('已标记发货，通知邮件进入待处理队列。').waitFor();
    const mailResult = django(['send_shipment_emails']);
    if (!mailResult.includes('preview')) throw new Error('Console email preview missing');
    fs.writeFileSync(path.join(output, 'email-preview.txt'), 'Console backend: local preview, NOT real delivery.\n' + mailResult);
    await page.goto(orderUrl);
    await page.getByRole('heading', { name: '已发货', exact: true }).waitFor();
    if (!(await page.locator('.summary').innerText()).includes('本地预览，未投递')) throw new Error('Mail status incorrectly labelled');
    await page.screenshot({ path: path.join(shots, '05-shipped-order.png'), fullPage: true });
    await admin.goto(base + '/admin/shop/shipmentemail/');
    await admin.getByText('本地预览，未投递', { exact: true }).waitFor();
    await admin.screenshot({ path: path.join(shots, '06-email-outbox.png'), fullPage: true });
    // Real admin CRUD through rendered forms, then remove only this test product.
    await admin.goto(base + '/admin/shop/product/add/');
    await admin.locator('#id_category').selectOption({ label: '学习文具' });
    await admin.locator('#id_name').fill('CRUD验收商品');
    await admin.locator('#id_price').fill('12.50');
    await admin.locator('#id_stock').fill('8');
    await admin.locator('input[name=_save]').click();
    await admin.locator('#result_list').getByRole('link', { name: 'CRUD验收商品', exact: true }).click();
    const productUrl = admin.url();
    await admin.locator('#id_stock').fill('9');
    await admin.locator('input[name=_save]').click();
    await admin.locator('#result_list').getByRole('link', { name: 'CRUD验收商品', exact: true }).waitFor();
    await admin.screenshot({ path: path.join(shots, '07-product-admin.png'), fullPage: true });
    await admin.goto(productUrl.replace(/change\/$/, 'delete/'));
    await admin.locator('input[type=submit]').click();
    if (await admin.locator('#result_list').getByRole('link', { name: 'CRUD验收商品', exact: true }).count()) throw new Error('Admin delete failed');
    await page.goto(base + '/orders/');
    await page.screenshot({ path: path.join(shots, '08-order-history.png'), fullPage: true });
    await page.goto(orderUrl); await page.setViewportSize({ width: 390, height: 844 });
    await page.screenshot({ path: path.join(shots, '09-mobile-order.png'), fullPage: true });
    if (await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth)) throw new Error('Mobile horizontal overflow');
    if (errors.length) throw new Error(errors.join('\n'));
    const result = 'PASS: actual local browser checkout -> demo payment -> staff sales -> shipping -> console email preview -> order history; admin product create/update/delete; mobile 390px no horizontal overflow; no page errors.\n9 screenshots saved. Isolated SQLite browser database; MySQL concurrency tested separately. No real payment or email delivery.\n';
    fs.writeFileSync(path.join(output, 'browser-results.txt'), result); console.log(result);
  } finally {
    if (browser) await browser.close();
    server.kill(); fs.closeSync(serverLog);
  }
})().catch(e => { console.error(e); process.exitCode = 1; });
