/**
 * @file main.c
 * @brief Kiha firmware entry point for ESP32-S3.
 *
 * Main loop: Capture frame → Check scene change → Send via UDP → Feed watchdog
 * Adaptive frame rate: 10fps (idle) ↔ 30fps (motion detected)
 */

#include <stdio.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"

#include "camera_handler.h"
#include "network_handler.h"
#include "power_manager.h"
#include "frame_protocol.h"

static const char *TAG = "kiha_main";

static uint32_t s_frame_counter = 0;

/**
 * @brief Main frame capture and transmission task.
 */
static void kiha_capture_task(void *arg)
{
    (void)arg;
    uint8_t *frame_buf = NULL;
    uint32_t frame_len = 0;
    uint32_t delay_ms = 1000 / KIHA_FPS_LOW;  /* Start with low fps */

    ESP_LOGI(TAG, "Capture task started");

    while (1) {
        /* Feed watchdog to prevent system reset */
        kiha_power_feed_watchdog();

        /* Check if device should sleep (idle timeout) */
        if (kiha_power_should_sleep()) {
            kiha_power_enter_deep_sleep();
            /* Execution continues here after wake-up */
        }

        /* Adaptive frame rate based on scene change */
        if (kiha_camera_scene_changed()) {
            delay_ms = 1000 / KIHA_FPS_HIGH;  /* Motion → 30fps */
        } else {
            delay_ms = 1000 / KIHA_FPS_LOW;   /* Idle → 10fps */
        }

        /* Capture JPEG frame using hardware encoder */
        esp_err_t err = kiha_camera_capture(&frame_buf, &frame_len);
        if (err != ESP_OK) {
            ESP_LOGE(TAG, "Camera capture failed: %s", esp_err_to_name(err));
            vTaskDelay(pdMS_TO_TICKS(100));
            continue;
        }

        if (frame_len == 0 || frame_buf == NULL) {
            vTaskDelay(pdMS_TO_TICKS(delay_ms));
            continue;
        }

        /* Build frame packet */
        kiha_frame_packet_t packet = {0};
        packet.header.frame_id = s_frame_counter++;
        packet.header.timestamp = (uint32_t)(xTaskGetTickCount() * portTICK_PERIOD_MS);
        packet.header.fragment_info = 0x0100;  /* 1 fragment, index 0 */
        packet.payload_len = (uint16_t)frame_len;

        /* Copy frame data (within static buffer limits) */
        if (frame_len <= MAX_PAYLOAD_SIZE) {
            memcpy(packet.payload, frame_buf, frame_len);

            /* Send via encrypted UDP — no retry on failure */
            kiha_network_send_frame(&packet);
        } else {
            ESP_LOGW(TAG, "Frame too large (%u bytes), dropping", frame_len);
        }

        /* Release camera buffer */
        kiha_camera_release(frame_buf);

        vTaskDelay(pdMS_TO_TICKS(delay_ms));
    }
}

void app_main(void)
{
    ESP_LOGI(TAG, "=== KIHA Smart Glasses Firmware v1.0.0 ===");

    /* Initialize subsystems */
    ESP_ERROR_CHECK(kiha_power_init());
    ESP_ERROR_CHECK(kiha_camera_init());
    ESP_ERROR_CHECK(kiha_network_init());

    ESP_LOGI(TAG, "All subsystems initialized");
    ESP_LOGI(TAG, "Battery: %u%%", kiha_power_get_battery_level());

    /* Start main capture task */
    xTaskCreatePinnedToCore(
        kiha_capture_task,
        "kiha_capture",
        4096,            /* Stack size */
        NULL,            /* Parameters */
        5,               /* Priority */
        NULL,            /* Task handle */
        1                /* Core 1 (leave core 0 for Wi-Fi) */
    );
}
