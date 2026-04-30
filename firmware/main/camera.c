#include <string.h>
#include "esp_log.h"
#include "esp_camera.h"
#include "camera.h"

static const char *TAG = "CAMERA";

// ESP32-S3-EYE 摄像头引脚定义
#define CAMERA_PIN_PWDN    -1  // 不用
#define CAMERA_PIN_RESET   -1  // 不用
#define CAMERA_PIN_XCLK    15
#define CAMERA_PIN_SIOD    4
#define CAMERA_PIN_SIOC    5

#define CAMERA_PIN_D7      16
#define CAMERA_PIN_D6      17
#define CAMERA_PIN_D5      18
#define CAMERA_PIN_D4      8
#define CAMERA_PIN_D3      19
#define CAMERA_PIN_D2      20
#define CAMERA_PIN_D1      21
#define CAMERA_PIN_D0      13

#define CAMERA_PIN_VSYNC   6
#define CAMERA_PIN_HREF    7
#define CAMERA_PIN_PCLK    14

static bool s_camera_initialized = false;

esp_err_t camera_init(void)
{
    if (s_camera_initialized) {
        ESP_LOGI(TAG, "Camera already initialized");
        return ESP_OK;
    }

    ESP_LOGI(TAG, "Initializing camera...");

    camera_config_t config = {
        .pin_pwdn = CAMERA_PIN_PWDN,
        .pin_reset = CAMERA_PIN_RESET,
        .pin_xclk = CAMERA_PIN_XCLK,
        .pin_sscb_sda = CAMERA_PIN_SIOD,
        .pin_sscb_scl = CAMERA_PIN_SIOC,

        .pin_d7 = CAMERA_PIN_D7,
        .pin_d6 = CAMERA_PIN_D6,
        .pin_d5 = CAMERA_PIN_D5,
        .pin_d4 = CAMERA_PIN_D4,
        .pin_d3 = CAMERA_PIN_D3,
        .pin_d2 = CAMERA_PIN_D2,
        .pin_d1 = CAMERA_PIN_D1,
        .pin_d0 = CAMERA_PIN_D0,

        .pin_vsync = CAMERA_PIN_VSYNC,
        .pin_href = CAMERA_PIN_HREF,
        .pin_pclk = CAMERA_PIN_PCLK,

        .xclk_freq_hz = 20000000,
        .ledc_timer = LEDC_TIMER_0,
        .ledc_channel = LEDC_CHANNEL_0,

        .pixel_format = PIXFORMAT_JPEG,
        .frame_size = FRAMESIZE_SVGA,

        .jpeg_quality = 12,
        .fb_count = 2,
        .grab_mode = CAMERA_GRAB_WHEN_EMPTY,
        .fb_location = CAMERA_FB_IN_PSRAM,
    };

    esp_err_t err = esp_camera_init(&config);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Camera init failed with error 0x%x", err);
        return err;
    }

    sensor_t *s = esp_camera_sensor_get();
    if (s != NULL) {
        // 调整摄像头设置
        s->set_brightness(s, 0);
        s->set_contrast(s, 0);
        s->set_saturation(s, 0);
        s->set_whitebal(s, 1);
        s->set_awb_gain(s, 1);
        s->set_wb_mode(s, 0);
        s->set_exposure_ctrl(s, 1);
        s->set_aec2(s, 0);
        s->set_ae_level(s, 0);
        s->set_aec_value(s, 200);
        s->set_gain_ctrl(s, 1);
        s->set_agc_gain(s, 0);
        s->set_gainceiling(s, (gainceiling_t)0);
        s->set_bpc(s, 0);
        s->set_wpc(s, 1);
        s->set_raw_gma(s, 1);
        s->set_lenc(s, 1);
        s->set_hmirror(s, 0);
        s->set_vflip(s, 0);
        s->set_dcw(s, 1);
        s->set_colorbar(s, 0);
    }

    s_camera_initialized = true;
    ESP_LOGI(TAG, "Camera initialized successfully");
    return ESP_OK;
}

esp_err_t camera_capture(uint8_t **out_buf, size_t *out_len)
{
    if (!s_camera_initialized) {
        ESP_LOGE(TAG, "Camera not initialized");
        return ESP_FAIL;
    }

    camera_fb_t *fb = esp_camera_fb_get();
    if (!fb) {
        ESP_LOGE(TAG, "Camera capture failed");
        return ESP_FAIL;
    }

    if (fb->format != PIXFORMAT_JPEG) {
        ESP_LOGE(TAG, "Non-JPEG format not supported");
        esp_camera_fb_return(fb);
        return ESP_FAIL;
    }

    *out_buf = fb->buf;
    *out_len = fb->len;

    // 注意: 使用完后需要调用 camera_free_buf 释放
    // 但这里我们直接返回fb指针，让调用者负责释放
    // 为了简化，我们复制一份数据

    uint8_t *copy = malloc(fb->len);
    if (copy) {
        memcpy(copy, fb->buf, fb->len);
    }

    esp_camera_fb_return(fb);

    if (!copy) {
        return ESP_ERR_NO_MEM;
    }

    *out_buf = copy;
    *out_len = fb->len;

    ESP_LOGD(TAG, "Captured %d bytes", *out_len);
    return ESP_OK;
}

void camera_free_buf(uint8_t *buf)
{
    if (buf) {
        free(buf);
    }
}

bool camera_is_ready(void)
{
    return s_camera_initialized;
}
