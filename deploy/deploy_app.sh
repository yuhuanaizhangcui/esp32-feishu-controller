#!/bin/bash
# ============================================
# ESP32 飞书控制器 - 应用部署脚本
# 用途: 拉取代码、安装依赖、配置服务
# ============================================

set -e

# 配置变量
APP_USER="esp32ctrl"
APP_DIR="/opt/esp32-controller"
SERVICE_NAME="esp32-backend"
GIT_REPO="${GIT_REPO:-}"  # 可通过环境变量指定，如: https://github.com/xxx/esp32-feishu

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

echo "============================================"
echo "🚀 ESP32 飞书控制器 - 应用部署"
echo "============================================"
echo ""

# ===== 1. 检查环境 =====
echo "1️⃣ 检查运行环境..."

# 检查 root（部署需要 root 权限）
if [ "$EUID" -ne 0 ]; then
    log_error "请使用 root 用户或 sudo 运行"
    exit 1
fi

# 检查用户是否存在
if ! id "$APP_USER" &>/dev/null; then
    log_error "用户 $APP_USER 不存在，请先运行 init_server.sh"
    exit 1
fi

# 检查目录是否存在
if [ ! -d "$APP_DIR" ]; then
    mkdir -p $APP_DIR
    chown $APP_USER:$APP_USER $APP_DIR
    log_warn "应用目录不存在，已创建"
fi

log_info "环境检查通过"
echo ""

# ===== 2. 拉取代码 =====
echo "2️⃣ 拉取应用代码..."

if [ -n "$GIT_REPO" ]; then
    # 从 Git 拉取
    cd $APP_DIR
    if [ -d ".git" ]; then
        log_info "更新现有代码..."
        sudo -u $APP_USER git pull
    else
        log_info "克隆新代码..."
        sudo -u $APP_USER git clone $GIT_REPO .
    fi
else
    log_warn "未指定 GIT_REPO，跳过代码拉取"
    log_info "请手动上传代码到 $APP_DIR"
fi

echo ""

# ===== 3. 安装 Python 依赖 =====
echo "3️⃣ 安装 Python 依赖..."

if [ -f "$APP_DIR/requirements.txt" ]; then
    cd $APP_DIR
    sudo -u $APP_USER $APP_DIR/venv/bin/pip install --upgrade pip
    sudo -u $APP_USER $APP_DIR/venv/bin/pip install -r requirements.txt
    log_info "依赖安装完成"
else
    log_error "未找到 requirements.txt"
fi

echo ""

# ===== 4. 配置环境变量 =====
echo "4️⃣ 配置环境变量..."

# 创建 .env 文件
cat > $APP_DIR/.env << 'EOF'
# 飞书应用配置
FEISHU_APP_ID=your-feishu-app-id
FEISHU_APP_SECRET=your-feishu-app-secret
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
EOF

chown $APP_USER:$APP_USER $APP_DIR/.env
chmod 600 $APP_DIR/.env

log_info "环境配置文件已创建: $APP_DIR/.env"
log_warn "请编辑 $APP_DIR/.env 填入实际配置！"
echo ""

# ===== 5. 复制服务文件 =====
echo "5️⃣ 配置 Systemd 服务..."

cp $APP_DIR/deploy/esp32-backend.service /etc/systemd/system/ 2>/dev/null || true

# 如果服务文件不存在，创建它
if [ ! -f "/etc/systemd/system/$SERVICE_NAME.service" ]; then
    cat > /etc/systemd/system/$SERVICE_NAME.service << EOF
[Unit]
Description=ESP32 Feishu Controller Backend
After=network.target

[Service]
Type=simple
User=$APP_USER
WorkingDirectory=$APP_DIR
Environment="PATH=$APP_DIR/venv/bin"
EnvironmentFile=$APP_DIR/.env
ExecStart=$APP_DIR/venv/bin/python server.py
Restart=always
RestartSec=5
StandardOutput=append:$APP_DIR/logs/stdout.log
StandardError=append:$APP_DIR/logs/stderr.log

# 安全加固
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=$APP_DIR

[Install]
WantedBy=multi-user.target
EOF
    log_info "服务文件已创建"
fi

systemctl daemon-reload
log_info "Systemd 配置已刷新"
echo ""

# ===== 6. 启动服务 =====
echo "6️⃣ 启动服务..."

systemctl enable $SERVICE_NAME
systemctl restart $SERVICE_NAME

sleep 2

if systemctl is-active --quiet $SERVICE_NAME; then
    log_info "✅ 服务启动成功！"
else
    log_error "❌ 服务启动失败，请检查日志: journalctl -u $SERVICE_NAME -n 50"
fi

echo ""

# ===== 7. 配置 Nginx（可选）=====
echo "7️⃣ 配置 Nginx 反向代理（可选）..."

if [ -f "$APP_DIR/deploy/nginx_esp32.conf" ]; then
    cp $APP_DIR/deploy/nginx_esp32.conf /etc/nginx/sites-available/$SERVICE_NAME
    ln -sf /etc/nginx/sites-available/$SERVICE_NAME /etc/nginx/sites-enabled/
    
    # 测试配置
    if nginx -t; then
        systemctl reload nginx
        log_info "Nginx 配置已生效"
    else
        log_error "Nginx 配置有误，请检查"
    fi
else
    log_warn "未找到 Nginx 配置文件，跳过"
fi

echo ""

# ===== 完成 =====
echo "============================================"
echo "✅ 部署完成！"
echo "============================================"
echo ""
echo "📋 常用命令:"
echo "  查看状态:  systemctl status $SERVICE_NAME"
echo "  查看日志:  journalctl -u $SERVICE_NAME -f"
echo "  重启服务:  systemctl restart $SERVICE_NAME"
echo "  停止服务:  systemctl stop $SERVICE_NAME"
echo ""
echo "🌐 访问地址:"
echo "  - 直接访问: http://localhost:5000"
echo "  - Nginx代理: http://your-domain.com"
echo "  - 健康检查: http://your-domain.com/health"
echo ""
echo "⚠️  重要提醒:"
echo "  1. 编辑 $APP_DIR/.env 填入实际配置"
echo "  2. 配置防火墙: ufw allow 80/tcp && ufw allow 443/tcp"
echo "  3. 申请 SSL 证书（推荐使用 Let's Encrypt）"
echo ""
