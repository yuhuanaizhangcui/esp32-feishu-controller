#!/usr/bin/env python3
"""
MQTT 模拟测试脚本
用于无硬件时验证 MQTT 通信流程

功能:
1. 模拟 ESP32 设备订阅控制指令
2. 模拟飞书后端发布控制指令
3. 监听设备状态上报
4. 测试各种指令的收发
"""

import json
import time
import threading
import argparse
from typing import Optional

try:
    import paho.mqtt.client as mqtt
except ImportError:
    print("❌ 未安装 paho-mqtt，请运行: pip install paho-mqtt")
    exit(1)


# ===== 配置 (与 app_config.py 保持一致) =====
MQTT_BROKER = "broker.hivemq.cloud"  # TODO: 修改为你的 MQTT Broker
MQTT_PORT = 8883
MQTT_USERNAME = "your-username"        # TODO: 修改为你的用户名
MQTT_PASSWORD = "your-password"       # TODO: 修改为你的密码

CONTROL_TOPIC = "esp32/control"
STATUS_TOPIC = "esp32/status"

# 支持的指令
COMMANDS = {
    "1": ("led_on", "开灯"),
    "2": ("led_off", "关灯"),
    "3": ("motor_left", "马达左转"),
    "4": ("motor_right", "马达右转"),
    "5": ("status", "查询状态"),
}


class MQTTSimulator:
    """MQTT 模拟器"""

    def __init__(self, client_id: str, use_tls: bool = True):
        self.client = mqtt.Client(client_id=client_id)
        self.client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)

        # 回调
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect

        self.use_tls = use_tls

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print(f"✅ [{client._client_id}] MQTT 连接成功")
        else:
            print(f"❌ [{client._client_id}] MQTT 连接失败，错误码: {rc}")

    def on_message(self, client, userdata, msg):
        try:
            payload = msg.payload.decode('utf-8')
            print(f"\n📨 [{client._client_id}] 收到消息 [{msg.topic}]:")
            print(f"   {payload}")
        except Exception as e:
            print(f"❌ 消息处理失败: {e}")

    def on_disconnect(self, client, userdata, rc):
        print(f"⚠️ [{client._client_id}] MQTT 连接断开")

    def connect(self):
        if self.use_tls:
            self.client.tls_set()
        self.client.connect(MQTT_BROKER, MQTT_PORT, 60)
        self.client.loop_start()

    def disconnect(self):
        self.client.loop_stop()
        self.client.disconnect()

    def subscribe(self, topic: str):
        self.client.subscribe(topic)
        print(f"📡 [{self.client._client_id}] 已订阅: {topic}")

    def publish(self, topic: str, message: dict):
        payload = json.dumps(message, ensure_ascii=False)
        self.client.publish(topic, payload)
        print(f"📤 [{self.client._client_id}] 发布消息 [{topic}]:")
        print(f"   {payload}")


def run_device_simulator():
    """运行设备模拟器（模拟 ESP32）"""
    print("\n" + "="*50)
    print("🤖 ESP32 设备模拟器启动")
    print("="*50)

    device = MQTTSimulator("esp32_simulator")
    device.connect()
    device.subscribe(CONTROL_TOPIC)

    print(f"✅ 设备模拟器已启动，等待指令...")
    print(f"   订阅主题: {CONTROL_TOPIC}")
    print(f"   状态主题: {STATUS_TOPIC}")
    print("-"*50)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 设备模拟器停止")
        device.disconnect()


def run_controller_simulator():
    """运行控制器模拟器（模拟飞书后端）"""
    print("\n" + "="*50)
    print("🎮 控制器模拟器启动 (模拟飞书后端)")
    print("="*50)

    controller = MQTTSimulator("controller_simulator")
    controller.connect()
    controller.subscribe(STATUS_TOPIC)

    print(f"✅ 控制器模拟器已启动")
    print(f"   监听状态: {STATUS_TOPIC}")
    print("-"*50)

    try:
        while True:
            print("\n请选择要发送的指令:")
            for key, (cmd, desc) in COMMANDS.items():
                print(f"  {key}. {desc} ({cmd})")
            print("  q. 退出")

            choice = input("\n请输入选项: ").strip().lower()

            if choice == 'q':
                break

            if choice in COMMANDS:
                cmd, desc = COMMANDS[choice]
                message = {
                    "action": cmd,
                    "timestamp": int(time.time()),
                    "source": "simulator"
                }
                controller.publish(CONTROL_TOPIC, message)
            else:
                print("⚠️ 无效选项，请重新选择")

    except KeyboardInterrupt:
        pass
    finally:
        print("\n🛑 控制器模拟器停止")
        controller.disconnect()


def run_both():
    """同时运行设备模拟器和控制器模拟器"""
    print("\n" + "="*50)
    print("🔄 双向模拟模式")
    print("="*50)

    # 创建设备模拟器线程
    device = MQTTSimulator("esp32_simulator_both")
    device.connect()
    device.subscribe(CONTROL_TOPIC)

    # 创建控制器模拟器线程
    controller = MQTTSimulator("controller_simulator_both")
    controller.connect()
    controller.subscribe(STATUS_TOPIC)

    print(f"✅ 双向模拟已启动")
    print(f"   设备模拟器订阅: {CONTROL_TOPIC}")
    print(f"   控制器模拟器订阅: {STATUS_TOPIC}")
    print("-"*50)

    try:
        # 主线程作为控制器发送指令
        while True:
            print("\n请选择要发送的指令:")
            for key, (cmd, desc) in COMMANDS.items():
                print(f"  {key}. {desc} ({cmd})")
            print("  a. 自动测试（发送所有指令）")
            print("  q. 退出")

            choice = input("\n请输入选项: ").strip().lower()

            if choice == 'q':
                break
            elif choice == 'a':
                # 自动测试
                print("\n🤖 自动测试开始...")
                for key, (cmd, desc) in COMMANDS.items():
                    message = {
                        "action": cmd,
                        "timestamp": int(time.time()),
                        "source": "auto_test"
                    }
                    controller.publish(CONTROL_TOPIC, message)
                    time.sleep(1)
                print("✅ 自动测试完成\n")
            elif choice in COMMANDS:
                cmd, desc = COMMANDS[choice]
                message = {
                    "action": cmd,
                    "timestamp": int(time.time()),
                    "source": "simulator"
                }
                controller.publish(CONTROL_TOPIC, message)
            else:
                print("⚠️ 无效选项，请重新选择")

    except KeyboardInterrupt:
        pass
    finally:
        print("\n🛑 模拟停止")
        device.disconnect()
        controller.disconnect()


def main():
    parser = argparse.ArgumentParser(description='ESP32 MQTT 模拟测试工具')
    parser.add_argument('--mode', choices=['device', 'controller', 'both'],
                        default='both', help='运行模式')
    args = parser.parse_args()

    print("\n" + "🚀 ESP32 MQTT 模拟测试工具".center(50, "="))
    print(f"MQTT Broker: {MQTT_BROKER}:{MQTT_PORT}")
    print(f"用户名: {MQTT_USERNAME}")
    print("="*50)

    if args.mode == 'device':
        run_device_simulator()
    elif args.mode == 'controller':
        run_controller_simulator()
    else:
        run_both()


if __name__ == "__main__":
    main()
