/*
 * ESP32-S3-EYE WiFi Voice Reporter - HTTP Server + I2S Audio Capture
 * 
 * 功能：
 * 1. 连接WiFi
 * 2. 通过SNTP获取NTP实时时间
 * 3. 提供HTTP服务器，手机浏览器访问查看时间和文字回复
 * 4. I2S PDM麦克风采集音频，通过HTTP POST发送到PC语音识别服务器
 * 5. 接收PC端的文字回复显示在网页上
 */

#include <string.h>
#include <time.h>
#include <sys/time.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/event_groups.h"
#include "freertos/timers.h"
#include "esp_system.h"
#include "esp_wifi.h"
#include "esp_event.h"
#include "esp_log.h"
#include "esp_netif.h"
#include "esp_http_server.h"
#include "esp_http_client.h"
#include "nvs_flash.h"
#include "driver/i2s_pdm.h"
#include "lwip/apps/sntp.h"

static const char *TAG = "time_fetcher";
static const char *HTTP_TAG = "http_server";
static const char *AUDIO_TAG = "audio_capture";
static const char *HTTP_CLIENT_TAG = "http_client";

/* WiFi事件标志位 */
#define WIFI_CONNECTED_BIT BIT0
#define WIFI_FAIL_BIT      BIT1

static int s_retry_num = 0;
static EventGroupHandle_t s_wifi_event_group;
static bool s_wifi_connected = false;

/* NTP服务器列表 */
static const char *ntp_servers[] = {
    "pool.ntp.org",
    "time.windows.com",
    "cn.pool.ntp.org"
};

/* HTTP服务器句柄 */
static httpd_handle_t server = NULL;

/* 音频配置 */
#define AUDIO_SAMPLE_RATE 16000
#define AUDIO_BYTE_RATE (AUDIO_SAMPLE_RATE * 2)  // 16-bit mono
#define AUDIO_BUFFER_SIZE 1600  // 50ms of audio data
#define AUDIO_SEND_INTERVAL_MS 50

/* HTTP发送队列配置 */
#define AUDIO_SEND_QUEUE_SIZE 4
typedef struct {
    uint8_t *data;
    size_t length;
} audio_packet_t;

/* PC语音识别服务器地址 (端口8087) */
#define VOICE_SERVER_URL "http://10.1.41.99:8087/voice"
#define VOICE_SERVER_IP "10.1.41.99"
#define VOICE_SERVER_PORT 8087

/* 文字回复存储 */
#define REPLY_BUFFER_SIZE 256
static char s_text_reply[REPLY_BUFFER_SIZE] = "";
static bool s_reply_updated = false;
static SemaphoreHandle_t s_reply_mutex;

/* I2S麦克风句柄 */
static i2s_chan_handle_t i2s_rx_handle = NULL;

/* 函数声明 */
static void wifi_init_sta(void);
static void wifi_event_handler(void *arg, esp_event_base_t event_base,
                               int32_t event_id, void *event_data);
static void ip_event_handler(void *arg, esp_event_base_t event_base,
                             int32_t event_id, void *event_data);
static esp_err_t root_get_handler(httpd_req_t *req);
static esp_err_t api_time_get_handler(httpd_req_t *req);
static esp_err_t api_reply_get_handler(httpd_req_t *req);
static esp_err_t api_reply_post_handler(httpd_req_t *req);
static void start_http_server(void);
static void print_time_callback(TimerHandle_t xTimer);
static void audio_capture_task(void *pvParameters);
static esp_err_t send_audio_to_server(uint8_t *data, size_t length);
static void init_i2s_microphone(void);

/* WiFi初始化 - Station模式 */
static void wifi_init_sta(void)
{
    s_wifi_event_group = xEventGroupCreate();

    ESP_ERROR_CHECK(esp_netif_init());
    ESP_ERROR_CHECK(esp_event_loop_create_default());
    esp_netif_create_default_wifi_sta();

    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(esp_wifi_init(&cfg));

    /* 注册事件处理器 */
    ESP_ERROR_CHECK(esp_event_handler_instance_register(WIFI_EVENT,
                                                        ESP_EVENT_ANY_ID,
                                                        &wifi_event_handler,
                                                        NULL,
                                                        NULL));
    ESP_ERROR_CHECK(esp_event_handler_instance_register(IP_EVENT,
                                                        IP_EVENT_STA_GOT_IP,
                                                        &ip_event_handler,
                                                        NULL,
                                                        NULL));

    /* 配置WiFi */
    wifi_config_t wifi_config = {
        .sta = {
            .ssid = "431",
            .password = "88888888",
            .threshold.authmode = WIFI_AUTH_WPA_PSK,
            .pmf_cfg = {
                .capable = false,
                .required = false
            },
        },
    };

    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_STA));
    ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_STA, &wifi_config));
    ESP_ERROR_CHECK(esp_wifi_start());

    ESP_LOGI(TAG, "WiFi STA mode initialized, connecting...");

    /* 等待连接结果 */
    EventBits_t bits = xEventGroupWaitBits(s_wifi_event_group,
                                           WIFI_CONNECTED_BIT | WIFI_FAIL_BIT,
                                           pdFALSE,
                                           pdFALSE,
                                           portMAX_DELAY);

    if (bits & WIFI_CONNECTED_BIT) {
        ESP_LOGI(TAG, "Connected to AP SSID:'431'");
        s_wifi_connected = true;
    } else if (bits & WIFI_FAIL_BIT) {
        ESP_LOGE(TAG, "Failed to connect to AP SSID:'431'");
    }
}

/* WiFi事件处理 */
static void wifi_event_handler(void *arg, esp_event_base_t event_base,
                               int32_t event_id, void *event_data)
{
    if (event_base == WIFI_EVENT && event_id == WIFI_EVENT_STA_START) {
        esp_wifi_connect();
    } else if (event_base == WIFI_EVENT && event_id == WIFI_EVENT_STA_DISCONNECTED) {
        wifi_event_sta_disconnected_t *disconnected = (wifi_event_sta_disconnected_t *)event_data;
        ESP_LOGE(TAG, "Disconnected from AP: SSID '%s', reason 0x%x", 
                 disconnected->ssid, disconnected->reason);
        if (s_retry_num < 20) {
            esp_wifi_connect();
            s_retry_num++;
            ESP_LOGI(TAG, "Retry to connect to the AP (attempt %d/20)", s_retry_num);
        } else {
            xEventGroupSetBits(s_wifi_event_group, WIFI_FAIL_BIT);
            ESP_LOGE(TAG, "Max retries reached, giving up");
        }
    }
}

/* IP获取事件处理 */
static void ip_event_handler(void *arg, esp_event_base_t event_base,
                             int32_t event_id, void *event_data)
{
    ip_event_got_ip_t *event = (ip_event_got_ip_t *)event_data;
    ESP_LOGI(TAG, "Got IP: " IPSTR, IP2STR(&event->ip_info.ip));
    s_retry_num = 0;
    xEventGroupSetBits(s_wifi_event_group, WIFI_CONNECTED_BIT);
    
    /* WiFi连接成功后配置SNTP */
    ESP_LOGI(TAG, "Configuring SNTP...");
    sntp_setoperatingmode(0);
    sntp_setservername(0, ntp_servers[0]);
    sntp_setservername(1, ntp_servers[1]);
    sntp_setservername(2, ntp_servers[2]);
    sntp_init();
    ESP_LOGI(TAG, "SNTP configured, time will be synced automatically");
}

/* 初始化I2S PDM麦克风 */
static void init_i2s_microphone(void)
{
    i2s_chan_config_t chan_cfg = I2S_CHANNEL_DEFAULT_CONFIG(I2S_NUM_AUTO, I2S_ROLE_MASTER);
    ESP_ERROR_CHECK(i2s_new_channel(&chan_cfg, NULL, &i2s_rx_handle));

    i2s_pdm_rx_config_t pdm_rx_cfg = {
        .clk_cfg = I2S_PDM_RX_CLK_DEFAULT_CONFIG(AUDIO_SAMPLE_RATE),
        .slot_cfg = I2S_PDM_RX_SLOT_DEFAULT_CONFIG(I2S_DATA_BIT_WIDTH_16BIT, I2S_SLOT_MODE_MONO),
        .gpio_cfg = {
            .clk = GPIO_NUM_46,  // I2S CLK pin for ESP32-S3-EYE
            .din = GPIO_NUM_43,  // I2S DATA pin for ESP32-S3-EYE
            .invert_flags = {
                .clk_inv = false,
            },
        },
    };
    ESP_ERROR_CHECK(i2s_channel_init_pdm_rx_mode(i2s_rx_handle, &pdm_rx_cfg));
    ESP_ERROR_CHECK(i2s_channel_enable(i2s_rx_handle));
    
    ESP_LOGI(AUDIO_TAG, "I2S PDM microphone initialized");
}

/* 发送音频数据到PC语音识别服务器 - 使用持久连接减少栈消耗 */
static esp_err_t send_audio_to_server(uint8_t *data, size_t length)
{
    if (!s_wifi_connected) {
        return ESP_FAIL;
    }
    
    /* 使用静态变量保持连接 */
    static esp_http_client_handle_t client = NULL;
    static char url_buf[128];
    static int init_done = 0;
    
    if (!init_done) {
        esp_http_client_config_t config = {
            .url = VOICE_SERVER_URL,
            .method = HTTP_METHOD_POST,
            .timeout_ms = 3000,
            .disable_auto_redirect = false,
        };
        
        client = esp_http_client_init(&config);
        if (client == NULL) {
            ESP_LOGE(HTTP_CLIENT_TAG, "Failed to initialize HTTP client");
            return ESP_FAIL;
        }
        init_done = 1;
    }
    
    /* 设置请求内容长度 */
    esp_http_client_set_header(client, "Content-Type", "application/octet-stream");
    esp_err_t err = esp_http_client_open(client, length);
    if (err != ESP_OK) {
        ESP_LOGW(HTTP_CLIENT_TAG, "Open failed: %s, retrying...", esp_err_to_name(err));
        esp_http_client_cleanup(client);
        init_done = 0;
        return ESP_FAIL;
    }
    
    int written = esp_http_client_write(client, (char *)data, length);
    if (written < 0) {
        ESP_LOGW(HTTP_CLIENT_TAG, "Write failed");
        esp_http_client_cleanup(client);
        init_done = 0;
        return ESP_FAIL;
    }
    
    int status_code = esp_http_client_fetch_headers(client);
    if (status_code < 200 || status_code >= 300) {
        ESP_LOGW(HTTP_CLIENT_TAG, "Status %d", status_code);
    }
    
    esp_http_client_close(client);
    return ESP_OK;
}

/* 音频采集队列句柄 */
static QueueHandle_t s_audio_queue = NULL;

/* I2S音频采集任务 - 只负责采集和入队 */
static void audio_capture_task(void *pvParameters)
{
    size_t bytes_read;
    int16_t *audio_buffer = NULL;
    int consecutive_failures = 0;
    
    audio_buffer = (int16_t *)malloc(AUDIO_BUFFER_SIZE);
    if (audio_buffer == NULL) {
        ESP_LOGE(AUDIO_TAG, "Failed to allocate audio buffer");
        vTaskDelete(NULL);
        return;
    }
    
    ESP_LOGI(AUDIO_TAG, "Audio capture task started");
    
    while (1) {
        /* 读取音频数据 */
        if (i2s_channel_read(i2s_rx_handle, (char *)audio_buffer, AUDIO_BUFFER_SIZE, &bytes_read, 1000) == ESP_OK) {
            /* 将数据放入队列 - 不等待，直接发送 */
            audio_packet_t *packet = (audio_packet_t *)malloc(sizeof(audio_packet_t));
            if (packet != NULL) {
                packet->data = (uint8_t *)malloc(bytes_read);
                if (packet->data != NULL) {
                    memcpy(packet->data, audio_buffer, bytes_read);
                    packet->length = bytes_read;
                    /* 非阻塞发送 */
                    if (xQueueSend(s_audio_queue, &packet, 0) != pdTRUE) {
                        free(packet->data);
                        free(packet);
                    }
                } else {
                    free(packet);
                }
            }
        } else {
            ESP_LOGW(AUDIO_TAG, "I2S read failed");
        }
        
        vTaskDelay(pdMS_TO_TICKS(AUDIO_SEND_INTERVAL_MS));
    }
    
    free(audio_buffer);
}

/* HTTP音频发送任务 - 负责网络通信 */
static void audio_http_send_task(void *pvParameters)
{
    audio_packet_t *packet = NULL;
    
    ESP_LOGI(AUDIO_TAG, "HTTP send task started");
    
    while (1) {
        /* 从队列获取音频数据包 */
        if (xQueueReceive(s_audio_queue, &packet, pdMS_TO_TICKS(100))) {
            if (packet == NULL) {
                continue;
            }
            
            /* 每次请求都创建新的HTTP客户端，避免Connection reset问题 */
            esp_http_client_config_t config = {
                .url = VOICE_SERVER_URL,
                .method = HTTP_METHOD_POST,
                .timeout_ms = 5000,
                .disable_auto_redirect = false,
            };
            
            esp_http_client_handle_t client = esp_http_client_init(&config);
            if (client == NULL) {
                ESP_LOGE(HTTP_CLIENT_TAG, "Failed to init HTTP client");
                free(packet->data);
                free(packet);
                continue;
            }
            
            /* 设置请求头 */
            esp_http_client_set_header(client, "Content-Type", "application/octet-stream");
            
            /* 打开连接 */
            esp_err_t err = esp_http_client_open(client, packet->length);
            if (err != ESP_OK) {
                ESP_LOGE(HTTP_CLIENT_TAG, "Open failed: %s", esp_err_to_name(err));
                esp_http_client_cleanup(client);
                free(packet->data);
                free(packet);
                vTaskDelay(pdMS_TO_TICKS(100));
                continue;
            }
            
            /* 写入音频数据 */
            int written = esp_http_client_write(client, (char *)packet->data, packet->length);
            if (written < 0) {
                ESP_LOGE(HTTP_CLIENT_TAG, "Write failed");
            } else {
                /* 获取响应头 */
                int status_code = esp_http_client_fetch_headers(client);
                if (status_code >= 200 && status_code < 300) {
                    ESP_LOGI(HTTP_CLIENT_TAG, "Send OK, status %d", status_code);
                } else {
                    ESP_LOGW(HTTP_CLIENT_TAG, "Status %d", status_code);
                }
            }
            
            /* 关闭并清理连接 */
            esp_http_client_close(client);
            esp_http_client_cleanup(client);
            
            /* 释放数据包内存 */
            free(packet->data);
            free(packet);
            
            /* 短暂延迟避免连接过于频繁 */
            vTaskDelay(pdMS_TO_TICKS(10));
        }
    }
}

/* HTTP根路径处理器 - 返回HTML网页 */
static esp_err_t root_get_handler(httpd_req_t *req)
{
    /* 获取服务器IP地址 */
    esp_netif_ip_info_t ip_info;
    esp_netif_t *netif = esp_netif_get_handle_from_ifkey("WIFI_STA_DEF");
    esp_netif_get_ip_info(netif, &ip_info);
    char ip_str[32];
    snprintf(ip_str, sizeof(ip_str), IPSTR, IP2STR(&ip_info.ip));
    
    /* 获取当前时间 */
    time_t now;
    struct tm timeinfo = {0};
    char time_str[32];
    char date_str[32];
    
    time(&now);
    localtime_r(&now, &timeinfo);
    strftime(time_str, sizeof(time_str), "%H:%M:%S", &timeinfo);
    strftime(date_str, sizeof(date_str), "%Y/%m/%d", &timeinfo);
    
    /* 获取文字回复 */
    char reply_text[REPLY_BUFFER_SIZE];
    if (s_reply_mutex != NULL && xSemaphoreTake(s_reply_mutex, pdMS_TO_TICKS(100)) == pdTRUE) {
        strncpy(reply_text, s_text_reply, REPLY_BUFFER_SIZE - 1);
        reply_text[REPLY_BUFFER_SIZE - 1] = '\0';
        xSemaphoreGive(s_reply_mutex);
    } else {
        strcpy(reply_text, "");
    }
    
    /* 使用静态缓冲区避免栈溢出 */
    static char html_response[4096];
    size_t offset = 0;
    
    /* 构建HTML响应 */
    offset += snprintf(html_response + offset, sizeof(html_response) - offset,
        "<!DOCTYPE html><html lang=\"zh-CN\"><head>"
        "<meta charset=\"UTF-8\"><meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">"
        "<title>ESP32 Voice</title>"
        "<style>"
        "*{margin:0;padding:0;box-sizing:border-box}"
        "body{font-family:sans-serif;background:linear-gradient(135deg,#667eea,#764ba2);min-height:100vh;display:flex;justify-content:center;align-items:center;padding:20px}"
        ".container{background:rgba(255,255,255,0.95);border-radius:20px;padding:40px;text-align:center;max-width:500px;width:100%%}"
        ".time{font-size:48px;font-weight:700;color:#333;margin:20px 0;font-family:monospace}"
        ".date{font-size:20px;color:#888;margin:15px 0}"
        ".reply-section{margin-top:30px;padding-top:20px;border-top:1px solid #eee}"
        ".reply-label{font-size:14px;color:#999;margin-bottom:10px}"
        ".reply-text{font-size:16px;color:#333;background:#f5f5f5;padding:15px;border-radius:10px;min-height:50px;margin-bottom:15px;word-wrap:break-word}"
        ".reply-input{width:100%%;padding:12px;font-size:14px;border:1px solid #ddd;border-radius:10px;margin-bottom:10px}"
        ".reply-btn{background:#667eea;color:white;border:none;padding:12px 30px;font-size:14px;border-radius:10px;cursor:pointer}"
        ".ip{font-size:12px;color:#bbb;margin-top:10px}"
        "</style></head><body><div class=\"container\">"
        "<div class=\"time\">%s</div>"
        "<div class=\"date\">%s</div>"
        "<div class=\"ip\">IP: %s</div>"
        "<div class=\"reply-section\">"
        "<div class=\"reply-label\">PC Reply:</div>"
        "<div class=\"reply-text\" id=\"reply\">%s</div>"
        "<form id=\"rf\"><input type=\"text\" class=\"reply-input\" id=\"ri\" placeholder=\"Type reply...\">"
        "<button type=\"submit\" class=\"reply-btn\">Send</button></form></div>"
        "<script>"
        "setInterval(function(){var n=new Date();document.getElementById('time').textContent=String(n.getHours()).padStart(2,'0')+':'+String(n.getMinutes()).padStart(2,'0')+':'+String(n.getSeconds()).padStart(2,'0');document.getElementById('date').textContent=n.getFullYear()+'/'+String(n.getMonth()+1).padStart(2,'0')+'/'+String(n.getDate()).padStart(2,'0')},1000);"
        "setInterval(function(){fetch('/api/reply').then(r=>r.text()).then(t=>{if(t)document.getElementById('reply').textContent=t}),2000);"
        "document.getElementById('rf').addEventListener('submit',function(e){e.preventDefault();fetch('/api/reply',{method:'POST',headers:{'Content-Type':'text/plain'},body:document.getElementById('ri').value}).then(r=>r.text()).then(t=>{document.getElementById('reply').textContent=t;document.getElementById('ri').value=''})});"
        "</script></body></html>",
        time_str, date_str, ip_str, reply_text);
    
    httpd_resp_set_type(req, "text/html; charset=utf-8");
    httpd_resp_send(req, html_response, strlen(html_response));
    
    ESP_LOGI(HTTP_TAG, "Voice page accessed");
    return ESP_OK;
}

/* HTTP JSON API处理器 - 获取时间 */
static esp_err_t api_time_get_handler(httpd_req_t *req)
{
    time_t now;
    struct tm timeinfo = {0};
    char time_str[64];
    const char *weekdays[] = {"Sunday", "Monday", "Tuesday", "Wednesday", 
                              "Thursday", "Friday", "Saturday"};
    
    time(&now);
    localtime_r(&now, &timeinfo);
    strftime(time_str, sizeof(time_str), "%Y-%m-%d %H:%M:%S", &timeinfo);
    
    char json_data[128];
    snprintf(json_data, sizeof(json_data),
             "{\"time\":\"%s\",\"timezone\":\"Asia/Shanghai\",\"weekday\":\"%s\"}",
             time_str, weekdays[timeinfo.tm_wday]);
    
    httpd_resp_set_type(req, "application/json");
    httpd_resp_send(req, json_data, strlen(json_data));
    
    ESP_LOGI(HTTP_TAG, "JSON API accessed: %s", json_data);
    return ESP_OK;
}

/* HTTP API处理器 - 获取文字回复 */
static esp_err_t api_reply_get_handler(httpd_req_t *req)
{
    char reply_text[REPLY_BUFFER_SIZE];
    
    if (s_reply_mutex != NULL && xSemaphoreTake(s_reply_mutex, pdMS_TO_TICKS(100)) == pdTRUE) {
        strncpy(reply_text, s_text_reply, REPLY_BUFFER_SIZE - 1);
        reply_text[REPLY_BUFFER_SIZE - 1] = '\0';
        xSemaphoreGive(s_reply_mutex);
    } else {
        strcpy(reply_text, "");
    }
    
    httpd_resp_set_type(req, "text/plain");
    httpd_resp_send(req, reply_text, strlen(reply_text));
    
    return ESP_OK;
}

/* HTTP API处理器 - 设置文字回复 */
static esp_err_t api_reply_post_handler(httpd_req_t *req)
{
    char buf[REPLY_BUFFER_SIZE];
    int content_len = req->content_len;
    
    if (content_len >= REPLY_BUFFER_SIZE) {
        content_len = REPLY_BUFFER_SIZE - 1;
    }
    
    int received = 0;
    while (received < content_len) {
        int ret = httpd_req_recv(req, buf + received, content_len - received);
        if (ret <= 0) {
            break;
        }
        received += ret;
    }
    buf[received] = '\0';
    
    /* 更新回复文本 */
    if (s_reply_mutex != NULL && xSemaphoreTake(s_reply_mutex, pdMS_TO_TICKS(100)) == pdTRUE) {
        strncpy(s_text_reply, buf, REPLY_BUFFER_SIZE - 1);
        s_text_reply[REPLY_BUFFER_SIZE - 1] = '\0';
        s_reply_updated = true;
        xSemaphoreGive(s_reply_mutex);
        ESP_LOGI(HTTP_TAG, "Reply updated: %s", s_text_reply);
    }
    
    char response[REPLY_BUFFER_SIZE + 16];
    snprintf(response, sizeof(response), "OK: %s", s_text_reply);
    
    httpd_resp_set_type(req, "text/plain");
    httpd_resp_send(req, response, strlen(response));
    
    return ESP_OK;
}

/* 启动HTTP服务器 */
static void start_http_server(void)
{
    httpd_config_t config = HTTPD_DEFAULT_CONFIG();
    config.server_port = 8087;
    config.stack_size = 8192;  // 增加栈空间避免溢出
    
    ESP_LOGI(HTTP_TAG, "Starting HTTP server...");
    
    esp_err_t err = httpd_start(&server, &config);
    if (err != ESP_OK) {
        ESP_LOGE(HTTP_TAG, "Failed to start HTTP server: %s", esp_err_to_name(err));
        return;
    }
    
    httpd_uri_t root_uri = {
        .uri = "/",
        .method = HTTP_GET,
        .handler = root_get_handler,
        .user_ctx = NULL
    };
    
    httpd_uri_t time_uri = {
        .uri = "/api/time",
        .method = HTTP_GET,
        .handler = api_time_get_handler,
        .user_ctx = NULL
    };
    
    httpd_uri_t reply_get_uri = {
        .uri = "/api/reply",
        .method = HTTP_GET,
        .handler = api_reply_get_handler,
        .user_ctx = NULL
    };
    
    httpd_uri_t reply_post_uri = {
        .uri = "/api/reply",
        .method = HTTP_POST,
        .handler = api_reply_post_handler,
        .user_ctx = NULL
    };
    
    httpd_register_uri_handler(server, &root_uri);
    httpd_register_uri_handler(server, &time_uri);
    httpd_register_uri_handler(server, &reply_get_uri);
    httpd_register_uri_handler(server, &reply_post_uri);
    
    /* 获取服务器IP地址 */
    esp_netif_ip_info_t ip_info;
    esp_netif_t *netif = esp_netif_get_handle_from_ifkey("WIFI_STA_DEF");
    esp_netif_get_ip_info(netif, &ip_info);
    char ip_str[32];
    snprintf(ip_str, sizeof(ip_str), IPSTR, IP2STR(&ip_info.ip));
    
    ESP_LOGI(HTTP_TAG, "HTTP server started. Access http://%s/", ip_str);
}

/* 定期打印时间回调 */
static void print_time_callback(TimerHandle_t xTimer)
{
    time_t now;
    struct tm timeinfo = {0};
    char strftime_buf[64];
    
    time(&now);
    localtime_r(&now, &timeinfo);
    strftime(strftime_buf, sizeof(strftime_buf), "%c", &timeinfo);
    
    ESP_LOGI(TAG, "time_fetcher: time: %s, Sunday, Asia/Shanghai", strftime_buf);
}

void app_main(void)
{
    /* 初始化NVS闪存 */
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase());
        ret = nvs_flash_init();
    }
    ESP_ERROR_CHECK(ret);

    ESP_LOGI(TAG, "ESP32-S3-EYE WiFi Voice Reporter started");
    ESP_LOGI(TAG, "Board: ESP32-S3-EYE");
    
    /* 设置时区为中国标准时间 */
    setenv("TZ", "CST-8", 1);
    tzset();
    
    /* 创建回复互斥锁 */
    s_reply_mutex = xSemaphoreCreateMutex();
    if (s_reply_mutex != NULL) {
        xSemaphoreGive(s_reply_mutex);
    }
    
    /* 初始化WiFi并连接 */
    wifi_init_sta();
    
    if (!s_wifi_connected) {
        ESP_LOGE(TAG, "WiFi connection failed, restarting in 5 seconds...");
        vTaskDelay(pdMS_TO_TICKS(5000));
        esp_restart();
    }
    
    /* 初始化I2S麦克风 */
    init_i2s_microphone();
    
    /* 启动HTTP服务器 */
    start_http_server();
    
    /* 创建音频采集队列 */
    s_audio_queue = xQueueCreate(AUDIO_SEND_QUEUE_SIZE, sizeof(audio_packet_t *));
    if (s_audio_queue == NULL) {
        ESP_LOGE(AUDIO_TAG, "Failed to create audio queue");
    }
    
    /* 创建音频采集任务 (栈空间8192字节) */
    xTaskCreate(audio_capture_task, "audio_capture", 8192, NULL, 5, NULL);
    
    /* 创建HTTP发送任务 (栈空间16384字节，esp_http_client需要大量栈) */
    if (s_audio_queue != NULL) {
        xTaskCreate(audio_http_send_task, "audio_http_send", 16384, NULL, 4, NULL);
    }
    
    /* 创建定期打印时间定时器 (每10秒) */
    TimerHandle_t print_timer = xTimerCreate("print_timer",
                                             pdMS_TO_TICKS(10000),
                                             pdTRUE,
                                             NULL,
                                             print_time_callback);
    
    if (print_timer != NULL) {
        if (xTimerStart(print_timer, pdMS_TO_TICKS(1000)) == pdPASS) {
            ESP_LOGI(TAG, "Print timer started (10s interval)");
        } else {
            ESP_LOGE(TAG, "Failed to start print timer");
        }
    }
    
    /* 主循环 - 等待 */
    while (1) {
        vTaskDelay(pdMS_TO_TICKS(1000));
    }
}