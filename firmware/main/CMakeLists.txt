idf_component_register(SRCS "main.c" "wifi_connect.c" "http_client.c" "led_indicator.c" "face_detection.c"
    INCLUDE_DIRS "."
    REQUIRES esp_http_client esp_wifi esp_driver_gpio esp_timer nvs_flash json freertos log espdl esp_camera)
