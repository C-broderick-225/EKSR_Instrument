
#include <Arduino.h>

extern volatile bool is_connected;
extern volatile bool service_found;

void nimble_start(void);
bool connectToServer();
bool nimble_send(uint8_t *pData, uint16_t len);
