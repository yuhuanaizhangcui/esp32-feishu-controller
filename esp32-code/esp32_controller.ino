/*
 * ESP32 控制器 - 飞书远程控制
 * 功能: 通过 MQTT 接收飞书指令，控制 LED 和马达
 * 
 * 硬件连接:
 * - LED: GPIO 2 (内置LED，或外接LED通过220Ω电阻)
 * - 马达 IN1: GPIO 18
 * - 马达 IN2: GPIO 19  
 * - 马达 ENA: GPIO 21 (PWM调速，可选)
 * 
 * 依赖库:
 * - WiFi (内置)
 * - PubSubClient (MQTT客户端) - 通过库管理器安装
 * 
 * 安装步骤:
 * 1. Arduino IDE -> 工具 -> 开发板 -> ESP32 Dev Module
 * 2. 工具 -> 管理库 -> 搜索 "PubSubClient" -> 安装
 * 3. 修改下方配置区的 WiFi 和 MQTT 参数
 * 4. 上传代码
 */

#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

// ===== 配置区 =====
const char* WIFI_SSID = "YOUR_WIFI_SSID";           // TODO: 修改为你的 WiFi 名称
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";    // TODO: 修改为你的 WiFi 密码

// MQTT Broker 配置 (HiveMQ Cloud 免费版)
const char* MQTT_SERVER = "broker.hivemq.cloud";     // TODO: 修改为你的 MQTT Broker 地址
const int   MQTT_PORT = 8883;                       // TLS 端口
const char* MQTT_USERNAME = "your-username";         // TODO: 修改为 MQTT 用户名
const char* MQTT_PASSWORD = "your-password";        // TODO: 修改为 MQTT 密码

// MQTT Topic
const char* MQTT_CONTROL_TOPIC = "esp32/control";    // 指令下发主题
const char* MQTT_STATUS_TOPIC = "esp32/status";     // 状态上报主题

// GPIO 引脚定义
const int LED_PIN = 2;         // 内置 LED 引脚
const int MOTOR_IN1 = 18;      // 马达控制引脚 1
const int MOTOR_IN2 = 19;      // 马达控制引脚 2
const int MOTOR_ENA = 21;      // 马达使能引脚 (PWM)

// ===== 全局对象 =====
WiFiClientSecure wifi_client;
PubSubClient mqtt_client(wifi_client);

// 状态变量
bool led_state = false;
String motor_state = "stop";   // stop, left, right
unsigned long device_uptime = 0;
unsigned long last_status_time = 0;
const unsigned long STATUS_INTERVAL = 10000;  // 每10秒上报一次状态

// ===== 函数声明 =====
void connect_wifi();
void connect_mqtt();
void mqtt_callback(char* topic, byte* payload, unsigned int length);
void publish_status();
void handle_command(const char* command);
void set_led(bool on);
void set_motor(const char* direction);


// ===== 初始化 =====
void setup() {
  // 初始化串口
  Serial.begin(115200);
  delay(1000);
  
  Serial.println("\n=== ESP32 控制器启动 ===");
  
  // 初始化 GPIO
  pinMode(LED_PIN, OUTPUT);
  pinMode(MOTOR_IN1, OUTPUT);
  pinMode(MOTOR_IN2, OUTPUT);
  pinMode(MOTOR_ENA, OUTPUT);
  
  // 初始状态
  digitalWrite(LED_PIN, LOW);
  digitalWrite(MOTOR_IN1, LOW);
  digitalWrite(MOTOR_IN2, LOW);
  digitalWrite(MOTOR_ENA, HIGH);  // 使能马达驱动
  
  // 连接 WiFi
  connect_wifi();
  
  // 配置 MQTT
  wifi_client.setInsecure();  // 简化 TLS 验证（生产环境应使用证书）
  mqtt_client.setServer(MQTT_SERVER, MQTT_PORT);
  mqtt_client.setCallback(mqtt_callback);
  
  // 连接 MQTT
  connect_mqtt();
  
  // 记录启动时间
  device_uptime = millis();
  
  Serial.println("✅ 初始化完成，等待指令...");
}

// ===== 主循环 =====
void loop() {
  // 确保 MQTT 连接
  if (!mqtt_client.connected()) {
    connect_mqtt();
  }
  mqtt_client.loop();
  
  // 定期上报状态
  if (millis() - last_status_time > STATUS_INTERVAL) {
    publish_status();
    last_status_time = millis();
  }
  
  // 心跳 LED 闪烁 (每5秒一次)
  if (millis() % 5000 < 50) {
    digitalWrite(LED_PIN, !digitalRead(LED_PIN));
    delay(50);
    digitalWrite(LED_PIN, led_state);  // 恢复实际状态
  }
  
  delay(10);
}


// ===== WiFi 连接 =====
void connect_wifi() {
  Serial.print("📡 连接 WiFi: ");
  Serial.println(WIFI_SSID);
  
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  
  int retry = 0;
  while (WiFi.status() != WL_CONNECTED && retry < 20) {
    delay(500);
    Serial.print(".");
    retry++;
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println();
    Serial.print("✅ WiFi 已连接，IP: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println();
    Serial.println("❌ WiFi 连接失败，将在5秒后重启...");
    delay(5000);
    ESP.restart();
  }
}


// ===== MQTT 连接 =====
void connect_mqtt() {
  while (!mqtt_client.connected()) {
    Serial.print("📨 连接 MQTT Broker...");
    
    // 生成唯一客户端 ID
    String client_id = "esp32_controller_" + String(WiFi.macAddress());
    client_id.replace(":", "");
    
    if (mqtt_client.connect(client_id.c_str(), MQTT_USERNAME, MQTT_PASSWORD)) {
      Serial.println(" ✅ 已连接");
      
      // 订阅控制主题
      if (mqtt_client.subscribe(MQTT_CONTROL_TOPIC)) {
        Serial.print("✅ 已订阅主题: ");
        Serial.println(MQTT_CONTROL_TOPIC);
      } else {
        Serial.println("❌ 订阅失败");
      }
      
      // 上报上线状态
      publish_status();
      
    } else {
      Serial.print(" ❌ 连接失败，错误码: ");
      Serial.print(mqtt_client.state());
      Serial.println("，5秒后重试...");
      delay(5000);
    }
  }
}


// ===== MQTT 消息回调 =====
void mqtt_callback(char* topic, byte* payload, unsigned int length) {
  Serial.print("📩 收到消息 [");
  Serial.print(topic);
  Serial.print("]: ");
  
  // 解析 JSON 消息
  DynamicJsonDocument doc(256);
  DeserializationError error = deserializeJson(doc, payload, length);
  
  if (error) {
    Serial.print("❌ JSON 解析失败: ");
    Serial.println(error.c_str());
    return;
  }
  
  // 提取指令
  const char* action = doc["action"];
  if (action) {
    Serial.print("执行指令: ");
    Serial.println(action);
    handle_command(action);
  } else {
    Serial.println("⚠️ 消息中未找到 action 字段");
  }
}


// ===== 处理指令 =====
void handle_command(const char* command) {
  if (strcmp(command, "led_on") == 0) {
    set_led(true);
    Serial.println("💡 LED 已打开");
  }
  else if (strcmp(command, "led_off") == 0) {
    set_led(false);
    Serial.println("⚫ LED 已关闭");
  }
  else if (strcmp(command, "motor_left") == 0) {
    set_motor("left");
    Serial.println("⬅️ 马达左转");
  }
  else if (strcmp(command, "motor_right") == 0) {
    set_motor("right");
    Serial.println("➡️ 马达右转");
  }
  else if (strcmp(command, "status") == 0) {
    publish_status();
    Serial.println("📊 状态已上报");
  }
  else {
    Serial.print("⚠️ 未知指令: ");
    Serial.println(command);
  }
  
  // 上报执行后的状态
  delay(100);
  publish_status();
}


// ===== 控制 LED =====
void set_led(bool on) {
  led_state = on;
  digitalWrite(LED_PIN, on ? HIGH : LOW);
}


// ===== 控制马达 =====
void set_motor(const char* direction) {
  motor_state = direction;
  
  if (strcmp(direction, "left") == 0) {
    // 左转: IN1=HIGH, IN2=LOW
    digitalWrite(MOTOR_IN1, HIGH);
    digitalWrite(MOTOR_IN2, LOW);
  }
  else if (strcmp(direction, "right") == 0) {
    // 右转: IN1=LOW, IN2=HIGH
    digitalWrite(MOTOR_IN1, LOW);
    digitalWrite(MOTOR_IN2, HIGH);
  }
  else {
    // 停止: IN1=LOW, IN2=LOW
    digitalWrite(MOTOR_IN1, LOW);
    digitalWrite(MOTOR_IN2, LOW);
    motor_state = "stop";
  }
}


// ===== 上报状态 =====
void publish_status() {
  if (!mqtt_client.connected()) return;
  
  DynamicJsonDocument doc(256);
  doc["led"] = led_state ? "on" : "off";
  doc["motor"] = motor_state;
  doc["uptime"] = (millis() - device_uptime) / 1000;
  doc["ip"] = WiFi.localIP().toString();
  doc["rssi"] = WiFi.RSSI();
  
  char buffer[256];
  size_t n = serializeJson(doc, buffer);
  
  if (mqtt_client.publish(MQTT_STATUS_TOPIC, buffer, n)) {
    Serial.print("📤 状态已上报: ");
    Serial.println(buffer);
  } else {
    Serial.println("❌ 状态上报失败");
  }
}
