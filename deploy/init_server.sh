#!/bin/bash
# ============================================
# ESP32 飞书控制器 - 云服务器初始化脚本
# 适用: Ubuntu 20.04 / 22.04 LTS
# 用途: 初始化服务器环境（Python、Nginx、防火墙等）
# ============================================

set -e  # 遇到错误立即退出

echo "============================================"
echo "🚀 ESP32 飞书控制器 - 服务器初始化"
echo "============================================"
echo ""

# 检查是否为 root 用户
if [ "$EUID" -ne 0 ]; then 
    echo "❌ 请使用 root 用户或 sudo 运行此脚本"
    exit 1
fi

# 配置变量
APP_USER="esp32ctrl"
APP_DIR="/opt/esp32-controller"
PYTHON_VERSION="3.10"

echo "📋 配置信息:"
echo "  - 应用用户: $APP_USER"
echo "  - 安装目录: $APP_DIR"
echo "  - Python 版本: $PYTHON_VERSION"
echo ""

# ===== 1. 更新系统 =====
echo "1️⃣ 更新系统软件包..."
apt-get update -y
apt-get upgrade -y
echo "✅ 系统更新完成"
echo ""

# ===== 2. 安装基础软件 =====
echo "2️⃣ 安装基础软件..."
apt-get install -y \
    software-properties-common \
    curl \
    wget \
    git \
    unzip \
    vim \
    htop \
    tree \
    ufw \
    fail2ban
echo "✅ 基础软件安装完成"
echo ""

# ===== 3. 安装 Python =====
echo "3️⃣ 安装 Python $PYTHON_VERSION..."
add-apt-repository -y ppa:deadsnakes/ppa
apt-get update -y
apt-get install -y \
    python${PYTHON_VERSION} \
    python${PYTHON_VERSION}-venv \
    python${PYTHON_VERSION}-dev \
    python3-pip
echo "✅ Python 安装完成"
python${PYTHON_VERSION} --version
echo ""

# ===== 4. 创建应用用户 =====
echo "4️⃣ 创建应用用户: $APP_USER..."
if id "$APP_USER" &>/dev/null; then
    echo "  用户已存在，跳过创建"
else
    useradd -m -s /bin/bash $APP_USER
    echo "✅ 用户创建成功"
fi
echo ""

# ===== 5. 创建应用目录 =====
echo "5️⃣ 创建应用目录..."
mkdir -p $APP_DIR
mkdir -p $APP_DIR/logs
mkdir -p $APP_DIR/backups
chown -R $APP_USER:$APP_USER $APP_DIR
echo "✅ 目录创建完成: $APP_DIR"
echo ""

# ===== 6. 安装 Nginx =====
echo "6️⃣ 安装 Nginx..."
apt-get install -y nginx
systemctl enable nginx
systemctl start nginx
echo "✅ Nginx 安装完成"
echo ""

# ===== 7. 配置防火墙 =====
echo "7️⃣ 配置防火墙..."
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
echo "y" | ufw enable
echo "✅ 防火墙配置完成"
echo ""

# ===== 8. 配置 Python 虚拟环境 =====
echo "8️⃣ 创建 Python 虚拟环境..."
cd $APP_DIR
sudo -u $APP_USER python${PYTHON_VERSION} -m venv venv
echo "✅ 虚拟环境创建完成: $APP_DIR/venv"
echo ""

# ===== 9. 安装 Fail2ban =====
echo "9️⃣ 配置 Fail2ban（防暴力破解）..."
cat > /etc/fail2ban/jail.local << 'EOF'
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5

[sshd]
enabled = true
EOF
systemctl enable fail2ban
systemctl restart fail2ban
echo "✅ Fail2ban 配置完成"
echo ""

# ===== 10. 创建部署密钥目录 =====
echo "🔟 创建部署密钥目录..."
mkdir -p /home/$APP_USER/.ssh
chmod 700 /home/$APP_USER/.ssh
touch /home/$APP_USER/.ssh/authorized_keys
chmod 600 /home/$APP_USER/.ssh/authorized_keys
chown -R $APP_USER:$APP_USER /home/$APP_USER/.ssh
echo "✅ SSH 密钥目录创建完成"
echo ""

# ===== 完成 =====
echo "============================================"
echo "✅ 服务器初始化完成！"
echo "============================================"
echo ""
echo "📋 下一步操作:"
echo "  1. 上传应用代码到 $APP_DIR"
echo "  2. 运行部署脚本: ./deploy_app.sh"
echo "  3. 配置 Nginx 反向代理"
echo "  4. 申请 SSL 证书（可选）"
echo ""
echo "🔗 相关目录:"
echo "  - 应用目录: $APP_DIR"
echo "  - 日志目录: $APP_DIR/logs"
echo "  - Nginx 配置: /etc/nginx/sites-available/"
echo ""
echo "🚀 快速测试 Python:"
echo "  sudo -u $APP_USER $APP_DIR/venv/bin/python --version"
echo ""
