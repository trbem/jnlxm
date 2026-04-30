#ifndef CAMERA_H
#define CAMERA_H

#include "esp_err.h"

// 摄像头初始化
esp_err_t camera_init(void);

// 拍摄一张照片
esp_err_t camera_capture(uint8_t **out_buf, size_t *out_len);

// 释放图片缓冲区
void camera_free_buf(uint8_t *buf);

// 获取摄像头状态
bool camera_is_ready(void);

#endif // CAMERA_H
