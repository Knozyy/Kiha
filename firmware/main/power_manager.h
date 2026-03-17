/**
 * @file power_manager.h
 * @brief Power management module for ESP32-S3.
 *
 * Handles deep sleep, watchdog timer, and battery monitoring.
 */

#ifndef KIHA_POWER_MANAGER_H
#define KIHA_POWER_MANAGER_H

#include <stdint.h>
#include "esp_err.h"

/**
 * @brief Initialize power management (watchdog + sleep timers).
 * @return ESP_OK on success.
 */
esp_err_t kiha_power_init(void);

/**
 * @brief Enter deep sleep mode.
 *
 * Wake-up sources: IMU interrupt or GPIO button (per MASTER.md).
 * Target idle power: < 50mW.
 */
void kiha_power_enter_deep_sleep(void);

/**
 * @brief Feed the hardware watchdog timer.
 *
 * Must be called periodically (< KIHA_WATCHDOG_TIMEOUT_S).
 */
void kiha_power_feed_watchdog(void);

/**
 * @brief Get current battery level.
 * @return Battery percentage (0-100).
 */
uint8_t kiha_power_get_battery_level(void);

/**
 * @brief Check if device should enter deep sleep (idle timeout).
 * @return true if idle time exceeded KIHA_DEEP_SLEEP_TIMEOUT_MS.
 */
bool kiha_power_should_sleep(void);

#endif /* KIHA_POWER_MANAGER_H */
