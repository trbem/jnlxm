# ESP32-S3-EYE 固件

基于 ESP-IDF 的人脸识别家庭监控设备固件。

## 目录结构

```
src/
├── main.c              # 主程序入口
├── face_detect.c       # 人脸检测模块 (ESP-DL)
├── face_detect.h       # 人脸检测头文件
├── wifi_connect.c      # WiFi 连接模块
├── wifi_connect.h      # WiFi 连接头文件
├── http_client.c       # HTTP 客户端模块
├── http_client.h       # HTTP 客户端头文件
├── led_indicator.c    # LED 指示模块
├── led_indicator.h    # LED 指示头文件
└── config.h            # 配置文件
```

## 功能模块

1. **WiFi 连接**: 自动连接、掉线重连
2. **人脸检测**: ESP-DL 算法、图像质量评估
3. **数据上传**: HTTP POST 上传图片和特征向量
4. **LED 指示**: 绿=家人/红=陌生人/蓝=检测中

## 构建

需要 ESP-IDF 环境:

```bash
idf.py build
idf.py flash monitor
```

## 配置

在 `sdkconfig` 中配置:
- WiFi SSID/PASSWORD
- 服务器地址 API_URL
