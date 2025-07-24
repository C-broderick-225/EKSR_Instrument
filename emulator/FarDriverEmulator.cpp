#include <NimBLEDevice.h>
#include <math.h>

#define SERVICE_UUID        "FFE0"
#define CHARACTERISTIC_UUID "FFEC"

NimBLECharacteristic* pCharacteristic;
bool deviceConnected = false;

class ServerCallbacks : public NimBLEServerCallbacks {
    void onConnect(NimBLEServer* pServer) override {
      deviceConnected = true;
    }
    void onDisconnect(NimBLEServer* pServer) override {
      deviceConnected = false;
    }
};

// Helper to fill a packet for a given index
void fill_packet(uint8_t* data, uint8_t index, uint32_t t) {
    data[0] = 0xAA; // header
    data[1] = index; // index
    // Fill the rest with plausible values
    switch(index) {
        case 0: // Main data: rpm, gear, etc.
            data[2] = 0x00; // gear bits (mid)
            data[3] = 0x00; // reserved
            // Simulate rpm (bytes 4,5)
            {
                uint16_t rpm = 1200 + (uint16_t)(200 * sin(t/1000.0));
                data[4] = (rpm >> 8) & 0xFF;
                data[5] = rpm & 0xFF;
            }
            // reserved
            data[6] = 0x00;
            data[7] = 0x00;
            // iq (bytes 8,9), id (bytes 10,11)
            {
                int16_t iq = 500; // 5.00A
                int16_t id = 200; // 2.00A
                data[8] = (iq >> 8) & 0xFF;
                data[9] = iq & 0xFF;
                data[10] = (id >> 8) & 0xFF;
                data[11] = id & 0xFF;
            }
            // reserved
            data[12] = 0x00;
            data[13] = 0x00;
            data[14] = 0x00;
            data[15] = 0x00;
            break;
        case 1: // Voltage, power, etc.
            {
                // Voltage (bytes 0,1): 900 = 90.0V
                uint16_t voltage = 900;
                data[2] = (voltage >> 8) & 0xFF;
                data[3] = voltage & 0xFF;
                // Fill rest with zeros or plausible values
                for (int i = 4; i < 16; ++i) data[i] = 0;
            }
            break;
        case 4: // Controller temp
            data[2] = 40; // 40 deg C
            for (int i = 3; i < 16; ++i) data[i] = 0;
            break;
        case 13: // Motor temp, throttle
            data[2] = 50; // Motor temp 50C
            // Throttle (bytes 4,5): 2048 (mid)
            data[4] = (2048 >> 8) & 0xFF;
            data[5] = 2048 & 0xFF;
            for (int i = 6; i < 16; ++i) data[i] = 0;
            break;
        default:
            for (int i = 2; i < 16; ++i) data[i] = 0;
            break;
    }
}

void setup() {
  Serial.begin(115200);
  NimBLEDevice::init("FarDriver_Emu");
  NimBLEServer *pServer = NimBLEDevice::createServer();
  pServer->setCallbacks(new ServerCallbacks());

  NimBLEService *pService = pServer->createService(SERVICE_UUID);
  pCharacteristic = pService->createCharacteristic(
                      CHARACTERISTIC_UUID,
                      NIMBLE_PROPERTY::NOTIFY | NIMBLE_PROPERTY::WRITE
                    );
  pService->start();
  NimBLEAdvertising *pAdvertising = NimBLEDevice::getAdvertising();
  pAdvertising->addServiceUUID(SERVICE_UUID);
  pAdvertising->start();
}

void loop() {
  static uint8_t indices[] = {0, 1, 4, 13};
  static size_t idx = 0;
  static uint32_t lastSend = 0;
  static uint32_t t = 0;
  if (deviceConnected) {
    uint8_t data[16] = {0};
    fill_packet(data, indices[idx], t);
    pCharacteristic->setValue(data, 16);
    pCharacteristic->notify();
    idx = (idx + 1) % (sizeof(indices)/sizeof(indices[0]));
    t += 30;
    delay(30); // mimic real controller's update rate
  } else {
    delay(100);
  }
} 