idf_component_register(
    SRCS "app_main.c"
    INCLUDE_DIRS "."
    REQUIRES esp_wifi esp_event nvs_flash esp_netif esp_http_client log
)

# Set WiFi configuration from project config
#target_compile_options(${COMPONENT_LIB} PRIVATE "-DCONFIG_ESP_WIFI_SSID=\"431\"" "-DCONFIG_ESP_WIFI_PASSWORD=\"88888888\"")