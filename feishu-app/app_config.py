"""
飞书应用配置
请根据实际部署环境修改以下配置
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class FeishuConfig:
    """飞书应用配置"""
    # 飞书应用凭证（从飞书开放平台获取）
    app_id: str = os.getenv("FEISHU_APP_ID", "cli_xxxxxxxxxxxxxxxxxxxxxxxx")
    app_secret: str = os.getenv("FEISHU_APP_SECRET", "your-app-secret-here")

    # 飞书事件订阅配置
    verify_token: str = os.getenv("FEISHU_VERIFY_TOKEN", "your-verify-token-here")
    webhook_url: str = os.getenv("FEISHU_WEBHOOK_URL", "https://your-server-domain.com/feishu/webhook")

    # 消息加密密钥（可选，但推荐启用）
    encrypt_key: Optional[str] = os.getenv("FEISHU_ENCRYPT_KEY", None)


@dataclass
class MQTTConfig:
    """MQTT Broker 配置（推荐使用 HiveMQ Cloud 免费版）"""
    # HiveMQ Cloud 免费版配置
    broker_host: str = os.getenv("MQTT_BROKER_HOST", "broker.hivemq.cloud")
    broker_port: int = int(os.getenv("MQTT_BROKER_PORT", "8883"))

    # 认证凭据（从 HiveMQ Cloud 获取）
    username: str = os.getenv("MQTT_USERNAME", "your-mqtt-username")
    password: str = os.getenv("MQTT_PASSWORD", "your-mqtt-password")

    # TLS/SSL 配置（HiveMQ Cloud 需要 TLS）
    use_tls: bool = True
    tls_insecure: bool = False  # 生产环境建议设为 False

    # MQTT Topic 配置
    control_topic: str = "esp32/control"  # 指令下发主题
    status_topic: str = "esp32/status"    # 状态上报主题

    # 连接参数
    keepalive: int = 60
    qos: int = 1  # QoS 1 确保消息至少送达一次


@dataclass
class ServerConfig:
    """后端服务配置"""
    host: str = os.getenv("SERVER_HOST", "0.0.0.0")
    port: int = int(os.getenv("SERVER_PORT", "5000"))
    debug: bool = os.getenv("SERVER_DEBUG", "false").lower() == "true"


@dataclass
class GPIOMapping:
    """ESP32 GPIO 引脚映射（供参考，实际接线时确认）"""
    LED_PIN: int = 2           # 内置LED引脚（方便测试）
    MOTOR_IN1: int = 18        # 马达控制引脚1
    MOTOR_IN2: int = 19        # 马达控制引脚2
    MOTOR_ENA: int = 21        # 马达使能引脚（PWM调速）


# 全局配置实例
feishu_config = FeishuConfig()
mqtt_config = MQTTConfig()
server_config = ServerConfig()
gpio_mapping = GPIOMapping()


# 支持的指令定义
class Commands:
    """支持的指令列表"""
    LED_ON = "led_on"
    LED_OFF = "led_off"
    MOTOR_LEFT = "motor_left"
    MOTOR_RIGHT = "motor_right"
    STATUS = "status"

    ALL_COMMANDS = [LED_ON, LED_OFF, MOTOR_LEFT, MOTOR_RIGHT, STATUS]

    # 指令中文描述
    CMD_DESCRIPTIONS = {
        LED_ON: "开灯",
        LED_OFF: "关灯",
        MOTOR_LEFT: "马达左转",
        MOTOR_RIGHT: "马达右转",
        STATUS: "查询状态"
    }


def validate_config() -> bool:
    """验证配置是否完整"""
    errors = []

    if feishu_config.app_id.startswith("cli_") and "xxxxxxxx" in feishu_config.app_id:
        errors.append("飞书 App ID 未配置")

    if feishu_config.app_secret == "your-app-secret-here":
        errors.append("飞书 App Secret 未配置")

    if mqtt_config.username == "your-mqtt-username":
        errors.append("MQTT 用户名未配置")

    if "your-server-domain" in feishu_config.webhook_url:
        errors.append("飞书 Webhook URL 未配置")

    if errors:
        print("⚠️ 配置警告:")
        for error in errors:
            print(f"  - {error}")
        print("请修改 app_config.py 或设置环境变量")
        return False

    return True
