/**
 * @file network_handler.h
 * @brief UDP + DTLS network module for ESP32-S3.
 *
 * Transmits JPEG frames to the relay gateway (Flutter app)
 * using encrypted UDP with DTLS 1.3 (AES-128-GCM).
 */

#ifndef KIHA_NETWORK_HANDLER_H
#define KIHA_NETWORK_HANDLER_H

#include <stdint.h>
#include "esp_err.h"
#include "frame_protocol.h"

/**
 * @brief Initialize network (Wi-Fi + UDP socket + DTLS).
 * @return ESP_OK on success.
 */
esp_err_t kiha_network_init(void);

/**
 * @brief Send a frame packet over encrypted UDP.
 *
 * Applies HMAC-SHA256 and DTLS encryption before sending.
 * No retransmission — dropped frames are acceptable (real-time priority).
 *
 * @param packet The frame packet to transmit.
 * @return ESP_OK on success.
 */
esp_err_t kiha_network_send_frame(const kiha_frame_packet_t *packet);

/**
 * @brief Check Wi-Fi connection status.
 * @return true if connected.
 */
bool kiha_network_is_connected(void);

/**
 * @brief Deinitialize network resources.
 */
void kiha_network_deinit(void);

#endif /* KIHA_NETWORK_HANDLER_H */
