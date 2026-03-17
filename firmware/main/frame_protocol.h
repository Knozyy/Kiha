/**
 * @file frame_protocol.h
 * @brief Kiha frame packet format definitions.
 *
 * Packet format (UDP payload):
 * [frame_id: 4B] [timestamp: 4B] [fragment_info: 2B] [HMAC: 32B] [payload: variable]
 */

#ifndef KIHA_FRAME_PROTOCOL_H
#define KIHA_FRAME_PROTOCOL_H

#include <stdint.h>

/* --- Packet Format Constants --- */
#define KIHA_FRAME_ID_SIZE       4
#define KIHA_TIMESTAMP_SIZE      4
#define KIHA_FRAGMENT_INFO_SIZE  2
#define KIHA_HMAC_SIZE           32
#define KIHA_HEADER_SIZE         (KIHA_FRAME_ID_SIZE + KIHA_TIMESTAMP_SIZE + \
                                  KIHA_FRAGMENT_INFO_SIZE + KIHA_HMAC_SIZE)

/* --- Frame Limits --- */
#define MAX_FRAME_SIZE           65507  /* Max UDP payload */
#define MAX_PAYLOAD_SIZE         (MAX_FRAME_SIZE - KIHA_HEADER_SIZE)
#define MAX_FRAGMENTS_PER_FRAME  16

/* --- Adaptive Frame Rate --- */
#define KIHA_FPS_HIGH            30
#define KIHA_FPS_LOW             10
#define KIHA_FRAME_DIFF_THRESHOLD 0.05f  /* 5% pixel change threshold */

/* --- Power Management --- */
#define KIHA_DEEP_SLEEP_TIMEOUT_MS  30000  /* 30 seconds idle → deep sleep */
#define KIHA_WATCHDOG_TIMEOUT_S     10     /* Hardware watchdog: 10 seconds */

/**
 * @brief Frame packet header structure (packed, no padding).
 */
typedef struct __attribute__((packed)) {
    uint32_t frame_id;
    uint32_t timestamp;
    uint16_t fragment_info;  /* [total_frags: 4bit] [frag_index: 4bit] [reserved: 8bit] */
    uint8_t  hmac[KIHA_HMAC_SIZE];
} kiha_frame_header_t;

/**
 * @brief Complete frame packet (header + payload).
 */
typedef struct {
    kiha_frame_header_t header;
    uint8_t             payload[MAX_PAYLOAD_SIZE];
    uint16_t            payload_len;
} kiha_frame_packet_t;

#endif /* KIHA_FRAME_PROTOCOL_H */
