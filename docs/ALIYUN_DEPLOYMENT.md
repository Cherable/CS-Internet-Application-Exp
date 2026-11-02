# orangible 阿里云部署、备份与排错手册

核对日期：2026-11-02。本文为待执行手册，本轮没有 ECS、域名或证书，未声称已上线。ECS 提供常驻计算与公网入口；MySQL 持久保存用户、商品、购物车和订单；Gunicorn 运行 Django；Nginx 提供静态文件和 HTTPS。MySQL 容器不向宿主机发布端口，应用也没有公网直连端口。

## 1. 准备云资源

建议 Ubuntu 24.04 x86_64，2 核 4GB、40GB 以上磁盘，公网 IP 和域名。规格是作业容量建议，不是免费承诺。安全组只公开 TCP 80/443，22 限管理员公网 IP，3306/8000 不开放。设置域名 A 记录指向 ECS 公网 IP；中国内地建站须按实际适用备案流程处理。试用实例不能直接满足国内 ICP 备案资源条件，先确认再选择地域。[阿里云安全组官方说明](https://help.aliyun.com/zh/ecs/user-guide/start-using-security-groups)、[试用说明](https://help.aliyun.com/zh/ecs/user-guide/ecs-free-trial)。

仍建议 12 月 1–3 日申请试用并部署，暂定 12 月 8 日提交、维护至 2027 年 3 月 8 日。当前个人试用为总额度 300 元、有效期三个月，并非三个月持续免费；实际账单、权益和到期日以控制台为准，准备续费或迁移预算。不要为了本阶段截图提前开通。

## 2. 安装与取代码

以下命令在 ECS Ubuntu SSH 终端执行（不是 Windows）。使用 sudo 管理 Docker；不要用 Django runserver 对外部署。

```bash
sudo apt-get update
sudo apt-get install -y docker.io docker-compose-v2 git openssl
sudo systemctl enable --now docker
git clone https://github.com/Cherable/CS-Internet-Application-Exp.git orangible
cd orangible
cp .env.production.example .env.production
chmod 600 .env.production
openssl rand -hex 32
nano .env.production
```

用随机值替换 DJANGO_SECRET_KEY、MYSQL_PASSWORD 和 MYSQL_ROOT_PASSWORD 三个占位值，后两者不同。填写真实域名到 ALLOWED_HOSTS 和 CSRF_TRUSTED_ORIGINS（后者带 https://）。密码建议采用独立的十六进制随机串，避免 Compose 的美元符号插值。不要把配置提交到 GitHub。当前 DEBUG=false，演示付款开关明确为 true，课程展示会标记未真实扣款；实际商用必须关闭并接入经验证的支付平台。

初次使用 NGINX_CONFIG=http.conf、DJANGO_HTTPS=false。HTTP 仅用于连通检查，生产安全 Cookie 无法在普通 HTTP 上维持登录，应完成 HTTPS 后再注册登录。

## 3. 初始化 MySQL 与应用

```bash
sudo docker compose --env-file .env.production -f compose.production.yaml config --quiet
sudo docker compose --env-file .env.production -f compose.production.yaml build
sudo docker compose --env-file .env.production -f compose.production.yaml up -d db
sudo docker compose --env-file .env.production -f compose.production.yaml run --rm web python manage.py migrate
sudo docker compose --env-file .env.production -f compose.production.yaml run --rm web python manage.py seed_demo
sudo docker compose --env-file .env.production -f compose.production.yaml run --rm web python manage.py collectstatic --noinput
sudo docker compose --env-file .env.production -f compose.production.yaml run --rm web python manage.py createsuperuser
sudo docker compose --env-file .env.production -f compose.production.yaml up -d
sudo docker compose --env-file .env.production -f compose.production.yaml ps
curl -I http://你的域名/
```

迁移从代码创建表及约束，MySQL 数据保存在命名卷 mysql_data；重建应用镜像不丢失该卷。不要执行 down -v。初始化环境变量只在空数据库卷首次创建时生效，后来改 .env 密码不会自动更新已有 MySQL 用户。迁移需要表结构权限，生产可进一步分离迁移账号与运行账号。SQLite 预览数据库不会自动迁移到 MySQL。

## 4. Nginx 与 HTTPS

在阿里云数字证书管理控制台申请并完成域名所有权验证，下载 Nginx 格式证书。将证书链和私钥安全复制到 deploy/certs/fullchain.pem、privkey.pem；私钥不要公开，不放聊天或仓库。参考[阿里云官方部署 SSL 指南](https://help.aliyun.com/zh/ecs/user-guide/ssl)。

```bash
mkdir -p deploy/certs
# 将获签发的证书和私钥复制到上述文件名
chmod 700 deploy/certs
chmod 600 deploy/certs/privkey.pem
nano .env.production
# NGINX_CONFIG=https.conf
# DJANGO_HTTPS=true
sudo docker compose --env-file .env.production -f compose.production.yaml up -d --force-recreate web nginx
sudo docker compose --env-file .env.production -f compose.production.yaml exec nginx nginx -t
curl -I https://你的域名/
sudo docker compose --env-file .env.production -f compose.production.yaml exec web python manage.py check --deploy
```

nginx -t 失败先查看日志并修正文件，必要时切回 http.conf 排查。正确配置时 HTTP 重定向 HTTPS。Nginx 覆写代理协议头，Django 信任该头；不能额外向公网发布 web:8000。证书续期后覆盖对应文件，执行 nginx -t，再 exec nginx nginx -s reload。记录证书到期时间并提前续期，不假定测试证书有效期覆盖整个考核期。

## 5. 邮件处理

SMTP 主机、用户名和授权码只在 .env.production 设置。默认 console 只是预览。供应商支持 465 时启用 SSL=true、TLS=false；587 则按供应商文档使用 STARTTLS。ECS 默认限制 25 端口，参见[官方网络 FAQ](https://help.aliyun.com/zh/ecs/network-connectivity-faqs)。

```bash
sudo docker compose --env-file .env.production -f compose.production.yaml exec -T web python manage.py send_shipment_emails
```

可在 root 的 crontab -e 添加以下任务，替换为实际项目绝对路径；日志文件需建立轮转规则。

```cron
* * * * * cd /opt/orangible && /usr/bin/docker compose --env-file .env.production -f compose.production.yaml exec -T web python manage.py send_shipment_emails >> /var/log/orangible-mail.log 2>&1
```

发货与通知队列先事务提交，处理失败下次重试。SMTP 接受不等于收件箱已到达，外部邮件发送无法保证崩溃场景严格仅一次。实际验证须创建新订单并检查收件箱、垃圾箱和后台状态。

## 6. 备份、恢复和升级

```bash
sudo sh deploy/backup.sh
# 将 backups/*.sql.gz 加密后复制到独立机器/存储；只在本磁盘保存不算异地备份。
```

可每日在 root cron 中运行 cd /opt/orangible && sh deploy/backup.sh。备份含个人资料，应限制权限，按课程需要制定保留天数；本脚本不自动删除备份。恢复必须先在独立测试实例演练，恢复会修改数据库。正式恢复先停止应用写入并另做当前备份，再执行：

```bash
sudo docker compose --env-file .env.production -f compose.production.yaml stop web
# 替换成实际备份文件；保留现有 db，不执行 down -v。
gunzip -c backups/实际备份.sql.gz | sudo docker compose --env-file .env.production -f compose.production.yaml exec -T db sh -c 'MYSQL_PWD="$MYSQL_PASSWORD" mysql -u"$MYSQL_USER" "$MYSQL_DATABASE"'
sudo docker compose --env-file .env.production -f compose.production.yaml up -d web
```

升级先备份、记录 git rev-parse HEAD，再 git pull --ff-only、build、run --rm web python manage.py migrate、collectstatic，最后 up -d。回滚代码前确认迁移是否可逆，必要时在停写状态恢复匹配备份，不能只切旧代码承诺无损回滚。

## 7. 排错与验收

```bash
sudo docker compose --env-file .env.production -f compose.production.yaml logs --tail=100 web db nginx
sudo docker compose --env-file .env.production -f compose.production.yaml exec web python manage.py showmigrations
sudo docker compose --env-file .env.production -f compose.production.yaml exec nginx nginx -t
```

502：检查 web 是否启动、数据库健康、Gunicorn 日志。400：检查实际 Host 是否在 ALLOWED_HOSTS。403 CSRF：检查 https 域名、CSRF_TRUSTED_ORIGINS 和代理协议。登录后立即丢失：确认 HTTPS 与安全 Cookie。静态 404：重新 collectstatic，确认 static_data 挂载。数据库拒绝连接：检查 MYSQL_HOST=db、账号密码及旧卷中的真实用户密码，切勿删卷试错。公网超时：核对公网 IP、DNS、安全组、系统防火墙及容器端口。

最终须从校园网和手机流量各跑一遍注册→搜索→购物车→下单→演示付款→管理员发货→订单历史；补录真实网站地址、低权限测试账号及凭据交付方式、页面截图、SMTP 收件证据、HTTPS 锁标志、安全组和备份恢复结果。管理员密码不能放公开报告。每周检查可用性、余额和证书，维持提交后三个月访问。
