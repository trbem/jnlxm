#include <driver/gpio.h>
#include "esp_log.h"
#include "led_indicator.h"
#include "config.h"

static const char *TAG = "LED";

// LED GPIO 引脚定义
static gpio_num_t led_pins[3] = {
    LED_GREEN_PIN,  // 索引 0: 绿色
    LED_RED_PIN,     // 索引 1: 红色
    LED_BLUE_PIN     // 索引 2: 蓝色
};

// 当前 LED 状态
static int8_t current_color = -1;

// 初始化 LED GPIO
void led_init(void)
{
    ESP_LOGI(TAG, "初始化 LED GPIO");

    gpio_config_t io_conf = {
        .pin_bit_mask = (1ULL << LED_GREEN_PIN) | (1ULL << LED_RED_PIN) | (1ULL << LED_BLUE_PIN),
        .mode = GPIO_MODE_OUTPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };

    gpio_config(&io_conf);

    // 关闭所有 LED
    gpio_set_level(LED_GREEN_PIN, 0);
    gpio_set_level(LED_RED_PIN, 0);
    gpio_set_level(LED_BLUE_PIN, 0);

    ESP_LOGI(TAG, "LED 初始化完成");
}

// 设置 LED 颜色
void led_set_color(led_color_t color)
{
    if (color == current_color) {
        return;
    }

    // 先关闭所有 LED
    gpio_set_level(LED_GREEN_PIN, 0);
    gpio_set_level(LED_RED_PIN, 0);
    gpio_set_level(LED_BLUE_PIN, 0);

    // 设置新颜色
    switch (color) {
    case LED_COLOR_GREEN:
        gpio_set_level(LED_GREEN_PIN, 1);
        ESP_LOGI(TAG, "LED: 绿色 (家庭成员)");
        break;
    case LED_COLOR_RED:
        gpio_set_level(LED_RED_PIN, 1);
        ESP_LOGI(TAG, "LED: 红色 (陌生人)");
        break;
    case LED_COLOR_BLUE:
        gpio_set_level(LED_BLUE_PIN, 1);
        ESP_LOGI(TAG, "LED: 蓝色 (检测中)");
        break;
    case LED_COLOR_WHITE:
        gpio_set_level(LED_GREEN_PIN, 1);
        gpio_set_level(LED_RED_PIN, 1);
        gpio_set_level(LED_BLUE_PIN, 1);
        ESP_LOGI(TAG, "LED: 白色");
        break;
    case LED_COLOR_OFF:
    default:
        ESP_LOGI(TAG, "LED: 关闭");
        break;
    }

    current_color = color;
}

// 关闭所有 LED
void led_off(void)
{
    led_set_color(LED_COLOR_OFF);
}

// LED 闪烁效果
void led_blink(led_color_t color, uint32_t interval_ms, uint8_t times)
{
    for (uint8_t i = 0; i < times; i++) {
        led_set_color(color);
        vTaskDelay(pdMS_TO_TICKS(interval_ms / 2));
        led_off();
        vTaskDelay(pdMS_TO_TICKS(interval_ms / 2));
    }
}
