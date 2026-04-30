#ifndef LED_INDICATOR_H
#define LED_INDICATOR_H

#include <stdint.h>
#include "freertos/FreeRTOS.h"

// LED 颜色枚举
typedef enum {
    LED_COLOR_OFF = -1,
    LED_COLOR_GREEN = 0,
    LED_COLOR_RED = 1,
    LED_COLOR_BLUE = 2,
    LED_COLOR_WHITE = 3
} led_color_t;

// 初始化 LED GPIO
void led_init(void);

// 设置 LED 颜色
void led_set_color(led_color_t color);

// 关闭所有 LED
void led_off(void);

// LED 闪烁效果
void led_blink(led_color_t color, uint32_t interval_ms, uint8_t times);

#endif // LED_INDICATOR_H
