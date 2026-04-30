# ESP32-S3-Eye 智能家庭助手 - 固件需求规格说明书

## 一、总体要求

### 1.1 开发环境
| 项目 | 要求 |
|------|------|
| 开发框架 | ESP-IDF v5.4+ |
| 目标芯片 | ESP32-S3 |
| 编译器 | xtensa-esp32s3-elf-gcc |
| 构建系统 | CMake |

### 1.2 固件功能概述
固件需要实现以下核心功能：
1. **Wi-Fi连接管理** - 自动连接预设Wi-Fi
2. **语音交互** - 录音、上传、播放AI回复
3. **图像采集** - 拍照、压缩、上传
4. **LCD显示** - 多状态界面切换
5. **按键处理** - 长按录音、双击拍照
6. **HTTP通信** - 与PC端服务器数据交换
7. **会话管理** - 维护session_id保持上下文

---

## 二、硬件引脚配置需求

### 2.1 ESP32-S3-Eye引脚分配

```c
// pins.h - 引脚定义文件
typedef struct {
    // ===== Wi-Fi =====
    // 内部WiFi，无需配置
    
    // ===== PDM麦克风 (I2S接口) =====
    int i2s_ws_pin;      // GPIO47 - Word Select
    int i2s_bclk_pin;    // GPIO45 - Bit Clock
    
    // ===== ST7789 LCD (SPI接口) =====
    int lcd_mosi_pin;    // GPIO07 - Master Out Slave In
    int lcd_sclk_pin;    // GPIO06 - Serial Clock
    int lcd_cs_pin;      // GPIO05 - Chip Select
    int lcd_dc_pin;      // GPIO05 - Data Command
    int lcd_rst_pin;     // GPIO48 - Reset
    int lcd_bl_pin;      // GPIO38 - Backlight
    
    // ===== 摄像头 (SPI/Camera接口) =====
    int cam_pwdn_pin;    // GPIO01 - PWDN (-1 if not used)
    int cam_reset_pin;   // GPIO02 - RESET
    int cam_xclk_pin;    // GPIO10 - XCLK
    int cam_sda_pin;     // GPIO11 - SDA (SCCB)
    int cam_scl_pin;     // GPIO12 - SCL (SCCB)
    int cam_d0_pin;      // GPIO13 - Data0
    int cam_d1_pin;      // GPIO14 - Data1
    int cam_d2_pin;      // GPIO15 - Data2
    int cam_d3_pin;      // GPIO16 - Data3
    int cam_d4_pin;      // GPIO17 - Data4
    int cam_d5_pin;      // GPIO18 - Data5
    int cam_d6_pin;      // GPIO19 - Data6
    int cam_d7_pin;      // GPIO20 - Data7
    int cam_vsync_pin;   // GPIO39 - VSYNC
    int cam_href_pin;    // GPIO40 - HREF
    int cam_pclk_pin;    // GPIO41 - PCLK
    
    // ===== 按键 =====
    int button_record_pin;   // GPIO0 - BOOT按钮（长按录音）
    
    // ===== LED指示 =====
    int led_pin;             // GPIO1 - 状态指示LED
    
    // ===== 其他（可选） =====
    int sd_card_mosi_pin;    // GPIO42 - SD卡MOSI
    int sd_card_sclk_pin;    // GPIO43 - SD卡SCLK
    int sd_card_cs_pin;      // GPIO44 - SD卡CS
    int sd_card_miso_pin;    // GPIO45 - SD卡MISO
    
    // ===== 外部传感器（I2C，可选） =====
    int sensor_sda_pin;      // GPIO08 - I2C SDA
    int sensor_scl_pin;      // GPIO09 - I2C SCL
} pin_config_t;
```

**注意**：具体引脚号需要根据ESP32-S3-Eye实际硬件原理图确认，以上为典型配置。

---

## 三、模块详细需求

### 3.1 Wi-Fi管理模块 (`wifi_manager/`)

#### 功能需求
| 功能 | 描述 |
|------|------|
| 自动连接 | 启动时自动连接预设Wi-Fi |
| 重连机制 | 断线后自动重连（最多3次） |
| 状态指示 | LED闪烁表示连接状态 |
| IP获取 | 支持DHCP自动获取IP |

#### 接口定义
```c
// wifi_manager.h
typedef struct {
    const char *ssid;
    const char *password;
    uint8_t max_retries;
} wifi_config_t;

// 初始化Wi-Fi管理
int wifi_init(wifi_config_t *config);

// 获取连接状态
bool wifi_is_connected(void);

// 获取IP地址
const char* wifi_get_ip(void);

// 获取本地IP字符串
void wifi_get_local_ip(char *ip_buffer, size_t len);
```

#### 配置参数
```c
// sdkconfig或Kconfig配置
CONFIG_WIFI_SSID="431"
CONFIG_WIFI_PASSWORD="88888888"
CONFIG_WIFI_MAX_RETRIES=3
CONFIG_WIFI_WAIT_TIMEOUT_MS=10000
```

---

### 3.2 音频录制模块 (`audio/`)

#### 功能需求
| 功能 | 描述 |
|------|------|
| PDM麦克风 | 通过I2S接口读取PDM麦克风数据 |
| WAV编码 | 实时编码为WAV格式（16kHz, 16bit, 单声道） |
| 定时录制 | 支持最长10秒录制 |
| 音频缓冲 | 使用环形缓冲区避免数据丢失 |

#### 接口定义
```c
// audio_record.h
typedef struct {
    uint32_t sample_rate;      // 采样率 (16000 Hz)
    int bits_per_sample;       // 位深 (16 bit)
    int channels;              // 声道数 (1 单声道)
    int max_duration_ms;       // 最大录制时长 (10000 ms)
    int i2s_ws_pin;
    int i2s_bclk_pin;
    int i2s_sd_pin;            // 如果不同
} audio_config_t;

typedef struct {
    void *data;                // 音频数据指针
    size_t length;             // 数据长度
    uint32_t sample_rate;      // 采样率
    uint16_t bits_per_sample;  // 位深
    uint8_t channels;          // 声道数
} audio_buffer_t;

// 初始化音频录制
int audio_init(audio_config_t *config);

// 开始录制
int audio_start_record(void);

// 停止录制，返回音频数据
audio_buffer_t* audio_stop_record(void);

// 释放音频数据
void audio_free_buffer(audio_buffer_t *buffer);

// 检查是否在录制
bool audio_is_recording(void);
```

#### 音频格式要求
```
WAV文件格式：
- 采样率: 16000 Hz
- 位深: 16 bit (2 bytes per sample)
- 声道: 单声道 (1 channel)
- 数据格式: 小端序 (Little Endian)
- WAV头部: 44 bytes (standard RIFF WAV header)

WAV头部结构:
Bytes 0-3:   "RIFF"
Bytes 4-7:   文件总长度 (little-endian)
Bytes 8-11:  "WAVE"
Bytes 12-15: "fmt "
Bytes 16-19: 16 (fmt chunk size)
Bytes 20-21: 1 (PCM format)
Bytes 22-23: 1 (mono)
Bytes 24-27: 16000 (sample rate)
Bytes 28-31: 32000 (byte rate = sr * channels * bits/8)
Bytes 32-33: 2 (block align = channels * bits/8)
Bytes 34-35: 16 (bits per sample)
Bytes 36-39: "data"
Bytes 40-43: 数据长度 (little-endian)
Bytes 44+:   音频数据
```

---

### 3.3 图像采集模块 (`image_capture/`) - 新增

#### 功能需求
| 功能 | 描述 |
|------|------|
| 摄像头驱动 | 支持OV2640摄像头 |
| 图像格式 | 输出JPEG格式（硬件压缩） |
| 分辨率可选 | 支持QVGA(320x240)、VGA(640x480) |
| 质量调节 | JPEG质量可配置(1-10) |

#### 接口定义
```c
// image_capture.h
typedef struct {
    int xclk_pin;
    int pwdn_pin;
    int reset_pin;
    int sda_pin;
    int scl_pin;
    int d0_pin;
    int d1_pin;
    int d2_pin;
    int d3_pin;
    int d4_pin;
    int d5_pin;
    int d6_pin;
    int d7_pin;
    int vsync_pin;
    int href_pin;
    int pclk_pin;
    
    uint16_t width;        // 图像宽度 (320 or 640)
    uint16_t height;       // 图像高度 (240 or 480)
    uint8_t quality;       // JPEG质量 (1-10, 10最佳)
} camera_config_t;

typedef struct {
    void *data;             // JPEG数据指针
    size_t length;          // 数据长度
    uint16_t width;         // 图像宽度
    uint16_t height;        // 图像高度
} image_buffer_t;

// 初始化摄像头
int camera_init(camera_config_t *config);

// 拍摄照片
image_buffer_t* camera_capture(void);

// 释放图像数据
void camera_free_buffer(image_buffer_t *buffer);

// 设置图像质量
int camera_set_quality(uint8_t quality);

// 设置分辨率
int camera_set_resolution(uint16_t width, uint16_t height);
```

#### 内存管理要求
```
- JPEG输出缓冲区: 最大约64KB (VGA质量8)
- 使用ESP32的PSRAM（如果有）存储图像数据
- 拍摄后立即释放缓冲区，避免内存泄漏
```

---

### 3.4 LCD显示模块 (`lcd_display/`)

#### 功能需求
| 功能 | 描述 |
|------|------|
| SPI接口 | 驱动ST7789 LCD |
| 分辨率 | 160x80 (或128x128，根据实际面板) |
| 多状态界面 | 待机、录音、思考、显示结果等 |
| 文字显示 | 中文/英文显示 |
| 图标显示 | Wi-Fi、麦克风、LED状态图标 |
| 背光控制 | 可调节背光亮度 |

#### 接口定义
```c
// lcd_display.h
typedef enum {
    STATE_IDLE,           // 待机状态
    STATE_RECORDING,      // 录音中
    STATE_UPLOADING,      // 上传中
    STATE_THINKING,       // 思考中
    STATE_DISPLAY_RESULT, // 显示结果
    STATE_PHOTO_READY,    // 拍照完成
    STATE_ERROR           // 错误状态
} display_state_t;

// 初始化LCD
int lcd_init(int mosi_pin, int sclk_pin, int cs_pin, 
             int dc_pin, int rst_pin, int bl_pin);

// 清屏
void lcd_clear(uint16_t color);

// 显示文字
void lcd_print(int x, int y, const char *text, uint16_t color);

// 显示中文（需要字库）
void lcd_print_chinese(int x, int y, const char *chinese_text, uint16_t color);

// 绘制矩形
void lcd_draw_rect(int x, int y, int width, int height, 
                   uint16_t color, bool fill);

// 设置背光
void lcd_set_backlight(uint8_t brightness);  // 0-255

// 切换状态
void lcd_set_state(display_state_t state);

// 显示特定状态界面
void lcd_show_idle_screen(void);
void lcd_show_recording_screen(void);
void lcd_show_thinking_screen(void);
void lcd_show_result_screen(const char *text);
void lcd_show_error_screen(const char *error_msg);

// 刷新显示
void lcd_refresh(void);

// 关闭背光
void lcd_turn_off_backlight(void);
```

#### 状态界面设计
```
1. 待机界面 (STATE_IDLE):
   ┌────────────────────────┐
   │  ┌──┐                   │
   │  │W│  已连接: 431       │
   │  └──┘  IP: 10.x.x.x    │
   │                        │
   │   [麦克风图标]          │
   │   按住按钮说话          │
   └────────────────────────┘

2. 录音界面 (STATE_RECORDING):
   ┌────────────────────────┐
   │     正在录音...         │
   │                        │
   │   ▂▃▅▇▅▃▂              │  // 音频波形动画
   │   ▃▅▇▅▃▅▇              │
   │   ▅▇▅▃▇▅▃              │
   │                        │
   └────────────────────────┘

3. 思考界面 (STATE_THINKING):
   ┌────────────────────────┐
   │     思考中...           │
   │                        │
   │   ● ○ ○                │  // 旋转动画
   │   ○ ● ○                │
   │   ○ ○ ●                │
   │                        │
   └────────────────────────┘

4. 结果显示界面 (STATE_DISPLAY_RESULT):
   ┌────────────────────────┐
   │  AI回复内容...          │
   │  这里显示多行文字       │
   │  最多显示5行            │
   └────────────────────────┘

5. 拍照界面 (STATE_PHOTO_READY):
   ┌────────────────────────┐
   │  📷 图片已识别          │
   │  描述: 客厅,无人        │
   └────────────────────────┘
```

---

### 3.5 按键处理模块 (`button/`)

#### 功能需求
| 功能 | 描述 |
|------|------|
| 长按检测 | 长按>1秒开始录音 |
| 释放检测 | 释放按钮停止录音并发送 |
| 双击检测 | 双击按钮触发拍照 |
| 防抖处理 | 软件防抖（50ms） |

#### 接口定义
```c
// button.h
typedef enum {
    BUTTON_NONE,
    BUTTON_SHORT_PRESS,    // 短按（单击）
    BUTTON_LONG_PRESS,     // 长按
    BUTTON_DOUBLE_PRESS    // 双击
} button_event_t;

typedef void (*button_callback_t)(button_event_t event);

// 初始化按键
int button_init(int pin);

// 注册回调函数
void button_register_callback(button_callback_t callback);

// 更新按键状态（需在主循环调用）
void button_update(void);

// 获取当前按键事件
button_event_t button_get_event(void);

// 清除事件
void button_clear_event(void);
```

#### 按键事件时序
```
短按:  按下(50ms防抖) → 释放 → 判定为短按
长按:  按下(>1000ms) → 触发长按事件 → 释放
双击:  短按 → 间隔<500ms → 短按 → 判定为双击
```

---

### 3.6 HTTP通信模块 (`http_client/`)

#### 功能需求
| 功能 | 描述 |
|------|------|
| POST请求 | 发送JSON+Base64数据到服务器 |
| 超时处理 | 连接超时5秒，读取超时90秒 |
| 错误处理 | 网络错误、服务器错误 |
| Session管理 | 维护session_id |

#### 接口定义
```c
// http_client.h
typedef struct {
    const char *server_ip;    // 服务器IP
    int server_port;          // 服务器端口 (8000 or 8082)
    const char *session_id;   // 会话ID
} http_config_t;

typedef struct {
    const char *response;     // 响应内容
    int http_code;            // HTTP状态码
    float time_elapsed;       // 耗时(秒)
} http_response_t;

// 初始化HTTP客户端
int http_init(http_config_t *config);

// 发送语音请求
// audio_base64: Base64编码的WAV音频
// 返回: http_response_t (需要调用者free)
http_response_t* http_send_voice(const char *audio_base64);

// 发送图像请求
// image_base64: Base64编码的JPEG图像
// prompt: 提示词（可选，NULL使用默认）
http_response_t* http_send_image(const char *image_base64, const char *prompt);

// 发送文字对话
// message: 用户消息
http_response_t* http_send_chat(const char *message);

// 清除会话历史
http_response_t* http_clear_history(void);

// 解析语音响应
// 返回: response_text 和 response_audio_base64
typedef struct {
    char *response;           // AI回复文字
    char *audio_base64;       // TTS音频Base64
    char *session_id;         // 会话ID
    float time;               // 耗时
} voice_response_parse_t;

voice_response_parse_t* http_parse_voice_response(const char *json);

// 解析图像响应
typedef struct {
    char *response;
    char *session_id;
    float time;
} image_response_parse_t;

image_response_parse_t* http_parse_image_response(const char *json);

// 释放响应内存
void http_free_response(http_response_t *response);
void http_free_voice_response(voice_response_parse_t *parse);
void http_free_image_response(image_response_parse_t *parse);
```

#### JSON格式示例
```json
// 请求 - 语音
{
    "audio_base64": "UklGRiQAAABXQVZFZm10IBAAAAABAAEARKwAAIhYAQACABAAZGF0YQAAAAA=",
    "session_id": "device_001"
}

// 响应 - 语音
{
    "response": "这是客厅的监控画面，目前没有人在家。",
    "audio_base64": "SUQzBAAAAAAAI1RTU0UAAAAPAAADTGF2ZjU4Ljc2LjEwMA==",
    "session_id": "device_001",
    "time": 3.5
}

// 请求 - 图像
{
    "image_base64": "/9j/4AAQSkZJRg...",
    "session_id": "device_001",
    "prompt": "请描述这张图片的内容"
}

// 响应 - 图像
{
    "response": "这是一张客厅的照片，可以看到沙发、电视和窗户。",
    "session_id": "device_001",
    "time": 5.2
}
```

---

### 3.7 Base64编解码模块 (`base64/`)

#### 功能需求
| 功能 | 描述 |
|------|------|
| 编码 | 二进制数据转Base64字符串 |
| 解码 | Base64字符串转二进制数据 |
| 内存优化 | 使用缓冲区避免频繁分配 |

#### 接口定义
```c
// base64.h
// 编码: 返回需要free的字符串
char* base64_encode(const uint8_t *data, size_t length);

// 解码: 返回需要free的内存
uint8_t* base64_decode(const char *input, size_t *output_length);

// 计算Base64输出长度
size_t base64_encoded_length(size_t input_length);
```

---

### 3.8 会话管理模块 (`session/`)

#### 功能需求
| 功能 | 描述 |
|------|------|
| Session ID生成 | 设备唯一ID |
| 持久化存储 | NVS保存，重启不丢失 |

#### 接口定义
```c
// session.h
// 初始化会话管理
int session_init(void);

// 获取session ID
const char* session_get_id(void);

// 清除会话历史（可选，调用服务器API）
int session_clear_history(void);
```

---

## 四、主程序流程 (`main/main.c`)

### 4.1 初始化流程
```c
// main.c - 主程序入口
void app_main(void)
{
    // 1. 初始化NVS
    nvs_flash_init();
    
    // 2. 初始化引脚配置
    pin_config_t pins = DEFAULT_PINS;
    
    // 3. 初始化Wi-Fi
    wifi_config_t wifi = {
        .ssid = "431",
        .password = "88888888"
    };
    wifi_init(&wifi);
    
    // 等待连接成功
    while (!wifi_is_connected()) {
        vTaskDelay(pdMS_TO_TICKS(100));
    }
    
    // 4. 初始化LCD
    lcd_init(pins.lcd_mosi_pin, ...);
    lcd_show_idle_screen();
    
    // 5. 初始化音频
    audio_config_t audio = {
        .sample_rate = 16000,
        .bits_per_sample = 16,
        .channels = 1,
        .max_duration_ms = 10000
    };
    audio_init(&audio);
    
    // 6. 初始化摄像头
    camera_config_t cam = {
        .width = 640,
        .height = 480,
        .quality = 8
    };
    camera_init(&cam);
    
    // 7. 初始化按键
    button_init(pins.button_record_pin);
    button_register_callback(button_event_handler);
    
    // 8. 初始化HTTP客户端
    http_config_t http = {
        .server_ip = "10.1.41.99",
        .server_port = 8000,
        .session_id = session_get_id()
    };
    http_init(&http);
    
    // 9. 主循环
    while (1) {
        button_update();
        
        button_event_t event = button_get_event();
        
        switch (event) {
            case BUTTON_LONG_PRESS:
                // 长按: 录音 → 上传 → 等待回复 → 显示/播放
                handle_voice_interaction();
                break;
                
            case BUTTON_DOUBLE_PRESS:
                // 双击: 拍照 → 上传 → 等待结果 → 显示
                handle_photo_capture();
                break;
                
            default:
                break;
        }
        
        vTaskDelay(pdMS_TO_TICKS(50));
    }
}
```

### 4.2 语音交互流程
```c
static void handle_voice_interaction(void)
{
    // 1. 显示录音界面
    lcd_set_state(STATE_RECORDING);
    lcd_show_recording_screen();
    
    // 2. 开始录音
    audio_start_record();
    
    // 3. 等待释放按钮
    while (audio_is_recording()) {
        button_update();
        if (button_get_event() == BUTTON_NONE) {
            vTaskDelay(pdMS_TO_TICKS(10));
        }
    }
    
    // 4. 停止录音，获取音频数据
    audio_buffer_t *audio = audio_stop_record();
    
    // 5. 显示上传中
    lcd_set_state(STATE_UPLOADING);
    lcd_print(0, 0, "上传中...", COLOR_BLACK);
    
    // 6. Base64编码
    char *audio_b64 = base64_encode(audio->data, audio->length);
    
    // 7. 发送到服务器
    http_response_t *resp = http_send_voice(audio_b64);
    
    // 8. 释放音频数据
    audio_free_buffer(audio);
    free(audio_b64);
    
    // 9. 解析响应
    voice_response_parse_t *parse = http_parse_voice_response(resp->response);
    http_free_response(resp);
    
    // 10. 显示结果
    lcd_set_state(STATE_DISPLAY_RESULT);
    lcd_show_result_screen(parse->response);
    
    // 11. 播放音频（如果有）
    if (parse->audio_base64) {
        // TODO: 实现I2S DAC播放音频
        // play_audio(parse->audio_base64);
    }
    
    http_free_voice_response(parse);
}
```

### 4.3 拍照识别流程
```c
static void handle_photo_capture(void)
{
    // 1. 显示拍照中
    lcd_set_state(STATE_THINKING);
    lcd_show_thinking_screen();
    
    // 2. 拍摄照片
    image_buffer_t *image = camera_capture();
    
    // 3. Base64编码
    char *image_b64 = base64_encode(image->data, image->length);
    
    // 4. 释放图像数据
    camera_free_buffer(image);
    
    // 5. 发送到服务器
    http_response_t *resp = http_send_image(image_b64, "请描述这张图片的内容");
    
    // 6. 释放Base64
    free(image_b64);
    
    // 7. 解析响应
    image_response_parse_t *parse = http_parse_image_response(resp->response);
    http_free_response(resp);
    
    // 8. 显示结果
    lcd_set_state(STATE_DISPLAY_RESULT);
    lcd_show_result_screen(parse->response);
    
    http_free_image_response(parse);
}
```

---

## 五、内存与性能要求

### 5.1 内存使用估算
```
栈内存 (Task Stack):
- 主任务: 8KB
- 各子模块: 2-4KB

堆内存 (Heap):
- 音频缓冲: 64KB (10秒 @ 16kHz 16bit mono)
- 图像缓冲: 64KB (VGA JPEG Q8)
- Base64编码: 约原始大小 * 4/3
- HTTP缓冲: 32KB

PSRAM (如果可用):
- 图像存储: 额外64KB
- 音频缓存: 额外32KB
```

### 5.2 性能指标
```
- 录音延迟: < 100ms
- 拍照时间: < 500ms
- 图像上传 (64KB): < 3秒 (Wi-Fi良好)
- AI响应时间: 3-10秒 (取决于服务器)
- LCD刷新: < 100ms
```

---

## 六、错误处理要求

### 6.1 错误类型及处理
```c
// errors.h
typedef enum {
    ERROR_NONE = 0,
    ERROR_WIFI_CONNECT,       // Wi-Fi连接失败
    ERROR_WIFI_TIMEOUT,       // Wi-Fi连接超时
    ERROR_CAMERA_INIT,        // 摄像头初始化失败
    ERROR_AUDIO_INIT,         // 音频初始化失败
    ERROR_LCD_INIT,           // LCD初始化失败
    ERROR_HTTP_SERVER,        // 服务器连接失败
    ERROR_HTTP_TIMEOUT,       // HTTP请求超时
    ERROR_HTTP_SERVER_ERROR,  // 服务器错误
    ERROR_MEMORY,             // 内存不足
    ERROR_AUDIO_RECORD,       // 录音失败
    ERROR_CAMERA_CAPTURE,     // 拍照失败
    ERROR_BASE64,             // Base64编码失败
    ERROR_UNKNOWN             // 未知错误
} error_code_t;

// 错误处理函数
void error_handle(error_code_t error);
void error_show_message(const char *message);
void error_blink_led(int times);
```

### 6.2 LED状态指示
```
- 常亮: 正常运行
- 慢闪 (1Hz): 待机
- 快闪 (3Hz): 录音中
- 双闪 (2Hz): 上传中
- 快闪 (5Hz): 思考中
- 常亮2秒灭1秒: 错误
- 快速连续闪: 严重错误（需要重启）
```

---

## 七、配置文件 (sdkconfig)

```
# Wi-Fi配置
CONFIG_WIFI_SSID="431"
CONFIG_WIFI_PASSWORD="88888888"
CONFIG_WIFI_MAX_RETRIES=3

# 服务器配置
CONFIG_SERVER_IP="10.1.41.99"
CONFIG_SERVER_PORT=8000
CONFIG_SESSION_ID="device_001"

# 音频配置
CONFIG_AUDIO_SAMPLE_RATE=16000
CONFIG_AUDIO_BITS=16
CONFIG_AUDIO_CHANNELS=1
CONFIG_AUDIO_MAX_DURATION=10000

# 摄像头配置
CONFIG_CAMERA_WIDTH=640
CONFIG_CAMERA_HEIGHT=480
CONFIG_CAMERA_QUALITY=8

# LCD配置
CONFIG_LCD_WIDTH=160
CONFIG_LCD_HEIGHT=80

# HTTP超时配置
CONFIG_HTTP_CONNECT_TIMEOUT=5000
CONFIG_HTTP_READ_TIMEOUT=90000

# 按键配置
CONFIG_BUTTON_LONG_PRESS_MS=1000
CONFIG_BUTTON_DEBOUNCE_MS=50
```

---

## 八、文件结构

```
esp32-s3-eye-firmware/
├── CMakeLists.txt              # 项目构建文件
├── partitions.csv              # 分区表
├── sdkconfig.defaults          # 默认配置
├── README.md                   # 说明文档
│
├── main/
│   ├── CMakeLists.txt
│   ├── main.c                  # 主程序入口
│   ├── pins.h                  # 引脚定义
│   ├── app_state.c             # 应用状态管理
│   └── app_state.h
│
├── components/
│   ├── wifi_manager/           # Wi-Fi管理 (已有)
│   │   ├── CMakeLists.txt
│   │   ├── wifi_manager.c
│   │   └── wifi_manager.h
│   │
│   ├── audio/                  # 音频录制 (已有)
│   │   ├── CMakeLists.txt
│   │   ├── audio_record.c
│   │   └── audio_record.h
│   │
│   ├── lcd/                    # LCD显示 (已有)
│   │   ├── CMakeLists.txt
│   │   ├── lcd_display.c
│   │   └── lcd_display.h
│   │
│   ├── ui/                     # UI组件 (已有)
│   │   ├── CMakeLists.txt
│   │   └── ui_text.c
│   │
│   ├── session/                # 会话管理 (已有)
│   │   ├── CMakeLists.txt
│   │   └── session.c
│   │
│   ├── image_capture/          # 新增: 图像采集
│   │   ├── CMakeLists.txt
│   │   ├── camera_driver.c
│   │   └── camera_driver.h
│   │
│   ├── http_client/            # 新增: HTTP通信
│   │   ├── CMakeLists.txt
│   │   ├── http_client.c
│   │   └── http_client.h
│   │
│   ├── base64/                 # 新增: Base64编解码
│   │   ├── CMakeLists.txt
│   │   ├── base64.c
│   │   └── base64.h
│   │
│   └── button/                 # 新增: 按键处理
│       ├── CMakeLists.txt
│       ├── button.c
│       └── button.h
│
└── main_app/                   # 新增: 主应用逻辑
    ├── CMakeLists.txt
    ├── voice_interaction.c     # 语音交互流程
    ├── photo_capture.c         # 拍照识别流程
    └── state_machine.c         # 状态机
```

---

## 九、开发阶段规划

### 第一阶段：基础整合（1-2周）
- [ ] 第1步：整合ESP32-S3-Eye摄像头驱动
  - 测试摄像头拍照功能
  - 实现JPEG图像采集和压缩
- [ ] 第2步：扩展Server端API
  - 实现`/api/image`接口
  - 测试图像上传和识别
- [ ] 第3步：ESP32 → Server图像传输
  - 实现HTTP POST上传图片
  - 调试网络传输稳定性

### 第二阶段：功能完善（2-3周）
- [ ] 第4步：UI状态机设计
  - 设计待机、录音、思考、显示等状态
  - 实现LCD界面切换
- [ ] 第5步：语音触发拍照
  - 集成语音识别结果判断
  - 实现"拍照"指令触发
- [ ] 第6步：多模态对话
  - 支持"看图+对话"模式
  - 会话历史统一管理

### 第三阶段：扩展功能（2-3周）
- [ ] 第7步：传感器集成
  - 接入DHT11温湿度显示
  - 添加异常报警功能
- [ ] 第8步：MQTT支持（可选）
  - 实现双向通信
  - 支持远程指令下发
- [ ] 第9步：Web管理界面
  - 设备配置管理
  - 历史图片浏览
  - 对话记录查看

### 第四阶段：优化与封装（1-2周）
- [ ] 第10步：性能优化
  - 图像传输压缩优化
  - 内存管理优化
- [ ] 第11步：外壳设计与3D打印
- [ ] 第12步：文档整理与发布

---

## 十、预算汇总

### 最低配置（核心功能）
| 材料 | 预估价格 |
|------|---------|
| ESP32-S3-Eye开发板 | ¥100 |
| USB数据线 | ¥15 |
| **总计** | **约¥115** |

### 推荐配置（完整功能）
| 材料 | 预估价格 |
|------|---------|
| ESP32-S3-Eye开发板 | ¥100 |
| USB数据线 | ¥15 |
| OV2640摄像头 | ¥20 |
| SD卡模块 | ¥8 |
| 传感器套件（DHT11、舵机、蜂鸣器、LED） | ¥36 |
| 面包板+杜邦线 | ¥25 |
| **总计** | **约¥224** |

### 完美配置（含外壳）
| 材料 | 预估价格 |
|------|---------|
| 推荐配置 | ¥224 |
| 3D打印外壳 | ¥40 |
| 亚克力面板 | ¥15 |
| **总计** | **约¥280** |

---

## 十一、风险与注意事项

1. **ESP32-S3-Eye摄像头兼容性**：需确认板载摄像头接口是否支持OV2640
2. **内存限制**：ESP32-S3有4MB OSPI RAM，图像处理需注意内存管理
3. **网络稳定性**：建议固定PC端IP地址或使用域名
4. **供电稳定性**：外设较多时需确保5V/2A以上供电
5. **Wi-Fi干扰**：避免与其他2.4GHz设备（如蓝牙）同时高负荷使用

---

## 十二、附录

### 12.1 参考文档
- ESP-IDF编程指南：https://docs.espressif.com/projects/esp-idf/
- ESP32-S3数据手册：https://www.espressif.com.cn/sites/default/files/documentation/esp32-s3_datasheet_cn.pdf
- ST7789 LCD驱动手册：https://www.lcdwiki.com/1.44inch_LCD_Module
- OV2640摄像头数据手册

### 12.2 相关资源
- ESP32-S3-Eye开发板资料（正点原子）
- ESP-IDF v5.4+ 开发环境搭建指南
- FastAPI后端服务部署文档

---

*文档版本：v1.0*
*最后更新：2026-04-27*