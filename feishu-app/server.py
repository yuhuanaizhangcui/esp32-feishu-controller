#!/usr/bin/env python3
"""
ESP32 控制器 - 飞书后端服务
接收飞书事件，处理用户指令，通过 MQTT 发送到 ESP32
"""

import json
import logging
import time
from typing import Dict, Any, Optional

from flask import Flask, request, jsonify
from threading import Thread

# 导入配置
from app_config import (
    feishu_config, mqtt_config, server_config,
    validate_config, Commands
)

# 导入飞书卡片构建器
from feishu_card import (
    build_control_card,
    build_status_card,
    build_response_message,
    card_to_json
)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 初始化 Flask 应用
app = Flask(__name__)

# 全局 MQTT 客户端
mqtt_client = None


def init_mqtt_client() -> bool:
    """初始化 MQTT 客户端"""
    try:
        import paho.mqtt.client as mqtt

        client = mqtt.Client(client_id=f"feishu_esp32_{int(time.time())}")

        # 设置认证
        if mqtt_config.username and mqtt_config.password:
            client.username_pw_set(mqtt_config.username, mqtt_config.password)

        # 连接回调
        def on_connect(client, userdata, flags, rc):
            if rc == 0:
                logger.info(f"✅ MQTT 连接成功: {mqtt_config.broker_host}:{mqtt_config.broker_port}")
                # 订阅状态主题
                client.subscribe(mqtt_config.status_topic, qos=mqtt_config.qos)
            else:
                logger.error(f"❌ MQTT 连接失败，错误码: {rc}")

        # 消息回调
        def on_message(client, userdata, msg):
            try:
                payload = msg.payload.decode('utf-8')
                logger.info(f"📨 收到 MQTT 消息 [{msg.topic}]: {payload}")
            except Exception as e:
                logger.error(f"处理 MQTT 消息失败: {e}")

        # 断开连接回调
        def on_disconnect(client, userdata, rc):
            logger.warning(f"⚠️ MQTT 连接断开，错误码: {rc}")

        client.on_connect = on_connect
        client.on_message = on_message
        client.on_disconnect = on_disconnect

        # 连接到 Broker
        if mqtt_config.use_tls:
            client.tls_set()  # 使用默认 TLS 设置

        client.connect(mqtt_config.broker_host, mqtt_config.broker_port, mqtt_config.keepalive)

        # 启动 MQTT 循环线程
        client.loop_start()

        return client

    except ImportError:
        logger.error("❌ paho-mqtt 未安装，请运行: pip install paho-mqtt")
        return None
    except Exception as e:
        logger.error(f"❌ MQTT 初始化失败: {e}")
        return None


def publish_command(command: str, extra_data: Optional[Dict] = None) -> bool:
    """发布控制指令到 MQTT"""
    global mqtt_client

    if not mqtt_client:
        logger.error("MQTT 客户端未初始化")
        return False

    # 构建指令消息
    message = {
        "action": command,
        "timestamp": int(time.time()),
        "source": "feishu"
    }

    if extra_data:
        message.update(extra_data)

    try:
        payload = json.dumps(message, ensure_ascii=False)
        result = mqtt_client.publish(
            mqtt_config.control_topic,
            payload,
            qos=mqtt_config.qos
        )

        if result.rc == 0:
            logger.info(f"✅ 指令发送成功: {command}")
            return True
        else:
            logger.error(f"❌ 指令发送失败，错误码: {result.rc}")
            return False

    except Exception as e:
        logger.error(f"❌ 发布指令异常: {e}")
        return False


# ===== 飞书事件处理 =====

def get_feishu_access_token() -> Optional[str]:
    """获取飞书 tenant_access_token"""
    try:
        import requests
        
        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        data = {
            "app_id": feishu_config.app_id,
            "app_secret": feishu_config.app_secret
        }
        
        response = requests.post(url, json=data, timeout=10)
        result = response.json()
        
        if result.get("code") == 0:
            token = result.get("tenant_access_token")
            logger.info("✅ 获取飞书访问令牌成功")
            return token
        else:
            logger.error(f"❌ 获取飞书令牌失败: {result.get('msg')}")
            return None
    except Exception as e:
        logger.error(f"❌ 获取飞书令牌异常: {e}")
        return None


def send_feishu_message(open_id: str, content: str, msg_type: str = "text"):
    """
    发送飞书消息
    
    Args:
        open_id: 接收者的 open_id
        content: 消息内容（JSON字符串或纯文本）
        msg_type: 消息类型 (text, interactive)
    """
    try:
        import requests
        
        token = get_feishu_access_token()
        if not token:
            logger.error("无法获取飞书访问令牌")
            return False
        
        url = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=open_id"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8"
        }
        data = {
            "receive_id": open_id,
            "msg_type": msg_type,
            "content": content
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=10)
        result = response.json()
        
        if result.get("code") == 0:
            logger.info(f"✅ 飞书消息发送成功")
            return True
        else:
            logger.error(f"❌ 飞书消息发送失败: {result.get('msg')}")
            return False
    except Exception as e:
        logger.error(f"❌ 发送飞书消息异常: {e}")
        return False


def send_feishu_card(open_id: str, card: Dict[str, Any]) -> bool:
    """
    发送飞书卡片消息
    
    Args:
        open_id: 接收者的 open_id
        card: 卡片字典（由 feishu_card.py 构建）
    """
    content = card_to_json(card)
    return send_feishu_message(open_id, content, msg_type="interactive")


def verify_request_signature(request) -> bool:
    """验证飞书请求签名（可选，推荐启用）"""
    # 飞书会在 Header 中携带签名，这里简化为返回 True
    # 生产环境建议实现完整的签名验证
    return True


def handle_message_event(event_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    处理接收消息事件
    
    Returns:
        包含处理结果的字典，包括是否发送卡片、回复消息等
    """
    try:
        # 解析事件数据
        sender_id = event_data.get("sender", {}).get("sender_id", {}).get("open_id")
        message_type = event_data.get("message_type")
        text = ""

        if message_type == "text":
            text = event_data.get("text", "").strip()
        elif message_type == "interactive":
            # 处理卡片按钮点击
            text = event_data.get("interactive", {}).get("value", {}).get("action", "")

        logger.info(f"📩 收到消息: {text} (from: {sender_id})")

        # 解析指令
        command_map = {
            "控制": "show_control_card",
            "/控制": "show_control_card",
            "开灯": Commands.LED_ON,
            "关灯": Commands.LED_OFF,
            "马达左转": Commands.MOTOR_LEFT,
            "马达右转": Commands.MOTOR_RIGHT,
            "/开灯": Commands.LED_ON,
            "/关灯": Commands.LED_OFF,
            "/马达左转": Commands.MOTOR_LEFT,
            "/马达右转": Commands.MOTOR_RIGHT,
            "/状态": Commands.STATUS,
        }

        command = command_map.get(text)

        if command == "show_control_card":
            # 发送控制面板卡片
            card = build_control_card()
            if sender_id:
                send_feishu_card(sender_id, card)
            return {"success": True, "action": "show_control_card"}

        elif command:
            # 发送 MQTT 指令
            success = publish_command(command)

            # 发送回复消息
            if sender_id:
                if success:
                    reply_text = build_response_message(True, command)
                else:
                    reply_text = build_response_message(False, command)
                send_feishu_message(sender_id, reply_text, msg_type="text")

            return {"success": success, "command": command}

        else:
            # 未知指令，发送帮助卡片
            if sender_id:
                help_text = "💡 支持的指令:\n- 控制（显示控制面板）\n- 开灯/关灯\n- 马达左转/马达右转"
                send_feishu_message(sender_id, help_text, msg_type="text")
            return {"success": False, "error": "unknown_command"}

    except Exception as e:
        logger.error(f"处理消息事件失败: {e}")
        if sender_id:
            send_feishu_message(sender_id, "❌ 处理消息时发生错误", msg_type="text")
        return {"success": False, "error": str(e)}


# ===== Flask 路由 =====

@app.route("/health", methods=["GET"])
def health_check():
    """健康检查"""
    mqtt_status = "connected" if mqtt_client and mqtt_client.is_connected() else "disconnected"
    return jsonify({
        "status": "ok",
        "mqtt": mqtt_status,
        "timestamp": int(time.time())
    })


@app.route("/feishu/webhook", methods=["POST"])
def feishu_webhook():
    """飞书事件订阅 Webhook"""
    try:
        # 获取请求数据
        body = request.get_json(force=True)
        logger.info(f"📥 飞书事件: {json.dumps(body, ensure_ascii=False)}")

        # 处理飞书验证挑战
        if "challenge" in body:
            return jsonify({"challenge": body["challenge"]})

        # 验证请求（可选）
        if not verify_request_signature(request):
            return jsonify({"error": "Invalid signature"}), 403

        # 解析事件类型
        header = body.get("header", {})
        event_type = header.get("event_type")

        if event_type == "im.message.receive_v1":
            # 处理消息接收事件
            # handle_message_event 现在负责发送消息到飞书
            # 这里只需要调用它并确认处理成功
            event = body.get("event", {})
            result = handle_message_event(event)

            logger.info(f"消息处理完成: {result}")
            return jsonify({"success": True})

        return jsonify({"success": True})

    except Exception as e:
        logger.error(f"Webhook 处理失败: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/control", methods=["POST"])
def api_control():
    """HTTP API 控制接口（备用）"""
    try:
        data = request.get_json(force=True)
        command = data.get("command")

        if not command or command not in Commands.ALL_COMMANDS:
            return jsonify({
                "error": "Invalid command",
                "valid_commands": Commands.ALL_COMMANDS
            }), 400

        success = publish_command(command)

        return jsonify({
            "success": success,
            "command": command,
            "description": Commands.CMD_DESCRIPTIONS.get(command)
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ===== 主程序 =====

def main():
    """主函数"""
    logger.info("🚀 启动 ESP32 控制器服务...")

    # 验证配置
    if not validate_config():
        logger.warning("配置不完整，部分功能可能无法使用")

    # 初始化 MQTT
    global mqtt_client
    mqtt_client = init_mqtt_client()

    if not mqtt_client:
        logger.warning("⚠️ MQTT 客户端初始化失败，将以受限模式启动")

    # 启动 Flask 服务
    logger.info(f"🌐 服务启动: http://{server_config.host}:{server_config.port}")
    app.run(
        host=server_config.host,
        port=server_config.port,
        debug=server_config.debug
    )


if __name__ == "__main__":
    main()
