#ifndef HTTP_CLIENT_H
#define HTTP_CLIENT_H

#include <stddef.h>
#include "esp_err.h"
#include "cJSON.h"

// 设备注册
char* http_device_register(const char *device_name);

// 发送心跳
esp_err_t http_send_heartbeat(const char *device_token);

// 上传图片进行识别
cJSON* http_upload_image(uint8_t *image_data, size_t image_len, const char *device_token);

// 获取设备配置
cJSON* http_get_config(void);

#endif // HTTP_CLIENT_H
