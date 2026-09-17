# 在线购物网站（框架版）

这是一个可直接导入 GitHub 的前后端分离项目骨架。当前版本只规定系统边界、核心数据结构、公共变量和接口位置，不包含注册、支付、发货、邮件等完整业务流程。

## 技术栈

- 后端：Java 17、Spring Boot、Spring Web、Spring Data JPA、Spring Security、Validation、Flyway
- 前端：Vue 3、TypeScript、Vite、Vue Router、Pinia、Axios
- 数据库：MySQL 8
- 部署目标：阿里云 ECS/RDS，可按需要增加 Nginx、HTTPS 和进程管理

## 目录结构

```text
online-shopping-platform/
├── backend/                 Spring Boot 后端
│   ├── src/main/java/       Java 源码
│   └── src/main/resources/  配置与数据库迁移
├── frontend/                Vue 3 前端
├── docs/                    需求、数据字典、接口约定、部署说明
├── .env.example             环境变量模板
└── compose.yaml             本地 MySQL
```

## 已固定的基础约定

- 用户角色：`CUSTOMER`、`SALES_MANAGER`、`ADMIN`
- 商品状态：`DRAFT`、`ACTIVE`、`INACTIVE`、`DELETED`
- 订单状态：`PENDING_PAYMENT`、`PAID`、`PROCESSING`、`SHIPPED`、`COMPLETED`、`CANCELLED`、`REFUNDED`
- 支付状态：`PENDING`、`SUCCESS`、`FAILED`、`CLOSED`、`REFUNDED`
- 邮件任务状态：`PENDING`、`SENT`、`FAILED`
- 金额统一使用 `BigDecimal` / MySQL `DECIMAL(12,2)`
- 时间统一由后端保存，接口传输使用 ISO 8601 格式
- 所有接口预留在 `/api/v1` 下
- 密码、数据库口令、JWT 密钥和邮件凭据只通过环境变量配置

## 本地初始化

1. 复制 `.env.example` 为 `.env` 并修改密码。
2. 启动 MySQL：`docker compose up -d mysql`。
3. 后端：进入 `backend`，执行 `mvn spring-boot:run`。
4. 前端：进入 `frontend`，执行 `npm install` 和 `npm run dev`。

当前安全配置只放行健康检查和商品查询占位接口，其余接口要求认证。认证流程将在下一阶段实现。

## 导入 GitHub

解压后，在项目根目录执行：

```bash
git init
git add .
git commit -m "chore: initialize online shopping platform scaffold"
git branch -M main
git remote add origin <你的 GitHub 仓库地址>
git push -u origin main
```

也可以在 GitHub 新建空仓库后，通过网页上传解压后的全部文件。

## 下一阶段建议

依次实现：身份认证与权限、商品目录、购物车、订单与库存、模拟/沙箱支付、发货与邮件、销售统计、阿里云部署。
