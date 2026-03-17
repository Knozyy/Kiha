/**
 * @file camera_handler.h
 * @brief Camera capture module for ESP32-S3.
 *
 * Uses hardware JPEG encoder for compression.
 * Implements adaptive frame rate (10-30 fps).
 */

#ifndef KIHA_CAMERA_HANDLER_H
#define KIHA_CAMERA_HANDLER_H

#include <stdint.h>
#include <stdbool.h>
#include "esp_err.h"

/**
 * @brief Initialize the camera module with hardware JPEG encoder.
 * @return ESP_OK on success, error code otherwise.
 */
esp_err_t kiha_camera_init(void);

/**
 * @brief Capture a single JPEG frame.
 *
 * Uses hardware JPEG encoder (not CPU) as per MASTER.md requirement.
 *
 * @param[out] buf     Pointer to receive JPEG data buffer.
 * @param[out] buf_len Length of captured JPEG data.
 * @return ESP_OK on success, error code otherwise.
 */
esp_err_t kiha_camera_capture(uint8_t **buf, uint32_t *buf_len);

/**
 * @brief Release a previously captured frame buffer.
 * @param buf Pointer to the buffer to release.
 */
void kiha_camera_release(uint8_t *buf);

/**
 * @brief Check if scene has changed significantly (for adaptive fps).
 *
 * Compares current frame with previous frame.
 * If diff < KIHA_FRAME_DIFF_THRESHOLD, returns false (no change → low fps).
 *
 * @return true if scene changed enough to warrant high fps.
 */
bool kiha_camera_scene_changed(void);

/**
 * @brief Deinitialize the camera module.
 */
void kiha_camera_deinit(void);

#endif /* KIHA_CAMERA_HANDLER_H */
