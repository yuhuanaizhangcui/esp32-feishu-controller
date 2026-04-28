#!/usr/bin/env python3
"""
飞书交互卡片构建器
生成带控制按钮的交互式卡片消息
"""

import json
from typing import Dict, List, Any


def build_control_card() -> Dict[str, Any]:
    """
    构建 ESP32 控制面板卡片

    返回符合飞书卡片 JSON 结构的字典
    文档: https://open.feishu.cn/document/ukTMukTMukTM/uczNxEjL3MTMx4yNzETM
    """
    card = {
        "config": {
            "wide_screen_mode": True,
            "enable_forward": True
        },
        "header": {
            "title": {
                "tag": "plain_text",
                "content": "🎮 ESP32 控制台"
            },
            "template": "blue"
        },
        "elements": [
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": "点击下方按钮控制 ESP32 开发板"
                }
            },
            {
                "tag": "hr"
            },
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": "**💡 LED 灯控制**"
                }
            },
            {
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {
                            "tag": "plain_text",
                            "content": "💡 开灯"
                        },
                        "type": "primary",
                        "value": {
                            "action": "led_on",
                            "source": "card_button"
                        },
                        "multi_interaction": False
                    },
                    {
                        "tag": "button",
                        "text": {
                            "tag": "plain_text",
                            "content": "⚫ 关灯"
                        },
                        "type": "danger",
                        "value": {
                            "action": "led_off",
                            "source": "card_button"
                        },
                        "multi_interaction": False
                    }
                ]
            },
            {
                "tag": "hr"
            },
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": "**🔄 马达控制**"
                }
            },
            {
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {
                            "tag": "plain_text",
                            "content": "⬅️ 马达左转"
                        },
                        "type": "default",
                        "value": {
                            "action": "motor_left",
                            "source": "card_button"
                        },
                        "multi_interaction": False
                    },
                    {
                        "tag": "button",
                        "text": {
                            "tag": "plain_text",
                            "content": "➡️ 马达右转"
                        },
                        "type": "default",
                        "value": {
                            "action": "motor_right",
                            "source": "card_button"
                        },
                        "multi_interaction": False
                    }
                ]
            },
            {
                "tag": "hr"
            },
            {
                "tag": "note",
                "elements": [
                    {
                        "tag": "plain_text",
                        "content": "Powered by ESP32 Controller | "
                    },
                    {
                        "tag": "a",
                        "text": "查看文档",
                        "href": "https://github.com/your-repo/esp32-feishu"
                    }
                ]
            }
        ]
    }

    return card


def build_status_card(status_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    构建设备状态卡片

    Args:
        status_data: 包含设备状态的字典，例如:
            {
                "led": "on/off",
                "motor": "left/right/stop",
                "uptime": 12345,
                "ip": "192.168.1.100"
            }
    """
    led_status = status_data.get("led", "unknown")
    motor_status = status_data.get("motor", "unknown")
    uptime = status_data.get("uptime", 0)
    ip = status_data.get("ip", "unknown")

    # 状态图标
    led_icon = "💡" if led_status == "on" else "⚫"
    motor_icon = "🔄" if motor_status != "stop" else "⏹️"

    card = {
        "config": {
            "wide_screen_mode": True
        },
        "header": {
            "title": {
                "tag": "plain_text",
                "content": "📊 设备状态"
            },
            "template": "green" if led_status == "on" or motor_status != "stop" else "grey"
        },
        "elements": [
            {
                "tag": "div",
                "fields": [
                    {
                        "is_short": True,
                        "text": {
                            "tag": "lark_md",
                            "content": f"**LED 状态**\n{led_icon} {led_status}"
                        }
                    },
                    {
                        "is_short": True,
                        "text": {
                            "tag": "lark_md",
                            "content": f"**马达状态**\n{motor_icon} {motor_status}"
                        }
                    }
                ]
            },
            {
                "tag": "div",
                "fields": [
                    {
                        "is_short": True,
                        "text": {
                            "tag": "lark_md",
                            "content": f"**运行时间**\n{uptime} 秒"
                        }
                    },
                    {
                        "is_short": True,
                        "text": {
                            "tag": "lark_md",
                            "content": f"**IP 地址**\n{ip}"
                        }
                    }
                ]
            },
            {
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {
                            "tag": "plain_text",
                            "content": "🔄 刷新状态"
                        },
                        "type": "default",
                        "value": {
                            "action": "status",
                            "source": "card_button"
                        }
                    }
                ]
            }
        ]
    }

    return card


def build_response_message(success: bool, action: str, extra_info: str = "") -> str:
    """
    构建简单的文本回复消息

    Args:
        success: 指令是否发送成功
        action: 执行的动作
        extra_info: 额外信息

    Returns:
        格式化的消息字符串
    """
    from app_config import Commands

    action_desc = Commands.CMD_DESCRIPTIONS.get(action, action)

    if success:
        msg = f"✅ **指令已发送**\n" \
              f"- 动作: {action_desc}\n" \
              f"- 状态: 已发送到设备"
    else:
        msg = f"❌ **指令发送失败**\n" \
              f"- 动作: {action_desc}\n" \
              f"- 请检查 MQTT 连接"

    if extra_info:
        msg += f"\n- 信息: {extra_info}"

    return msg


def card_to_json(card: Dict[str, Any], pretty: bool = False) -> str:
    """
    将卡片字典转换为 JSON 字符串

    Args:
        card: 卡片字典
        pretty: 是否格式化输出

    Returns:
        JSON 字符串
    """
    if pretty:
        return json.dumps(card, ensure_ascii=False, indent=2)
    return json.dumps(card, ensure_ascii=False)


# 测试代码
if __name__ == "__main__":
    # 测试控制卡片
    control_card = build_control_card()
    print("=== 控制面板卡片 ===")
    print(card_to_json(control_card, pretty=True))

    # 测试状态卡片
    status_data = {
        "led": "on",
        "motor": "left",
        "uptime": 12345,
        "ip": "192.168.1.100"
    }
    status_card = build_status_card(status_data)
    print("\n=== 设备状态卡片 ===")
    print(card_to_json(status_card, pretty=True))

    # 测试回复消息
    print("\n=== 回复消息 ===")
    print(build_response_message(True, "led_on"))
