# orangible · 在线购物网站课程实验

2026-10-27 品牌更新：网站名称统一为 **orangible**，页面采用橙色与奶油白配色。此次界面调整将在第二阶段一并上传；第一阶段文档与截图保留当时的实际效果。

使用 Django + MySQL 实现校园用品购物网站。当前版本完成第一阶段：注册、登录、注销、商品列表、关键词查询、分类筛选、详情页和购物车；商品分类及商品增删改查可通过 Django Admin 操作。

> 当前尚未实现订单、付款、发货邮件和销售报表，结算按钮明确禁用。第二阶段完成业务闭环，第三阶段交付阿里云部署与最终报告。代码仓库：[Cherable/CS-Internet-Application-Exp](https://github.com/Cherable/CS-Internet-Application-Exp)，当前尚无线上网站地址。

仓库原有 Java/Vue 框架说明保存在 `docs/repository-original/README.md`，原有 `compose.yaml` 保留。本次交付的可运行应用使用下面的 Django 启动步骤；原有框架说明不能代替本应用的运行说明。

## 分阶段交付

- [第一阶段：需求、设计、基础代码、测试与截图](docs/stages/stage-01/第一阶段交付文档.md)，实际执行日期 2026-10-25。
- 第二阶段独立文件：`docs/stages/stage-02/第二阶段交付文档.md`，后续执行时生成。
- 第三阶段独立文件：`docs/stages/stage-03/第三阶段交付文档.md`，后续执行时生成。
- [进度及后续执行约定](docs/PROGRESS.md)。不以覆盖第一阶段文档的方式交付后续成果。

## 本地运行（Windows PowerShell）

需要 Python 3.12。命令在项目根目录执行。

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py seed_demo
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

打开 <http://127.0.0.1:8000/>。先注册个人账户，然后查询商品并加入购物车。示例数据命令仅创建缺失商品，不创建默认密码账户，不覆盖已有商品。

管理员请另开终端自行创建，密码不会写入代码：

```powershell
.\.venv\Scripts\python.exe manage.py createsuperuser
```

后台地址：<http://127.0.0.1:8000/admin/>。修改库存、商品价格或上架状态后，前台以数据库最新值展示。普通顾客没有后台权限。

## Linux / macOS 本地运行

```bash
python3.12 -m venv .venv
source .venv/bin/activate
# Ubuntu: mysqlclient 构建需要系统开发依赖
sudo apt-get update
sudo apt-get install -y python3-dev default-libmysqlclient-dev build-essential pkg-config
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py seed_demo
python manage.py runserver 127.0.0.1:8000
```

## 使用 MySQL

本地默认 SQLite，仅用于快速演示。部署目标为 MySQL 8.4。先在 MySQL 管理终端中执行（替换占位密码）：

```sql
CREATE DATABASE campus_shop CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'campus_shop'@'localhost' IDENTIFIED BY '替换为独立强密码';
GRANT ALL PRIVILEGES ON campus_shop.* TO 'campus_shop'@'localhost';
```

在 `.env` 中设置 `DB_ENGINE=mysql`、`MYSQL_DATABASE`、`MYSQL_USER`、`MYSQL_PASSWORD`、`MYSQL_HOST` 和 `MYSQL_PORT`，再执行 `manage.py migrate` 与 `manage.py seed_demo`。远程 MySQL 需使用实际来源主机授权；不要为方便演示把数据库端口向所有公网地址开放。SQLite 与 MySQL 是两个独立数据库，切换配置不会自动搬运数据。

## 验证

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe manage.py test --verbosity 2
```

本次 20 项 Django 测试在 SQLite 上通过。MySQL CI 工作流已提供，但本机没有 MySQL 服务，也没有远端 GitHub Actions 执行结果，因此尚不能声称 MySQL 已实测通过。MySQL 测试需要能创建 `test_campus_shop` 的专用测试账户，生产应用账户不应具有这一权限。

可选浏览器回归：安装 Node.js、`npm install --no-save --package-lock=false playwright` 和 Microsoft Edge，在开发服务器启动后运行 `node scripts/capture-stage1.cjs`。脚本会创建一个随机演示用户、操作购物车、保存 7 张本地截图；不生成管理员或固定密码。

## GitHub 提交

项目提供 README、锁定版本的依赖、迁移、环境变量样例、忽略规则、MIT 许可证和 SQLite/MySQL 两组 CI 配置。首次手动配置 Git 时，可在根目录执行；已关联远程仓库时只需提交并推送后续修改：

```bash
git init
git add .
git status --short
git commit -m "feat: deliver stage one campus shopping website"
git branch -M main
git remote add origin https://github.com/Cherable/CS-Internet-Application-Exp.git
git push -u origin main
```

提交前确认 `.env`、数据库、虚拟环境和日志未进入暂存区。源材料 `ex.html` 的版权属于其原作者；自行确认是否应公开上传，可只把应用代码目录与报告交至课程仓库。报告中最终填写真实仓库地址与线上地址。

## 阿里云部署交付范围

第三阶段提供 ECS 上的 Docker Compose、MySQL、Nginx、HTTPS、域名和安全组配置、备份恢复及排错步骤。`runserver` 只用于本地开发，不能用于公网正式部署；本阶段没有购买云资源或发布网站。

## 目录

```text
config/                  Django 配置和入口
shop/                    模型、表单、视图、后台、测试
shop/migrations/         数据库版本迁移
templates/               中文页面模板
static/shop/             响应式 CSS（无需外部图片或 CDN）
scripts/                 可复现截图脚本
docs/stages/stage-01/    第一阶段独立报告、测试记录与截图
.github/workflows/       SQLite 与 MySQL CI
requirements.txt         已锁定 Python 依赖
```

## 参考

- [Django 认证系统](https://docs.djangoproject.com/en/5.2/topics/auth/default/)
- [Django MySQL 配置](https://docs.djangoproject.com/en/5.2/ref/databases/#mysql-notes)

原创应用代码采用 MIT 许可证，原始课程材料不包含在该授权范围内。
