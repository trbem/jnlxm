#include <string.h>
#include "esp_http_client.h"
#include "esp_log.h"
#include "cJSON.h"
#include "config.h"

static const char *TAG = "HTTP";

// HTTP 事件处理
static esp_err_t http_event_handler(esp_http_client_event_t *evt)
{
    switch (evt->event_id) {
    case HTTP_EVENT_ERROR:
        ESP_LOGD(TAG, "HTTP_EVENT_ERROR");
        break;
    case HTTP_EVENT_ON_CONNECTED:
        ESP_LOGD(TAG, "HTTP_EVENT_ON_CONNECTED");
        break;
    case HTTP_EVENT_HEADER_SENT:
        ESP_LOGD(TAG, "HTTP_EVENT_HEADER_SENT");
        break;
    case HTTP_EVENT_ON_HEADER:
        ESP_LOGD(TAG, "HTTP_EVENT_ON_HEADER, key=%s, value=%s", evt->header_key, evt->header_value);
        break;
    case HTTP_EVENT_ON_DATA:
        ESP_LOGD(TAG, "HTTP_EVENT_ON_DATA, len=%d", evt->data_len);
        break;
    case HTTP_EVENT_ON_FINISH:
        ESP_LOGD(TAG, "HTTP_EVENT_ON_FINISH");
        break;
    case HTTP_EVENT_DISCONNECTED:
        ESP_LOGD(TAG, "HTTP_EVENT_DISCONNECTED");
        break;
    default:
        break;
    }
    return ESP_OK;
}

// 设备注册
char* http_device_register(const char *device_name)
{
    char url[256];
    snprintf(url, sizeof(url), "%s:%d/api/device/register", API_URL, API_PORT);

    cJSON *body = cJSON_CreateObject();
    cJSON_AddStringToObject(body, "device_name", device_name);
    cJSON_AddStringToObject(body, "device_type", "ESP32-S3-EYE");
    char *json_str = cJSON_PrintUnformatted(body);

    esp_http_client_config_t config = {
        .url = url,
        .event_handler = http_event_handler,
        .method = HTTP_METHOD_POST,
    };

    esp_http_client_handle_t client = esp_http_client_init(&config);
    esp_http_client_set_header(client, "Content-Type", "application/json");
    esp_http_client_set_post_field(client, json_str, strlen(json_str));

    char *response = NULL;
    int content_length = 0;

    esp_err_t err = esp_http_client_perform(client);
    if (err == ESP_OK) {
        content_length = esp_http_client_get_content_length(client);
        response = malloc(content_length + 1);
        if (response) {
            int read_len = esp_http_client_read(client, response, content_length);
            response[read_len] = '\0';
        }
    }

    esp_http_client_cleanup(client);
    cJSON_Delete(body);
    free(json_str);

    // 解析响应获取 token
    if (response) {
        cJSON *json = cJSON_Parse(response);
        if (json) {
            cJSON *token = cJSON_GetObjectItem(json, "device_token");
            if (token && token->valuestring) {
                char *result = strdup(token->valuestring);
                cJSON_Delete(json);
                free(response);
                return result;
            }
            cJSON_Delete(json);
        }
        free(response);
    }

    return NULL;
}

// 发送心跳
esp_err_t http_send_heartbeat(const char *device_token)
{
    char url[256];
    snprintf(url, sizeof(url), "%s:%d/api/device/heartbeat", API_URL, API_PORT);

    char post_data[256];
    snprintf(post_data, sizeof(post_data), "device_token=%s", device_token);

    esp_http_client_config_t config = {
        .url = url,
        .event_handler = http_event_handler,
        .method = HTTP_METHOD_POST,
    };

    esp_http_client_handle_t client = esp_http_client_init(&config);
    esp_http_client_set_header(client, "Content-Type", "application/x-www-form-urlencoded");
    esp_http_client_set_post_field(client, post_data, strlen(post_data));

    esp_err_t err = esp_http_client_perform(client);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "心跳发送失败: %s", esp_err_to_name(err));
    }

    esp_http_client_cleanup(client);
    return err;
}

// 上传图片进行识别
cJSON* http_upload_image(uint8_t *image_data, size_t image_len, const char *device_token)
{
    char url[256];
    snprintf(url, sizeof(url), "%s:%d/api/device/upload", API_URL, API_PORT);

    // 构建 multipart 表单数据
    char *boundary = "----JKXTBoundary123456789";
    char header[512];
    snprintf(header, sizeof(header),
        "--%s\r\n"
        "Content-Disposition: form-data; name=\"device_token\"\r\n\r\n"
        "%s\r\n",
        boundary, device_token);

    char *body = malloc(strlen(header) + image_len + 50);
    strcpy(body, header);
    memcpy(body + strlen(header), image_data, image_len);
    sprintf(body + strlen(header) + image_len, "\r\n--%s--\r\n", boundary);

    esp_http_client_config_t config = {
        .url = url,
        .event_handler = http_event_handler,
        .method = HTTP_METHOD_POST,
    };

    esp_http_client_handle_t client = esp_http_client_init(&config);
    char content_type[128];
    snprintf(content_type, sizeof(content_type), "multipart/form-data; boundary=%s", boundary);
    esp_http_client_set_header(client, "Content-Type", content_type);
    esp_http_client_set_post_field(client, body, strlen(header) + image_len + strlen("\r\n--%s--\r\n") + 20);

    char *response = NULL;
    int content_length = 0;
    esp_err_t err = esp_http_client_perform(client);

    if (err == ESP_OK) {
        content_length = esp_http_client_get_content_length(client);
        if (content_length > 0) {
            response = malloc(content_length + 1);
            if (response) {
                int read_len = esp_http_client_read(client, response, content_length);
                response[read_len] = '\0';
            }
        }
    }

    esp_http_client_cleanup(client);
    free(body);

    if (response) {
        cJSON *json = cJSON_Parse(response);
        free(response);
        return json;
    }

    return NULL;
}

// 获取设备配置
cJSON* http_get_config(void)
{
    char url[256];
    snprintf(url, sizeof(url), "%s:%d/api/device/config", API_URL, API_PORT);

    esp_http_client_config_t config = {
        .url = url,
        .event_handler = http_event_handler,
        .method = HTTP_METHOD_GET,
    };

    esp_http_client_handle_t client = esp_http_client_init(&config);
    char *response = NULL;
    esp_err_t err = esp_http_client_perform(client);

    if (err == ESP_OK) {
        int content_length = esp_http_client_get_content_length(client);
        if (content_length > 0) {
            response = malloc(content_length + 1);
            if (response) {
                int read_len = esp_http_client_read(client, response, content_length);
                response[read_len] = '\0';
            }
        }
    }

    esp_http_client_cleanup(client);

    if (response) {
        cJSON *json = cJSON_Parse(response);
        free(response);
        return json;
    }

    return NULL;
}
