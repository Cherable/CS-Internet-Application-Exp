# 应用部署设计

部署目标为阿里云 ECS Linux 实例。ECS 提供计算与公网访问环境，Gunicorn 运行 Django 应用，MySQL 保存业务数据，Nginx 提供反向代理、静态文件和 HTTPS。

## 服务结构

compose.production.yaml 定义 db、web、nginx 三个服务。MySQL 使用 8.4 镜像和持久化数据卷；应用使用 Python 3.12 镜像构建；Nginx 使用只读静态文件卷与证书挂载。宿主机公开 80、443 端口，应用和数据库通过容器内部网络通信。

## 配置与安全

生产配置包含 DEBUG 关闭、主机名校验、CSRF 可信来源、安全 Cookie、HTTPS 重定向与代理协议识别。证书链和私钥分别挂载于 Nginx 的 fullchain.pem 和 privkey.pem。密钥、数据库文件和运行缓存不纳入源码。

## 数据与维护

数据库表结构由 Django 迁移管理，MySQL 命名卷负责持久化。备份脚本 deploy/backup.sh 采用一致性逻辑导出、限制文件权限和压缩保存。发货邮件由管理命令读取任务队列，记录处理状态与重试次数。

## 验证范围

当前完成部署配置编写和本地应用测试，尚未开展 Docker/MySQL 8.4 运行、云服务器发布、证书、校园网及备份恢复验证。

## 参考文献

- [阿里云 ECS 安全组](https://help.aliyun.com/zh/ecs/user-guide/start-using-security-groups)
- [阿里云 SSL 部署方案](https://help.aliyun.com/zh/ecs/user-guide/ssl)
