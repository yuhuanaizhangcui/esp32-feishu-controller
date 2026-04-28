# ESP32 飞书控制器

使用飞书控制的 ESP32 IoT 项目，通过云 MQTT 中转实现 LED 和马达的远程控制。

## 📁 项目结构

```
esp32-feishu-controller/
├── feishu-app/              # 飞书后端服务
│   ├── server.py          # Flask 主服务
│   ├── app_config.py       # 配置管理
│   ├── feishu_card.py      # 交互卡片构建器
│   └── requirements.txt    # Python 依赖
├── esp32-code/             # ESP32 Arduino 代码
│   └── esp32_controller.ino
├── deploy/                 # 云服务器部署脚本
│   ├── init_server.sh      # 服务器初始化
│   ├── deploy_app.sh       # 应用部署
│   └── esp32-backend.service
├── test/                   # 测试脚本
│   └── mqtt_simulator.py   # MQTT 模拟器
└── docs/                   # 文档
    ├── README.md           # 项目说明
    └── DEPLOY_CLOUD.md     # 云部署指南
```

## 🔧 快速开始

### 1. 配置 HiveMQ Cloud

1. 注册 [HiveMQ Cloud](https://console.hivemq.cloud/)
2. 创建免费集群，获取连接信息

### 2. 创建飞书应用

1. 进入 [飞书开放平台](https://open.feishu.cn/)
2. 创建自建应用，获取 App ID 和 App Secret
3. 配置事件订阅，URL 填写你的后端地址

### 3. 部署后端服务

```bash
cd feishu-app
pip install -r requirements.txt

# 配置环境变量
export FEISHU_APP_ID=your-app-id
export FEISHU_APP_SECRET=your-app-secret
export MQTT_USERNAME=your-mqtt-username
export MQTT_PASSWORD=your-mqtt-password

# 启动服务
python server.py
```

### 4. 烧录 ESP32

使用 Arduino IDE 或 PlatformIO 打开 `esp32-code/esp32_controller.ino`，配置 WiFi 和 MQTT 信息后烧录。

## 📡 系统架构

```
[飞书客户端]
    ↓
[飞书开放平台] → 事件订阅
    ↓
[Python Flask 后端]
    ↓ (MQTT)
[云 MQTT Broker] (HiveMQ Cloud)
    ↓ (MQTT)
[ESP32 开发板]
```

## 🎮 支持的指令

| 指令 | 功能 |
|------|------|
| 开灯 | 点亮 LED |
| 关灯 | 熄灭 LED |
| 马达左转 | 马达逆时针旋转 |
| 马达右转 | 马达顺时针旋转 |
| 控制 | 显示交互控制面板 |

## 📖 详细文档

- [云服务器部署指南](./deploy/DEPLOY_CLOUD.md)

## 📜 License

MIT License
