/**
 * @file camera_handler.c
 * @brief Camera capture module implementation for ESP32-S3.
 */

#include "camera_handler.h"
#include "frame_protocol.h"
#include "esp_log.h"

static const char *TAG = "kiha_camera";

/* Static frame buffer to minimize dynamic allocation (MASTER.md rule) */
static uint8_t s_frame_buffer[MAX_PAYLOAD_SIZE];
static uint32_t s_frame_buffer_len = 0;

esp_err_t kiha_camera_init(void)
{
    ESP_LOGI(TAG, "Initializing camera with hardware JPEG encoder");

    /* TODO: Refactor - Configure ESP32-S3 camera peripheral
     * 1. Set pixel format to JPEG
     * 2. Configure hardware JPEG encoder
     * 3. Set initial resolution (640x480)
     * 4. Initialize DMA buffers
     */

    return ESP_OK;
}

esp_err_t kiha_camera_capture(uint8_t **buf, uint32_t *buf_len)
{
    if (buf == NULL || buf_len == NULL) {
        return ESP_ERR_INVALID_ARG;
    }

    /* TODO: Refactor - Actual camera capture using esp_camera API */
    *buf = s_frame_buffer;
    *buf_len = s_frame_buffer_len;

    return ESP_OK;
}

void kiha_camera_release(uint8_t *buf)
{
    /* Static buffer — no deallocation needed */
    (void)buf;
}

bool kiha_camera_scene_changed(void)
{
    /* TODO: Refactor - Implement frame diff comparison
     * Compare current frame histogram with previous frame.
     * If diff > KIHA_FRAME_DIFF_THRESHOLD → return true (high fps)
     * Else → return false (low fps to save power)
     */
    return true;
}

void kiha_camera_deinit(void)
{
    ESP_LOGI(TAG, "Camera deinitialized");
    /* TODO: Refactor - Release camera resources */
}
