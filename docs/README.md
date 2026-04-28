# ESP32 飞书控制器 - 部署说明

通过飞书远程控制 ESP32 开发板，支持 LED 灯和马达控制。

## 系统架构

```
[飞书客户端] 
    ↓ (点击卡片按钮)
[飞书开放平台] ←→ [飞书自建应用]
    ↓ (事件回调)
[Python Flask 后端] (接收飞书事件)
    ↓ (发布 MQTT 消息)
[云 MQTT Broker] (HiveMQ Cloud 免费版)
    ↓ (订阅接收)
[ESP32 开发板] (WiFi + MQTT → GPIO 控制)
```

## 目录结构

```
.
├── feishu-app/                    # 飞书后端服务
│   ├── manifest.json            # 飞书应用配置
│   ├── app_config.py            # 应用配置
│   ├── server.py                # Flask 主服务
│   ├── feishu_card.py           # 卡片构建器
│   └── requirements.txt         # Python 依赖
├── esp32-code/                   # ESP32 Arduino 代码
│   └── esp32_controller.ino     # 主程序
├── test/                        # 测试工具
│   └── mqtt_simulator.py        # MQTT 模拟器
└── docs/                        # 文档
    └── README.md                # 本文档
```

---

## 第一步：注册 HiveMQ Cloud（免费）

MQTT Broker 用于在内网 ESP32 和飞书后端之间中转消息。

### 1.1 注册账号

1. 访问 [HiveMQ Cloud](https://www.hivemq.com/cloud/)
2. 点击 "Get Started Free"
3. 使用邮箱/Google 账号注册

### 1.2 创建集群

1. 选择 **HiveMQ Cloud Free**（免费版）
2. 区域选择离你最近的（如 Asia Pacific - Singapore）
3. 等待集群创建完成（约 2-3 分钟）

### 1.3 获取连接凭据

1. 进入集群管理页面
2. 点击 **Access Management** → **Create Credentials**
3. 设置用户名和密码（记住它们，后面会用到）
4. 记录下连接地址（如 `broker.xxxxx.cluster.hivemq.cloud:8883`）

> ⚠️ 免费版限制：同时最多 100 个客户端连接，但对于个人项目足够。

---

## 第二步：创建飞书自建应用

### 2.1 创建应用

1. 访问 [飞书开放平台](https://open.feishu.cn/)
2. 登录后进入「开发者后台」
3. 点击「创建自建应用」
4. 填写应用名称（如「ESP32控制器」）和描述
5. 创建完成后，在「凭证与基础信息」中获取：
   - `App ID`（格式：`cli_xxxxxxxx`）
   - `App Secret`

### 2.2 配置应用能力

在「应用功能」中启用：

1. **机器人**：启用机器人能力
2. **消息**：启用接收消息

### 2.3 配置权限

在「权限管理」中添加：

- `im:message:send_as_bot` - 发送消息
- `im:message:read` - 读取消息
- `im:chat.member:bot` - 获取群成员

### 2.4 配置事件订阅

1. 在「事件订阅」中启用
2. 将「事件配置」中的 `Request URL` 填入你的后端地址
   - 格式：`https://你的服务器域名/feishu/webhook`
3. 订阅事件：
   - `im.message.receive_v1` - 接收消息

### 2.5 发布应用

1. 在「版本管理与发布」中创建版本
2. 填写版本号和更新说明
3. 申请发布（个人应用可自行审批）

---

## 第三步：部署后端服务

### 3.1 安装依赖

```bash
cd feishu-app
pip install -r requirements.txt
```

### 3.2 配置参数

编辑 `app_config.py` 或设置环境变量：

```bash
# 飞书配置
export FEISHU_APP_ID="cli_xxxxxxxxxxxxxxxxxxxxxxxx"
export FEISHU_APP_SECRET="your-app-secret"
export FEISHU_VERIFY_TOKEN="your-verify-token"

# MQTT 配置
export MQTT_BROKER_HOST="broker.xxxxx.cluster.hivemq.cloud"
export MQTT_BROKER_PORT="8883"
export MQTT_USERNAME="your-mqtt-username"
export MQTT_PASSWORD="your-mqtt-password"
```

### 3.3 配置公网访问

后端服务需要能被飞书访问，有以下方案：

#### 方案 A：云服务器（推荐）

在云服务器（如阿里云、腾讯云）上部署：

```bash
python server.py
```

#### 方案 B：内网穿透

使用 ngrok 将本地服务暴露到公网：

```bash
# 安装 ngrok
brew install ngrok  # macOS

# 启动内网穿透
ngrok http 5000
```

复制生成的 HTTPS 地址（如 `https://xxxxx.ngrok.io`），填入飞书事件订阅的 Request URL。

### 3.4 使用 systemd 守护进程（可选）

创建服务文件 `/etc/systemd/system/esp32-controller.service`：

```ini
[Unit]
Description=ESP32 Feishu Controller
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/feishu-app
ExecStart=/usr/bin/python3 server.py
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启用服务：

```bash
sudo systemctl daemon-reload
sudo systemctl enable esp32-controller
sudo systemctl start esp32-controller
```

---

## 第四步：配置 ESP32

### 4.1 硬件连接

```
ESP32          组件
-------        ------
GPIO 2  ────►  LED (+) ────► GND (通过 220Ω 电阻)

ESP32          L298N 马达驱动
-------        -------------
GPIO 18  ────► IN1
GPIO 19  ────► IN2
GPIO 21  ────► ENA
        ────► +12V (外部电源)
        ────► GND (共地)
```

> ⚠️ 马达需要外部电源（不要直接从 ESP32 取电）

### 4.2 安装 Arduino ESP32 支持

1. 在 Arduino IDE 中打开「偏好设置」
2. 在「附加开发板管理器 URLs」中添加：
   ```
   https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
   ```
3. 打开「工具」→「开发板」→「开发板管理器」
4. 搜索「esp32」并安装

### 4.3 安装依赖库

1. **PubSubClient**：MQTT 客户端
   - 打开「工具」→「管理库」
   - 搜索「PubSubClient」并安装

2. **ArduinoJson**：JSON 解析
   - 搜索「ArduinoJson」并安装

### 4.4 修改代码配置

编辑 `esp32_controller.ino`，修改以下配置：

```cpp
// WiFi 配置
const char* WIFI_SSID = "你的WiFi名称";
const char* WIFI_PASSWORD = "你的WiFi密码";

// MQTT 配置
const char* MQTT_SERVER = "broker.xxxxx.cluster.hivemq.cloud";
const char* MQTT_USERNAME = "你的MQTT用户名";
const char* MQTT_PASSWORD = "你的MQTT密码";
```

### 4.5 上传代码

1. 连接 ESP32 到电脑
2. 选择开发板：`工具` → `开发板` → `ESP32 Dev Module`
3. 选择端口：`工具` → `端口` → `/dev/cu.usbserial-xxxx`
4. 点击「上传」

---

## 第五步：测试验证

### 5.1 MQTT 模拟测试

在没有 ESP32 的情况下测试 MQTT 通信：

```bash
cd test
pip install paho-mqtt

# 运行双向模拟测试
python mqtt_simulator.py --mode both
```

按提示发送测试指令，观察消息收发。

### 5.2 飞书消息测试

1. 在飞书中找到你的机器人
2. 发送消息「开灯」「关灯」「马达左转」「马达右转」
3. 观察 ESP32（或模拟器）的响应

### 5.3 常见问题排查

| 问题 | 可能原因 | 解决方法 |
|------|---------|---------|
| MQTT 连接失败 | 账号密码错误/网络问题 | 检查 MQTT 凭据 |
| 飞书消息无响应 | 后端服务未启动/地址错误 | 检查服务状态和 URL |
| ESP32 不执行指令 | 代码未上传/WiFi 不通 | 检查串口监视器日志 |
| 消息延迟 | 网络延迟/MQTT QoS | 使用局域网或提高 QoS |

---

## 使用方式

### 文本指令

直接在飞书对话中发送：
- `开灯` / `/开灯`
- `关灯` / `/关灯`
- `马达左转` / `/马达左转`
- `马达右转` / `/马达右转`
- `状态` / `/状态`

### 卡片按钮

发送控制面板卡片（需后端发送卡片消息）。

---

## 安全建议

1. **MQTT 认证**：HiveMQ Cloud 已启用用户名密码认证
2. **飞书签名验证**：生产环境应启用 `encrypt_key` 验证请求签名
3. **HTTPS**：后端服务必须使用 HTTPS
4. **环境变量**：不要将敏感信息硬编码在代码中

---

## 扩展功能

### 添加更多控制指令

1. 在 `app_config.py` 的 `Commands` 类中添加新指令
2. 在 `feishu_card.py` 中添加对应按钮
3. 在 `esp32_controller.ino` 的 `handle_command()` 中处理

### 多设备控制

修改 MQTT Topic 设计：
- 控制：`device/{device_id}/control`
- 状态：`device/{device_id}/status`

### 定时任务

结合系统定时（如 cron）发送指令，实现自动化控制。

---

## 技术参考

- [飞书开放平台文档](https://open.feishu.cn/document/)
- [HiveMQ Cloud 文档](https://www.hivemq.com/docs/hivemq-cloud/latest/)
- [ESP32 Arduino 文档](https://docs.espressif.com/projects/arduino-esp32/)
- [PubSubClient 库](https://pubsubclient.knolleary.net/)

---

## License

MIT License
