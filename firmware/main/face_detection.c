#include "face_detection.h"
#include "esp_log.h"
#include "esp_timer.h"
#include "esp_dl.hpp"
#include "dl_tool.hpp"
#include "face_recognition.hpp"
#include "image_util.h"

static const char *TAG = "FACE_DETECT";

// 人脸识别模型配置
// 请根据实际模型路径修改
#define FACE_MODEL_PATH "/models/face_detection_yunet.model"
#define FACE_RECOGNITION_MODEL_PATH "/models/face_recognition_sface.model"

static bool g_face_models_loaded = false;

// 简化的 Haar 级联分类器实现
// 实际项目中应使用 ESP-DL 的 YOLOX 或 Yunet 模型
typedef struct {
    int16_t scale_factor;
    int min_size;
    int max_size;
    float threshold;
} cascade_config_t;

static cascade_config_t cascade_config = {
    .scale_factor = 1.1f,
    .min_size = 40,
    .max_size = 300,
    .threshold = 0.5f
};

esp_err_t face_detection_init(void)
{
    ESP_LOGI(TAG, "初始化人脸检测模块...");

    // 检查 PSRAM 是否可用（ESP32-S3 有 PSRAM）
    if (esp_get_free_heap_size() < 200 * 1024) {
        ESP_LOGW(TAG, "可用内存不足，人脸检测可能受影响");
    }

    g_face_models_loaded = true;
    ESP_LOGI(TAG, "人脸检测模块初始化完成");

    return ESP_OK;
}

int detect_faces(uint8_t *image_data, int width, int height,
                 face_detection_result_t *results, int max_results)
{
    if (!g_face_models_loaded || !image_data || !results) {
        return 0;
    }

    int detected_count = 0;

    // 简化的检测实现
    // 实际项目中应使用 ESP-DL 的人脸检测模型
    ESP_LOGD(TAG, "开始人脸检测, 图像尺寸: %dx%d", width, height);

    // 模拟检测 - 实际应用中替换为真实的模型推理
    // 这里可以集成 ESP-DL 的 Yunet 或其他模型

    // 方法1: 使用 ESP-DL Yunet 模型 (推荐)
    // dl::Yunet face_detector;
    // auto detections = face_detector.detect(image_data, width, height);

    // 方法2: 使用简单的图像处理方法进行人脸区域估计
    // 通过灰度化和边缘检测来辅助判断

    // 目前返回 0 表示需要更完善的模型集成
    // 设备端负责采集图像，发送到后端进行人脸识别

    ESP_LOGD(TAG, "人脸检测完成, 检测到 %d 个人脸", detected_count);

    return detected_count;
}

esp_err_t crop_face_region(uint8_t *src_image, int src_width, int src_height,
                           const face_detection_result_t *face,
                           uint8_t *dst_image, int dst_width, int dst_height)
{
    if (!src_image || !dst_image || !face) {
        return ESP_ERR_INVALID_ARG;
    }

    // 扩展人脸区域以包含更多上下文
    int margin = face->w / 4;
    int crop_x = (face->x - margin > 0) ? face->x - margin : 0;
    int crop_y = (face->y - margin > 0) ? face->y - margin : 0;
    int crop_w = face->w + margin * 2;
    int crop_h = face->h + margin * 2;

    // 确保裁剪区域在图像范围内
    if (crop_x + crop_w > src_width) crop_w = src_width - crop_x;
    if (crop_y + crop_h > src_height) crop_h = src_height - crop_y;

    ESP_LOGD(TAG, "裁剪人脸区域: (%d,%d) %dx%d -> %dx%d",
             crop_x, crop_y, crop_w, crop_h, dst_width, dst_height);

    // 使用 image_util 进行图像缩放和裁剪
    uint8_t *cropped = (uint8_t *)malloc(crop_w * crop_h * 3);
    if (!cropped) {
        return ESP_ERR_NO_MEM;
    }

    // 复制原始区域
    for (int y = 0; y < crop_h; y++) {
        memcpy(cropped + y * crop_w * 3,
               src_image + (crop_y + y) * src_width * 3 + crop_x * 3,
               crop_w * 3);
    }

    // 缩放到目标尺寸
    uint16_t scale_w = crop_w * 256 / dst_width;
    uint16_t scale_h = crop_h * 256 / dst_height;

    for (int y = 0; y < dst_height; y++) {
        for (int x = 0; x < dst_width; x++) {
            int src_x = x * scale_w / 256;
            int src_y = y * scale_h / 256;
            src_x = (src_x >= crop_w) ? crop_w - 1 : src_x;
            src_y = (src_y >= crop_h) ? crop_h - 1 : src_y;

            memcpy(dst_image + (y * dst_width + x) * 3,
                   cropped + (src_y * crop_w + src_x) * 3,
                   3);
        }
    }

    free(cropped);
    return ESP_OK;
}

bool check_image_quality(uint8_t *image_data, int width, int height, float *quality_score)
{
    if (!image_data || !quality_score) {
        return false;
    }

    // 简单的图像质量评估
    // 1. 检查亮度
    uint32_t brightness_sum = 0;
    int pixel_count = width * height;

    for (int i = 0; i < pixel_count; i++) {
        uint8_t r = image_data[i * 3];
        uint8_t g = image_data[i * 3 + 1];
        uint8_t b = image_data[i * 3 + 2];
        // 计算亮度 (Y = 0.299R + 0.587G + 0.114B)
        brightness_sum += (77 * r + 150 * g + 29 * b) >> 8;
    }

    float avg_brightness = (float)brightness_sum / pixel_count;

    // 亮度应该在 60-200 之间
    float brightness_score = 1.0f;
    if (avg_brightness < 60) {
        brightness_score = avg_brightness / 60.0f;
    } else if (avg_brightness > 200) {
        brightness_score = 1.0f - (avg_brightness - 200) / 55.0f;
    }
    brightness_score = brightness_score < 0 ? 0 : brightness_score;

    // 2. 检查对比度
    uint32_t variance = 0;
    for (int i = 0; i < pixel_count; i++) {
        uint8_t gray = (image_data[i * 3] * 77 + image_data[i * 3 + 1] * 150 +
                        image_data[i * 3 + 2] * 29) >> 8;
        int diff = (int)gray - (int)avg_brightness;
        variance += diff * diff;
    }

    float contrast = (float)variance / pixel_count / 100.0f;
    float contrast_score = contrast > 1.0f ? 1.0f : contrast;

    // 综合评分
    *quality_score = (brightness_score * 0.6f + contrast_score * 0.4f);

    ESP_LOGD(TAG, "图像质量评估: 亮度=%.1f, 对比度=%.2f, 综合=%.2f",
             avg_brightness, contrast, *quality_score);

    return *quality_score >= FACE_QUALITY_THRESHOLD;
}
