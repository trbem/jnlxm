#ifndef WIFI_CONNECT_H
#define WIFI_CONNECT_H

#include "esp_err.h"
#include "stdbool.h"

// 初始化 WiFi 为 Station 模式
esp_err_t wifi_init_sta(void);

// 检查 WiFi 是否已连接
bool wifi_is_connected(void);

// 获取 WiFi 信号强度 (RSSI)
int8_t wifi_get_rssi(void);

#endif // WIFI_CONNECT_H
