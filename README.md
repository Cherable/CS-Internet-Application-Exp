# orangible · 热带水果购物网站

Internet Application 课程实验，采用 Django、MySQL 和服务端模板。界面为雨林纪录片主题，包含全屏序章、虚化雨林背景、紧凑水果卡片和商品故事。

## 功能

- 注册、登录、注销，水果检索与商品详情。
- 应季精选、即食/临期优惠、全部水果；默认按近30日销量排序。
- 购物车、事务下单、库存预留、取消、演示付款和订单历史。
- 后台商品、发货邮件任务及销售统计管理。
- 持久化每日供需模拟、人工补录与订单销量合并，页面同步排名；折扣每日更新，成交价格保存快照。

## 文档与验证

- [实验报告](docs/最终实验报告.md)
- [系统设计](docs/DESIGN.md)
- [部署设计](docs/ALIYUN_DEPLOYMENT.md)
- [当前界面](docs/screenshots/)
- [验证记录](docs/validation/)
- [摄影来源](docs/IMAGE_CREDITS.md)

MySQL 8.0.45 的46项业务测试通过；SQLite 43项通过、3项MySQL并发用例跳过。1042×871、1440×1000、390×844布局检查通过，验证完整图片、5:3卡片、首屏购买信息和无横向溢出。

## 技术组成

config/ 为应用配置，shop/ 为业务、模型和迁移，templates/ 与 static/ 为界面。生产编排使用 compose.production.yaml，配合 Dockerfile、deploy/ 与 GitHub Actions。

水果示例目录由 seed_fruits 管理，每日行情由 fruit-clock 服务维护。历史数据库迁移属于当前应用的必要组成。

## 实现范围

支付为演示，未真实扣款；邮件默认预览。销量、季节与供需含模拟设定，产区故事不构成实际供货证明。云服务器、容器运行和真实邮件收件尚待验收。

原创代码采用 MIT 许可证。
