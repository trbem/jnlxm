#ifndef CONFIG_H
#define CONFIG_H

// WiFi 配置
#define WIFI_SSID     "431"
#define WIFI_PASSWORD "88888888"

// 服务器配置
#define API_URL       "http://10.1.41.99"
#define API_PORT      8000

// 设备配置
#define DEVICE_NAME   "ESP32-S3-EYE-001"

// 检测配置
#define DETECTION_INTERVAL_MS   10000  // 检测间隔 (ms)
#define FACE_QUALITY_THRESHOLD  0.7    // 人脸质量阈值

// 图像配置
#define IMAGE_WIDTH   320
#define IMAGE_HEIGHT  240

// LED 引脚配置
#define LED_GREEN_PIN 48
#define LED_RED_PIN   45
#define LED_BLUE_PIN  21

// 状态定义
typedef enum {
    DEVICE_STATE_INIT = 0,
    DEVICE_STATE_WIFI_CONNECTING,
    DEVICE_STATE_WIFI_CONNECTED,
    DEVICE_STATE_REGISTERING,
    DEVICE_STATE_RUNNING,
    DEVICE_STATE_ERROR
} device_state_t;

typedef enum {
    RECOGNITION_RESULT_UNKNOWN = 0,
    RECOGNITION_RESULT_FAMILY,
    RECOGNITION_RESULT_STRANGER,
    RECOGNITION_RESULT_ERROR
} recognition_result_t;

#endif // CONFIG_H
