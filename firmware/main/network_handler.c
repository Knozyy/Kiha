/**
 * @file network_handler.c
 * @brief UDP + DTLS network module implementation.
 */

#include "network_handler.h"
#include "esp_log.h"

static const char *TAG = "kiha_network";

esp_err_t kiha_network_init(void)
{
    ESP_LOGI(TAG, "Initializing network (Wi-Fi + UDP + DTLS)");

    /* TODO: Refactor - Implementation steps:
     * 1. Initialize Wi-Fi STA mode
     * 2. Create UDP socket
     * 3. Initialize DTLS 1.3 context with PSK
     * 4. Use ESP32 hardware AES acceleration for AES-128-GCM
     */

    return ESP_OK;
}

esp_err_t kiha_network_send_frame(const kiha_frame_packet_t *packet)
{
    if (packet == NULL) {
        return ESP_ERR_INVALID_ARG;
    }

    if (!kiha_network_is_connected()) {
        ESP_LOGW(TAG, "Network not connected, dropping frame %u",
                 packet->header.frame_id);
        return ESP_ERR_INVALID_STATE;
    }

    /* TODO: Refactor - Implementation steps:
     * 1. Compute HMAC-SHA256 over payload
     * 2. Fill header.hmac field
     * 3. Encrypt with DTLS (AES-128-GCM)
     * 4. Send via UDP — NO retransmission on failure
     */

    ESP_LOGD(TAG, "Frame %u sent (%u bytes)",
             packet->header.frame_id, packet->payload_len);

    return ESP_OK;
}

bool kiha_network_is_connected(void)
{
    /* TODO: Refactor - Check actual Wi-Fi connection status */
    return false;
}

void kiha_network_deinit(void)
{
    ESP_LOGI(TAG, "Network deinitialized");
    /* TODO: Refactor - Close socket, tear down DTLS, disconnect Wi-Fi */
}
