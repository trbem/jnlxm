#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_system.h"
#include "esp_log.h"
#include "esp_timer.h"
#include "driver/gpio.h"
#include "wifi_connect.h"
#include "http_client.h"
#include "led_indicator.h"
#include "config.h"
#include "camera.h"
#include "face_detection.h"

static const char *TAG = "MAIN";

// 全局状态
static device_state_t g_device_state = DEVICE_STATE_INIT;
static char g_device_token[65] = {0};

// 硬件初始化
static esp_err_t hardware_init(void)
{
    ESP_LOGI(TAG, "初始化硬件...");

    // 初始化 LED GPIO
    led_init();

    // 初始化摄像头
    esp_err_t ret = camera_init();
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "摄像头初始化失败: %s", esp_err_to_name(ret));
    }

    ESP_LOGI(TAG, "硬件初始化完成");
    return ESP_OK;
}

// 获取设备配置
static void get_device_config(void)
{
    ESP_LOGI(TAG, "获取设备配置...");

    // 从服务器获取配置
    cJSON *config = http_get_config();

    if (config) {
        // 解析配置参数
        ESP_LOGI(TAG, "配置获取成功");
        cJSON_Delete(config);
    }
}

// 人脸检测任务
static void face_detection_task(void *pvParameters)
{
    ESP_LOGI(TAG, "人脸检测任务启动");

    while (g_device_state == DEVICE_STATE_RUNNING) {
        // 等待检测间隔
        vTaskDelay(pdMS_TO_TICKS(DETECTION_INTERVAL_MS));

        if (g_device_token[0] == '\0') {
            continue;
        }

        // 1. 拍摄照片
        uint8_t *image_buf = NULL;
        size_t image_len = 0;

        if (camera_capture(&image_buf, &image_len) != ESP_OK) {
            ESP_LOGW(TAG, "拍摄照片失败");
            continue;
        }

        // 2. 检查图像质量
        float quality_score = 0;
        if (!check_image_quality(image_buf, IMAGE_WIDTH, IMAGE_HEIGHT, &quality_score)) {
            ESP_LOGW(TAG, "图像质量不合格: %.2f", quality_score);
            camera_free_buf(image_buf);
            led_set_color(LED_COLOR_YELLOW);
            vTaskDelay(pdMS_TO_TICKS(500));
            led_off();
            continue;
        }

        // 3. 检测人脸
        face_detection_result_t faces[FACE_MAX_DETECTIONS];
        int face_count = detect_faces(image_buf, IMAGE_WIDTH, IMAGE_HEIGHT,
                                      faces, FACE_MAX_DETECTIONS);

        if (face_count > 0) {
            ESP_LOGI(TAG, "检测到 %d 个人脸", face_count);

            // 4. 尝试识别每个人脸
            for (int i = 0; i < face_count; i++) {
                led_set_color(LED_COLOR_BLUE);
                vTaskDelay(pdMS_TO_TICKS(200));

                // 上传到服务器进行识别
                cJSON *result = http_upload_image(image_buf, image_len, g_device_token);

                if (result) {
                    cJSON *matched = cJSON_GetObjectItem(result, "matched");
                    cJSON *member_name = cJSON_GetObjectItem(result, "member_name");
                    cJSON *confidence = cJSON_GetObjectItem(result, "confidence");

                    if (matched && cJSON_IsTrue(matched)) {
                        ESP_LOGI(TAG, "识别成功: %s, 置信度: %.2f",
                                 member_name ? member_name->valuestring : "未知",
                                 confidence ? confidence->valuedouble : 0);
                        led_set_color(LED_COLOR_GREEN);  // 绿灯表示家庭成员
                    } else {
                        ESP_LOGW(TAG, "陌生人或识别失败");
                        led_set_color(LED_COLOR_RED);  // 红灯表示陌生人
                    }
                    cJSON_Delete(result);
                }

                led_off();
                vTaskDelay(pdMS_TO_TICKS(500));
            }
        } else {
            ESP_LOGD(TAG, "未检测到人脸");
        }

        // 释放图像缓冲区
        camera_free_buf(image_buf);
    }

    ESP_LOGI(TAG, "人脸检测任务结束");
    vTaskDelete(NULL);
}

// 主循环任务
static void main_loop(void *pvParameters)
{
    ESP_LOGI(TAG, "开始主循环");

    while (1) {
        // LED 蓝色闪烁表示正在运行
        led_set_color(LED_COLOR_BLUE);
        vTaskDelay(pdMS_TO_TICKS(500));
        led_off();
        vTaskDelay(pdMS_TO_TICKS(2500));

        // 发送心跳
        if (g_device_state == DEVICE_STATE_RUNNING && g_device_token[0] != '\0') {
            http_send_heartbeat(g_device_token);
        }
    }
}

// 主程序入口
void app_main(void)
{
    ESP_LOGI(TAG, "===========================================");
    ESP_LOGI(TAG, "家庭监控智能助手 - ESP32-S3-EYE");
    ESP_LOGI(TAG, "固件版本: 1.0.0");
    ESP_LOGI(TAG, "===========================================");

    // 1. 硬件初始化
    ESP_ERROR_CHECK(hardware_init());

    // 2. WiFi 连接
    g_device_state = DEVICE_STATE_WIFI_CONNECTING;
    led_set_color(LED_COLOR_BLUE);

    wifi_init_sta();

    int retry = 0;
    while (!wifi_is_connected() && retry < 10) {
        ESP_LOGI(TAG, "等待 WiFi 连接... (%d/10)", retry + 1);
        vTaskDelay(pdMS_TO_TICKS(1000));
        retry++;
    }

    if (!wifi_is_connected()) {
        ESP_LOGE(TAG, "WiFi 连接失败!");
        g_device_state = DEVICE_STATE_ERROR;
        led_set_color(LED_COLOR_RED);
        return;
    }

    ESP_LOGI(TAG, "WiFi 连接成功");
    g_device_state = DEVICE_STATE_WIFI_CONNECTED;
    led_set_color(LED_COLOR_GREEN);
    vTaskDelay(pdMS_TO_TICKS(1000));

    // 3. 设备注册
    g_device_state = DEVICE_STATE_REGISTERING;
    led_set_color(LED_COLOR_BLUE);

    char *token = http_device_register(DEVICE_NAME);
    if (token) {
        strncpy(g_device_token, token, sizeof(g_device_token) - 1);
        ESP_LOGI(TAG, "设备注册成功, Token: %.32s...", g_device_token);
        free(token);
    } else {
        ESP_LOGE(TAG, "设备注册失败!");
        g_device_state = DEVICE_STATE_ERROR;
        led_set_color(LED_COLOR_RED);
        return;
    }

    // 4. 获取设备配置
    get_device_config();

    // 5. 初始化人脸检测
    if (face_detection_init() != ESP_OK) {
        ESP_LOGW(TAG, "人脸检测初始化失败，继续运行...");
    }

    // 6. 进入运行模式
    g_device_state = DEVICE_STATE_RUNNING;
    led_off();

    ESP_LOGI(TAG, "系统启动完成!");

    // 7. 创建主循环任务
    xTaskCreate(main_loop, "main_loop", 4096, NULL, 3, NULL);

    // 8. 创建人脸检测任务
    xTaskCreate(face_detection_task, "face_detection", 8192, NULL, 4, NULL);
}
