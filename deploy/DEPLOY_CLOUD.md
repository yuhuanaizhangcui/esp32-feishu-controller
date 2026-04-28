# ☁️ 云服务器部署指南

本文档介绍如何将 ESP32 飞书控制器部署到云服务器。

---

## 📋 准备工作

### 1. 云服务器要求

| 项目 | 推荐配置 | 说明 |
|------|---------|------|
| 操作系统 | Ubuntu 20.04/22.04 LTS | 其他 Linux 也可 |
| 内存 | ≥ 1GB | 低于 1GB 可能不足 |
| 硬盘 | ≥ 20GB | Python + 依赖约 500MB |
| 带宽 | 1Mbps+ | 够用，建议 5Mbps |
| IP | 公网 IP | 必需，飞书需要回调 |

**推荐云服务商：**
- 阿里云 ECS（新人优惠 ~30元/月）
- 腾讯云 CVM（轻量应用服务器 ~25元/月）
- 华为云 ECS（性价比高）

### 2. 准备材料

- [ ] 云服务器（公网 IP 已分配）
- [ ] 域名（可选，但推荐）
- [ ] 飞书应用 App ID 和 App Secret
- [ ] HiveMQ Cloud 账户和凭证

---

## 🚀 部署步骤

### 第一步：连接服务器

```bash
# 使用 SSH 连接
ssh root@你的服务器IP

# 如果使用密钥登录
ssh -i ~/.ssh/your_key.pem root@你的服务器IP
```

### 第二步：初始化服务器

上传并运行初始化脚本：

```bash
# 方法一：通过 scp 上传
scp -r ./deploy root@你的服务器IP:/tmp/

# 方法二：在服务器上直接下载
# 先把代码放到 GitHub，然后：
git clone https://github.com/your-repo/esp32-feishu.git
cd esp32-feishu/deploy
```

运行初始化脚本：

```bash
chmod +x init_server.sh
sudo ./init_server.sh
```

脚本会自动安装：
- Python 3.10
- Nginx
- 防火墙 (ufw)
- Fail2ban (防暴力破解)
- 应用用户和目录

### 第三步：上传代码

```bash
# 方法一：Git 拉取（推荐）
cd /opt/esp32-controller
sudo -u esp32ctrl git clone https://github.com/your-repo/esp32-feishu.git .

# 方法二：SCP 上传
scp -r ./feishu-app/* root@你的服务器IP:/opt/esp32-controller/
```

### 第四步：部署应用

```bash
cd /opt/esp32-controller/deploy
chmod +x deploy_app.sh
sudo ./deploy_app.sh
```

脚本会自动：
- 安装 Python 依赖
- 创建 .env 配置文件
- 配置 Systemd 服务
- 启动服务

### 第五步：配置环境变量

```bash
sudo nano /opt/esp32-controller/.env
```

填入实际配置：

```env
# 飞书应用配置
FEISHU_APP_ID=cli_xxxxxxxxxxxxxxxxxxxxxxxx
FEISHU_APP_SECRET=your-app-secret-here
FEISHU_VERIFY_TOKEN=your-verify-token

# MQTT 配置
MQTT_BROKER_HOST=broker.hivemq.cloud
MQTT_BROKER_PORT=8883
MQTT_USERNAME=your-mqtt-username
MQTT_PASSWORD=your-mqtt-password

# 服务配置
SERVER_HOST=127.0.0.1
SERVER_PORT=5000
SERVER_DEBUG=false
```

保存后重启服务：

```bash
sudo systemctl restart esp32-backend
```

### 第六步：配置 Nginx + SSL（推荐）

#### 6.1 安装 Certbot（Let's Encrypt 免费 SSL）

```bash
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d your-domain.com
```

#### 6.2 修改 Nginx 配置

```bash
sudo nano /etc/nginx/sites-available/esp32-backend
```

修改 `server_name` 为你的域名：

```
server_name your-domain.com;  # 改为你的域名
```

#### 6.3 重启 Nginx

```bash
sudo nginx -t
sudo systemctl reload nginx
```

### 第七步：配置防火墙

```bash
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp    # HTTPS
sudo ufw status
```

---

## 🔧 配置飞书开放平台

### 1. 设置事件订阅

在飞书开放平台 → 你的应用 → **事件与回调** → **事件订阅**：

```
请求地址 URL: https://your-domain.com/feishu/webhook
```

### 2. 添加事件

订阅以下事件：
- `im.message.receive_v1` - 接收消息

### 3. 配置权限

在 **权限管理** 中添加：
- `im:message` - 发送消息
- `im:message:send_as_bot` - 以机器人身份发送

---

## ✅ 验证部署

### 检查服务状态

```bash
# 查看服务状态
sudo systemctl status esp32-backend

# 查看实时日志
sudo journalctl -u esp32-backend -f

# 查看应用日志
sudo tail -f /opt/esp32-controller/logs/stdout.log
```

### 测试 API

```bash
# 健康检查
curl https://your-domain.com/health

# 发送测试指令
curl -X POST https://your-domain.com/api/control \
  -H "Content-Type: application/json" \
  -d '{"command": "led_on"}'
```

### 测试飞书

1. 在飞书中向机器人发送 `控制`
2. 应该收到带按钮的卡片
3. 点击按钮，查看服务器日志确认收到

---

## 📊 常用运维命令

```bash
# 查看服务状态
sudo systemctl status esp32-backend

# 重启服务
sudo systemctl restart esp32-backend

# 停止服务
sudo systemctl stop esp32-backend

# 查看日志
sudo journalctl -u esp32-backend -n 100  # 最近100行
sudo journalctl -u esp32-backend -f      # 实时日志

# 查看 Nginx 状态
sudo systemctl status nginx

# 重载 Nginx 配置
sudo nginx -t && sudo systemctl reload nginx

# 重启所有服务
sudo systemctl restart esp32-backend nginx
```

---

## 🔒 安全加固（可选）

### 1. 配置飞书请求签名验证

编辑 `server.py`，启用签名验证：

```python
def verify_request_signature(request) -> bool:
    # 实现完整的飞书签名验证
    # 参考: https://open.feishu.cn/document/ukTMukTMukTM/ucDOzEjL3IzL4Q
    ...
```

### 2. 限制 IP 访问（仅允许飞书服务器）

```bash
# 查看飞书服务器 IP 段
# 飞书 API 服务器 IP 可以加入白名单
sudo ufw allow from 103.252.27.0/24 to any port 5000
```

### 3. 配置自动备份

```bash
# 创建备份脚本
sudo nano /opt/esp32-controller/backup.sh
```

```bash
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR=/opt/esp32-controller/backups
cd /opt/esp32-controller
tar -czf $BACKUP_DIR/backup_$DATE.tar.gz .env logs/
find $BACKUP_DIR -name "backup_*.tar.gz" -mtime +7 -delete
```

```bash
# 添加定时任务
sudo crontab -e
# 每天凌晨3点备份
0 3 * * * /opt/esp32-controller/backup.sh
```

---

## 🆘 故障排查

### 服务启动失败

```bash
# 查看详细错误
sudo journalctl -u esp32-backend -n 50

# 常见问题：
# 1. 端口被占用
sudo lsof -i :5000

# 2. 权限问题
sudo chown -R esp32ctrl:esp32ctrl /opt/esp32-controller

# 3. Python 模块缺失
sudo -u esp32ctrl /opt/esp32-controller/venv/bin/pip install -r requirements.txt
```

### Nginx 502 错误

```bash
# 检查后端是否运行
curl http://127.0.0.1:5000/health

# 检查 Nginx 日志
sudo tail -f /var/log/nginx/esp32_error.log
```

### SSL 证书过期

```bash
# 续期 Let's Encrypt 证书
sudo certbot renew

# 自动续期（默认已配置）
sudo certbot renew --dry-run
```

---

## 📞 技术支持

如有问题，请提供：
1. `sudo journalctl -u esp32-backend -n 50` 的输出
2. `sudo systemctl status esp32-backend` 的输出
3. 错误截图

---

**祝你部署顺利！🎉**
