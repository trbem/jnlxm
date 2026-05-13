idf_component_register(
    SRC_DIRS "."
    INCLUDE_DIRS "."
    REQUIRES esp_wifi esp_netif esp_event nvs_flash esp_http_server lwip
)

# Set WiFi configuration from project config
target_compile_options(${COMPONENT_LIB} PRIVATE "-DCONFIG_ESP_WIFI_SSID=\"431\"" "-DCONFIG_ESP_WIFI_PASSWORD=\"88888888\"")