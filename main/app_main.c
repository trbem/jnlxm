/*
 * ESP32-S3-EYE WiFi Time Reporter
 * 
 * 功能：
 * 1. 连接WiFi (SSID: 431)
 * 2. 通过SNTP获取NTP实时时间
 * 3. 每30秒将时间信息上报到局域网服务器 http://10.1.41.99:8085
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
#include "esp_netif_sntp.h"
#include "esp_http_client.h"
#include "nvs_flash.h"

static const char *TAG = "time_fetcher";
static const char *HTTP_TAG = "reporter";

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
#define NTP_SERVER_COUNT (sizeof(ntp_servers) / sizeof(ntp_servers[0]))

/* 函数声明 */
static void wifi_init_sta(void);
static void obtain_time(void);
static void report_time_to_server(void);
static void wifi_event_handler(void *arg, esp_event_base_t event_base,
                               int32_t event_id, void *event_data);
static void ip_event_handler(void *arg, esp_event_base_t event_base,
                             int32_t event_id, void *event_data);
static bool is_time_synced(void);

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

    /* 配置WiFi - 使用纯WPA2认证模式 */
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

    /* 打印配置的SSID用于调试 */
    ESP_LOGI(TAG, "Configured SSID: '%s'", wifi_config.sta.ssid);

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
}

/* 检查时间是否已同步 */
static bool is_time_synced(void)
{
    time_t now;
    struct tm timeinfo = {0};
    time(&now);
    localtime_r(&now, &timeinfo);
    
    /* 如果tm_year小于(2024-1900)，说明时间还未设置(仍是1970年) */
    return timeinfo.tm_year >= (2024 - 1900);
}

/* 初始化SNTP */
static void initialize_sntp(void)
{
    ESP_LOGI(TAG, "Initializing SNTP");
    
    /* ESP-IDF v5.4使用ESP_NETIF_SNTP_DEFAULT_CONFIG_MULTIPLE配置多个NTP服务器 */
    esp_sntp_config_t config = ESP_NETIF_SNTP_DEFAULT_CONFIG_MULTIPLE(
        NTP_SERVER_COUNT,
        ESP_SNTP_SERVER_LIST(ntp_servers[0], ntp_servers[1]));
    
    config.start = true;  /* 自动启动SNTP服务 */
    
    esp_netif_sntp_init(&config);
}

/* 获取时间 - 等待NTP同步完成 */
static void obtain_time(void)
{
    if (!s_wifi_connected) {
        ESP_LOGW(TAG, "WiFi not connected, skipping time sync");
        return;
    }

    initialize_sntp();

    /* 等待时间同步完成 - 最多等待30秒 */
    int retry = 0;
    const int max_retries = 30;
    
    ESP_LOGI(TAG, "Waiting for NTP time sync...");
    while (!is_time_synced() && ++retry < max_retries) {
        ESP_LOGI(TAG, "Waiting for system time to be set... (%ds/%ds)", retry, max_retries);
        vTaskDelay(pdMS_TO_TICKS(1000));
    }
    
    if (!is_time_synced()) {
        ESP_LOGE(TAG, "Failed to get time from NTP servers after %d seconds", max_retries);
        esp_netif_sntp_deinit();
        return;
    }

    ESP_LOGI(TAG, "Time synchronized successfully from NTP");
    
    /* 打印当前时间 */
    time_t now;
    struct tm timeinfo = {0};
    time(&now);
    localtime_r(&now, &timeinfo);
    
    char strftime_buf[64];
    strftime(strftime_buf, sizeof(strftime_buf), "%c", &timeinfo);
    ESP_LOGI(TAG, "Current time: %s", strftime_buf);
    
    esp_netif_sntp_deinit();
}

/* HTTP上报回调 */
static esp_err_t _http_event_handler(esp_http_client_event_t *evt)
{
    switch (evt->event_id) {
        case HTTP_EVENT_ERROR:
            ESP_LOGE(HTTP_TAG, "HTTP Event Error");
            break;
        case HTTP_EVENT_ON_CONNECTED:
            ESP_LOGI(HTTP_TAG, "HTTP connected");
            break;
        case HTTP_EVENT_HEADER_SENT:
            ESP_LOGI(HTTP_TAG, "HTTP header sent");
            break;
        case HTTP_EVENT_ON_DATA:
            ESP_LOGI(HTTP_TAG, "HTTP data received");
            break;
        case HTTP_EVENT_ON_FINISH:
            ESP_LOGI(HTTP_TAG, "HTTP response finished");
            break;
        case HTTP_EVENT_DISCONNECTED:
            ESP_LOGI(HTTP_TAG, "HTTP disconnected");
            break;
        default:
            break;
    }
    return ESP_OK;
}

/* 上报时间到服务器 */
static void report_time_to_server(void)
{
    if (!s_wifi_connected) {
        ESP_LOGW(HTTP_TAG, "Cannot report: WiFi not connected");
        return;
    }
    
    if (!is_time_synced()) {
        ESP_LOGW(HTTP_TAG, "Cannot report: Time not synced yet");
        return;
    }

    time_t now;
    time(&now);
    struct tm timeinfo = {0};
    localtime_r(&now, &timeinfo);
    
    char time_str[64];
    strftime(time_str, sizeof(time_str), "%Y-%m-%d %H:%M:%S", &timeinfo);
    
    /* 构建JSON数据 */
    const char *weekdays[] = {"Sunday", "Monday", "Tuesday", "Wednesday", 
                              "Thursday", "Friday", "Saturday"};
    
    char json_data[128];
    snprintf(json_data, sizeof(json_data),
             "{\"time\":\"%s\",\"timezone\":\"Asia/Shanghai\",\"weekday\":\"%s\"}",
             time_str,
             weekdays[timeinfo.tm_wday]);
    
    ESP_LOGI(HTTP_TAG, "Reporting time: %s", json_data);
    
    /* 配置HTTP客户端 */
    esp_http_client_config_t config = {
        .url = "http://10.1.41.99:8085/time",
        .event_handler = _http_event_handler,
        .method = HTTP_METHOD_POST,
        .timeout_ms = 5000,
    };
    
    esp_http_client_handle_t client = esp_http_client_init(&config);
    
    /* 设置请求头 */
    esp_http_client_set_header(client, "Content-Type", "application/json");
    
    /* 发送请求 */
    esp_err_t err = esp_http_client_open(client, strlen(json_data));
    if (err != ESP_OK) {
        ESP_LOGE(HTTP_TAG, "Failed to open HTTP connection: %s", esp_err_to_name(err));
        esp_http_client_cleanup(client);
        return;
    }
    
    /* 写入数据 */
    err = esp_http_client_write(client, json_data, strlen(json_data));
    if (err < 0) {
        ESP_LOGE(HTTP_TAG, "Failed to write HTTP data: %s", esp_err_to_name(err));
    } else {
        ESP_LOGI(HTTP_TAG, "Successfully wrote %d bytes", err);
    }
    
    /* 读取响应 */
    int status_code = esp_http_client_fetch_headers(client);
    if (status_code >= 200 && status_code < 300) {
        char response[256];
        int content_len = esp_http_client_get_content_length(client);
        if (content_len > 0 && content_len < (int)sizeof(response) - 1) {
            int read_len = esp_http_client_read(client, response, content_len);
            if (read_len > 0) {
                response[read_len] = '\0';
                ESP_LOGI(HTTP_TAG, "Server response (%d): %s", status_code, response);
            }
        } else {
            ESP_LOGI(HTTP_TAG, "Server response (%d): (no content or length: %d)", 
                     status_code, content_len);
        }
    } else {
        ESP_LOGW(HTTP_TAG, "HTTP response status: %d", status_code);
    }
    
    /* 清理资源 */
    esp_http_client_cleanup(client);
}

/* 定期上报定时器回调 */
static void report_timer_callback(TimerHandle_t xTimer)
{
    report_time_to_server();
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

    ESP_LOGI(TAG, "ESP32-S3-EYE WiFi Time Reporter started");
    ESP_LOGI(TAG, "Board: ESP32-S3-EYE");
    ESP_LOGI(TAG, "Target server: http://10.1.41.99:8085");
    
    /* 设置时区为中国标准时间 */
    setenv("TZ", "CST-8", 1);
    tzset();
    
    /* 初始化WiFi并连接 */
    wifi_init_sta();
    
    if (!s_wifi_connected) {
        ESP_LOGE(TAG, "WiFi connection failed, restarting in 5 seconds...");
        vTaskDelay(pdMS_TO_TICKS(5000));
        esp_restart();
    }
    
    /* 获取初始时间 - 此函数会阻塞直到时间同步完成 */
    obtain_time();
    
    /* 创建定期上报定时器 (每30秒) */
    TimerHandle_t report_timer = xTimerCreate("report_timer",
                                               pdMS_TO_TICKS(30000),
                                               pdTRUE,
                                               NULL,
                                               report_timer_callback);
    
    if (report_timer != NULL) {
        if (xTimerStart(report_timer, pdMS_TO_TICKS(1000)) == pdPASS) {
            ESP_LOGI(TAG, "Report timer started (30s interval)");
        } else {
            ESP_LOGE(TAG, "Failed to start report timer");
        }
    }
    
    /* 主循环 - 定期打印当前时间 */
    char strftime_buf[64];
    while (1) {
        vTaskDelay(pdMS_TO_TICKS(10000));  /* 每10秒打印一次时间 */
        
        time_t now;
        struct tm timeinfo = {0};
        time(&now);
        localtime_r(&now, &timeinfo);
        strftime(strftime_buf, sizeof(strftime_buf), "%c", &timeinfo);
        
        ESP_LOGI(TAG, "time_fetcher: time: %s, Sunday, Asia/Shanghai", strftime_buf);
    }
}