/* Optional browser smoke test. Install playwright and Microsoft Edge first.
   Run the development server, then: node scripts/capture-stage1.cjs
   Images come from the running application, never a mockup. */
const { chromium } = require('playwright');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');

(async () => {
  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 }, deviceScaleFactor: 1 });
  const output = path.resolve(__dirname, '../docs/stages/stage-01/screenshots');
  fs.mkdirSync(output, { recursive: true });
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  const base = 'http://127.0.0.1:8000';
  await page.goto(base);
  await page.screenshot({ path: path.join(output, '01-catalog.png'), fullPage: true });
  await page.getByRole('link', { name: '注册', exact: true }).click();
  await page.screenshot({ path: path.join(output, '02-register.png'), fullPage: true });
  const username = 'demo_' + crypto.randomBytes(4).toString('hex');
  const password = crypto.randomBytes(18).toString('base64url');
  await page.locator('#id_username').fill(username);
  await page.locator('#id_email').fill(username + '@example.com');
  await page.locator('#id_password1').fill(password);
  await page.locator('#id_password2').fill(password);
  await page.getByRole('button', { name: '创建账户' }).click();
  await page.waitForURL(base + '/');
  await page.getByLabel('搜索商品', { exact: true }).fill('笔记本');
  await page.getByRole('button', { name: '查询', exact: true }).click();
  await page.screenshot({ path: path.join(output, '03-search.png'), fullPage: true });
  await page.getByRole('heading', { name: '点阵学习笔记本' }).getByRole('link').click();
  await page.screenshot({ path: path.join(output, '04-detail.png'), fullPage: true });
  await page.getByLabel('数量', { exact: true }).fill('2');
  await page.getByRole('button', { name: '加入购物车' }).click();
  await page.waitForURL(base + '/cart/');
  if (!(await page.locator('.summary').innerText()).includes('37.80')) throw new Error('Incorrect cart total');
  await page.screenshot({ path: path.join(output, '05-cart.png'), fullPage: true });
  await page.getByLabel('数量', { exact: true }).fill('3');
  await page.getByRole('button', { name: '更新', exact: true }).click();
  if (!(await page.locator('.summary').innerText()).includes('56.70')) throw new Error('Incorrect updated total');
  await page.getByRole('button', { name: '移除', exact: true }).click();
  await page.getByRole('heading', { name: '购物车还是空的' }).waitFor();
  await page.getByRole('button', { name: '注销', exact: true }).click();
  await page.getByRole('link', { name: '登录', exact: true }).click();
  await page.screenshot({ path: path.join(output, '06-login.png'), fullPage: true });
  await page.locator('#id_username').fill(username);
  await page.locator('#id_password').fill(password);
  await page.getByRole('button', { name: '登录', exact: true }).click();
  await page.waitForURL(base + '/');
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({ path: path.join(output, '07-mobile.png'), fullPage: true });
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth);
  if (overflow) throw new Error('Mobile page overflows horizontally');
  if (errors.length) throw new Error(errors.join('\n'));
  await browser.close();
  console.log('Browser smoke passed: register, search, detail, add/update/remove cart, logout, login, mobile. 7 screenshots saved.');
})().catch(error => { console.error(error); process.exit(1); });
