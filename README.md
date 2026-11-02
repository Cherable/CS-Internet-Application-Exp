# orangible 在线购物网站

Internet Application 课程实验，采用 Django、MySQL 与服务端模板实现校园用品购物系统。界面采用橙色与奶油白配色。

## 系统功能

- 顾客注册、登录、注销，商品浏览、关键词查询与分类筛选。
- 购物车、事务化下单、库存预留、订单取消与订单历史。
- 明确标注的演示付款、发货通知任务及失败重试。
- 后台商品管理、订单发货、销售数量与金额统计。

## 技术实现

Python 3.12、Django 5.2、MySQL，Django ORM 管理数据访问与迁移。订单采用价格快照、数据库事务、行锁、条件库存更新和唯一结算令牌。权限控制限定顾客访问自己的订单，销售管理采用 staff 与模型权限。

生产部署结构由 Gunicorn、Nginx 和 MySQL 组成，配置见 Dockerfile、compose.production.yaml 与 deploy/。GitHub Actions 包含 SQLite/MySQL 测试及容器构建检查。

## 实验文档

[完整实验报告](docs/最终实验报告.md) · [部署设计](docs/ALIYUN_DEPLOYMENT.md)

功能测试日志与运行截图位于 docs/stages/。MySQL 8.0.45 的 39 项测试全部通过；最近一次 SQLite 回归通过 36 项，跳过 3 项依赖 MySQL 行锁的用例。浏览器测试覆盖主要业务、后台商品维护及移动端布局。

## 实现范围

付款为课程演示，未真实扣款；邮件默认在本地预览，未验证真实投递。容器运行、云端部署及校园网访问尚未验收。

项目原创代码采用 MIT 许可证。
