/*
 * ESP32-S3-EYE WiFi Time Reporter
 * 
 * 功能：
 * 1. 连接WiFi (SSID: 431)
 * 2. 通过SNTP获取NTP实时时间
 * 3. 提供HTTP服务器，手机浏览器访问ESP的IP查看时间
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
#include "nvs_flash.h"
#include "lwip/apps/sntp.h"

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

/* HTTP服务器句柄 */
static httpd_handle_t server = NULL;

/* 函数声明 */
static void wifi_init_sta(void);
static void wifi_event_handler(void *arg, esp_event_base_t event_base,
                               int32_t event_id, void *event_data);
static void ip_event_handler(void *arg, esp_event_base_t event_base,
                             int32_t event_id, void *event_data);
static void start_http_server(void);
static void print_time_callback(TimerHandle_t xTimer);

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
    sntp_setoperatingmode(0);  /* 使用客户端模式 */
    sntp_setservername(0, ntp_servers[0]);
    sntp_setservername(1, ntp_servers[1]);
    sntp_setservername(2, ntp_servers[2]);
    sntp_init();
    ESP_LOGI(TAG, "SNTP configured, time will be synced automatically");
}

/* HTTP根路径处理器 */
static esp_err_t root_get_handler(httpd_req_t *req)
{
    time_t now;
    struct tm timeinfo = {0};
    char time_str[64];
    char ip_str[32];
    
    time(&now);
    localtime_r(&now, &timeinfo);
    strftime(time_str, sizeof(time_str), "%Y-%m-%d %H:%M:%S", &timeinfo);
    
    const char *weekdays[] = {"Sunday", "Monday", "Tuesday", "Wednesday", 
                              "Thursday", "Friday", "Saturday"};
    
    /* 获取服务器IP地址 */
    esp_netif_ip_info_t ip_info;
    esp_netif_t *netif = esp_netif_get_handle_from_ifkey("WIFI_STA_DEF");
    esp_netif_get_ip_info(netif, &ip_info);
    snprintf(ip_str, sizeof(ip_str), IPSTR, IP2STR(&ip_info.ip));
    
    /* 构建HTML响应 */
    char response[1024];
    snprintf(response, sizeof(response),
             "<!DOCTYPE html>"
             "<html>"
             "<head>"
             "<meta charset=\"UTF-8\">"
             "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">"
             "<title>ESP32-S3-EYE 时间上报</title>"
             "<style>"
             "body { font-family: Arial, sans-serif; margin: 50px; background: #f5f5f5; }"
             ".container { background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }"
             "h1 { color: #333; }"
             ".time { font-size: 24px; color: #007bff; margin: 20px 0; }"
             ".info { margin: 10px 0; color: #666; }"
             "</style>"
             "</head>"
             "<body>"
             "<div class=\"container\">"
             "<h1>ESP32-S3-EYE 时间上报</h1>"
             "<div class=\"time\">当前时间: %s</div>"
             "<div class=\"info\">时区: Asia/Shanghai (CST-8)</div>"
             "<div class=\"info\">星期: %s</div>"
             "<div class=\"info\">IP地址: %s</div>"
             "</div>"
             "</body>"
             "</html>",
             time_str,
             weekdays[timeinfo.tm_wday],
             ip_str);
    
    httpd_resp_set_type(req, "text/html");
    httpd_resp_send(req, response, strlen(response));
    
    ESP_LOGI(HTTP_TAG, "Time page accessed: %s", time_str);
    return ESP_OK;
}

/* HTTP JSON API处理器 */
static esp_err_t time_json_get_handler(httpd_req_t *req)
{
    time_t now;
    struct tm timeinfo = {0};
    char time_str[64];
    
    time(&now);
    localtime_r(&now, &timeinfo);
    strftime(time_str, sizeof(time_str), "%Y-%m-%d %H:%M:%S", &timeinfo);
    
    const char *weekdays[] = {"Sunday", "Monday", "Tuesday", "Wednesday", 
                              "Thursday", "Friday", "Saturday"};
    
    char json_data[128];
    snprintf(json_data, sizeof(json_data),
             "{\"time\":\"%s\",\"timezone\":\"Asia/Shanghai\",\"weekday\":\"%s\"}",
             time_str,
             weekdays[timeinfo.tm_wday]);
    
    httpd_resp_set_type(req, "application/json");
    httpd_resp_send(req, json_data, strlen(json_data));
    
    ESP_LOGI(HTTP_TAG, "JSON API accessed: %s", json_data);
    return ESP_OK;
}

/* 启动HTTP服务器 */
static void start_http_server(void)
{
    httpd_config_t config = HTTPD_DEFAULT_CONFIG();
    config.server_port = 80;
    config.stack_size = 4096;
    
    ESP_LOGI(HTTP_TAG, "Starting HTTP server on port 80...");
    
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
    
    httpd_uri_t json_uri = {
        .uri = "/time.json",
        .method = HTTP_GET,
        .handler = time_json_get_handler,
        .user_ctx = NULL
    };
    
    httpd_register_uri_handler(server, &root_uri);
    httpd_register_uri_handler(server, &json_uri);
    
    /* 获取服务器IP地址 */
    esp_netif_ip_info_t ip_info;
    esp_netif_t *netif = esp_netif_get_handle_from_ifkey("WIFI_STA_DEF");
    esp_netif_get_ip_info(netif, &ip_info);
    char ip_str[32];
    snprintf(ip_str, sizeof(ip_str), IPSTR, IP2STR(&ip_info.ip));
    
    ESP_LOGI(HTTP_TAG, "HTTP server started. Access http://%s/ or http://%s/time.json", ip_str, ip_str);
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

    ESP_LOGI(TAG, "ESP32-S3-EYE WiFi Time Reporter started");
    ESP_LOGI(TAG, "Board: ESP32-S3-EYE");
    
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
    
    /* 启动HTTP服务器 */
    start_http_server();
    
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