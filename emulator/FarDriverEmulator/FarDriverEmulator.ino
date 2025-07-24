#include <NimBLEDevice.h>
#include <math.h>

// Configuration constants
#define DEVICE_NAME "FarDriver_Emu"
#define LED_PIN 2
#define LED_BLINK_INTERVAL 500
#define PACKET_UPDATE_INTERVAL 30
#define PACKET_SIZE 16
#define PACKET_HEADER 0xAA

// Standard Nordic UART Service UUIDs
#define NUS_SERVICE_UUID        "6E400001-B5A3-F393-E0A9-E50E24DCCA9E"
#define NUS_TX_CHARACTERISTIC_UUID "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"
#define NUS_RX_CHARACTERISTIC_UUID "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"

// Custom FarDriver service (for EKSR Instrument compatibility)
#define FARDIVER_SERVICE_UUID        "FFE0"
#define FARDIVER_CHARACTERISTIC_UUID "FFEC"

// Packet indices for different data types
enum PacketIndex {
    INDEX_MAIN_DATA = 0,    // RPM, gear, current
    INDEX_VOLTAGE = 1,      // Voltage, power
    INDEX_CONTROLLER_TEMP = 4, // Controller temperature
    INDEX_MOTOR_THROTTLE = 13   // Motor temp, throttle
};

// Global variables
NimBLECharacteristic* pFarDriverCharacteristic = nullptr;
NimBLECharacteristic* pNusTxCharacteristic = nullptr;
NimBLECharacteristic* pNusRxCharacteristic = nullptr;
bool deviceConnected = false;
unsigned long lastBlinkTime = 0;
bool ledState = false;

// Packet indices array - optimized for cache locality
static const uint8_t PACKET_INDICES[] = {INDEX_MAIN_DATA, INDEX_VOLTAGE, INDEX_CONTROLLER_TEMP, INDEX_MOTOR_THROTTLE};
static const size_t NUM_PACKET_INDICES = sizeof(PACKET_INDICES) / sizeof(PACKET_INDICES[0]);

// Server callbacks class
class ServerCallbacks : public NimBLEServerCallbacks {
    void onConnect(NimBLEServer* pServer, ble_gap_conn_desc* desc) {
        Serial.println("[Emulator] onConnect callback triggered");
        deviceConnected = true;
        // Don't set LED here - let the loop() handle it
        Serial.println("[Emulator] Device connected");
        Serial.printf("[Emulator] Client: %02X:%02X:%02X:%02X:%02X:%02X\n", 
            desc->peer_ota_addr.val[5], desc->peer_ota_addr.val[4], desc->peer_ota_addr.val[3],
            desc->peer_ota_addr.val[2], desc->peer_ota_addr.val[1], desc->peer_ota_addr.val[0]);
        Serial.printf("[Emulator] Connection handle: %d\n", desc->conn_handle);
    }
    
    void onDisconnect(NimBLEServer* pServer) {
        Serial.println("[Emulator] onDisconnect callback triggered");
        deviceConnected = false;
        // Don't set LED here - let the loop() handle it
        Serial.println("[Emulator] Device disconnected");
    }
    
    void onMTUChange(uint16_t MTU, ble_gap_conn_desc* desc) {
        Serial.printf("[Emulator] MTU: %d\n", MTU);
    }
};

// Nordic UART Service callbacks
class NusCallbacks : public NimBLECharacteristicCallbacks {
    void onWrite(NimBLECharacteristic* pCharacteristic) {
        std::string rxValue = pCharacteristic->getValue();
        if (!rxValue.empty()) {
            Serial.print("[Emulator] Received: ");
            Serial.println(rxValue.c_str());
        }
    }
};

// Optimized packet generation
void fill_packet(uint8_t* data, uint8_t index, uint32_t timestamp) {
    // Initialize packet header
    data[0] = PACKET_HEADER;
    data[1] = index;
    
    // Clear remaining bytes
    memset(&data[2], 0, PACKET_SIZE - 2);
    
    switch(index) {
        case INDEX_MAIN_DATA: {
            // Gear bits (mid position)
            data[2] = 0x00;
            
            // Simulate RPM with sine wave variation
            uint16_t rpm = 1200 + (uint16_t)(200 * sin(timestamp / 1000.0));
            data[4] = (rpm >> 8) & 0xFF;
            data[5] = rpm & 0xFF;
            
            // Current values (iq, id)
            const int16_t iq = 500; // 5.00A
            const int16_t id = 200; // 2.00A
            data[8] = (iq >> 8) & 0xFF;
            data[9] = iq & 0xFF;
            data[10] = (id >> 8) & 0xFF;
            data[11] = id & 0xFF;
            break;
        }
        
        case INDEX_VOLTAGE: {
            // Voltage: 90.0V (900 in 100mV units)
            const uint16_t voltage = 900;
            data[2] = (voltage >> 8) & 0xFF;
            data[3] = voltage & 0xFF;
            break;
        }
        
        case INDEX_CONTROLLER_TEMP: {
            data[2] = 40; // 40°C controller temperature
            break;
        }
        
        case INDEX_MOTOR_THROTTLE: {
            data[2] = 50; // 50°C motor temperature
            // Throttle at mid position (2048)
            const uint16_t throttle = 2048;
            data[4] = (throttle >> 8) & 0xFF;
            data[5] = throttle & 0xFF;
            break;
        }
    }
}

// Print packet data in hex format
void print_packet_debug(const uint8_t* data, uint8_t index) {
    Serial.printf("[Emulator] Packet %d: ", index);
    for (int i = 0; i < PACKET_SIZE; ++i) {
        Serial.printf("%02X ", data[i]);
    }
    Serial.println();
}

// Initialize BLE services
void setup_ble_services(NimBLEServer* pServer) {
    // Create FarDriver service
    NimBLEService* pFarDriverService = pServer->createService(FARDIVER_SERVICE_UUID);
    pFarDriverCharacteristic = pFarDriverService->createCharacteristic(
        FARDIVER_CHARACTERISTIC_UUID,
        NIMBLE_PROPERTY::NOTIFY | NIMBLE_PROPERTY::WRITE
    );
    pFarDriverService->start();
    
    // Create Nordic UART Service
    NimBLEService* pNusService = pServer->createService(NUS_SERVICE_UUID);
    pNusTxCharacteristic = pNusService->createCharacteristic(
        NUS_TX_CHARACTERISTIC_UUID,
        NIMBLE_PROPERTY::NOTIFY
    );
    
    // Add descriptors for better compatibility
    pNusTxCharacteristic->createDescriptor("2901", NIMBLE_PROPERTY::READ, 20);
    pNusTxCharacteristic->createDescriptor("2902", NIMBLE_PROPERTY::READ | NIMBLE_PROPERTY::WRITE, 2);
    
    pNusRxCharacteristic = pNusService->createCharacteristic(
        NUS_RX_CHARACTERISTIC_UUID,
        NIMBLE_PROPERTY::WRITE | NIMBLE_PROPERTY::WRITE_NR
    );
    pNusRxCharacteristic->setCallbacks(new NusCallbacks());
    pNusService->start();
}

// Setup BLE advertising
void setup_ble_advertising() {
    NimBLEAdvertising* pAdvertising = NimBLEDevice::getAdvertising();
    
    // Configure advertising data
    NimBLEAdvertisementData advData;
    advData.setName(DEVICE_NAME);
    advData.addServiceUUID(FARDIVER_SERVICE_UUID);
    pAdvertising->setAdvertisementData(advData);
    
    // Configure scan response
    NimBLEAdvertisementData scanResponseData;
    scanResponseData.setName(DEVICE_NAME);
    scanResponseData.addServiceUUID(NUS_SERVICE_UUID);
    pAdvertising->setScanResponseData(scanResponseData);
    
    // Set advertising parameters
    pAdvertising->setMinInterval(0x20); // 20ms
    pAdvertising->setMaxInterval(0x40); // 40ms
    
    pAdvertising->start();
}

void setup() {
    Serial.begin(115200);
    Serial.println("[Emulator] Starting FarDriver BLE Emulator");
    
    // Initialize LED
    pinMode(LED_PIN, OUTPUT);
    digitalWrite(LED_PIN, LOW);
    
    // Initialize BLE
    NimBLEDevice::init(DEVICE_NAME);
    NimBLEDevice::setPower(ESP_PWR_LVL_P9);
    NimBLEDevice::setMTU(23);
    
    // Create server and set callbacks
    NimBLEServer* pServer = NimBLEDevice::createServer();
    pServer->setCallbacks(new ServerCallbacks());
    
    // Setup services and advertising
    setup_ble_services(pServer);
    setup_ble_advertising();
    
    // Set initial data on Nordic UART Service
    const uint8_t initData[] = {0x48, 0x65, 0x6C, 0x6C, 0x6F}; // "Hello"
    pNusTxCharacteristic->setValue(initData, sizeof(initData));
    
    Serial.println("[Emulator] BLE services started - LED will flash when advertising");
    Serial.printf("[Emulator] Nordic UART Service: %s\n", NUS_SERVICE_UUID);
    Serial.printf("[Emulator] FarDriver Service: %s\n", FARDIVER_SERVICE_UUID);
}

void loop() {
    static size_t packetIndex = 0;
    static uint32_t timestamp = 0;
    static unsigned long lastConnectionCheck = 0;
    
    // Check connection status periodically
    unsigned long currentTime = millis();
    if (currentTime - lastConnectionCheck >= 1000) { // Check every second
        lastConnectionCheck = currentTime;
        
        // Get the server and check if there are any connected clients
        NimBLEServer* pServer = NimBLEDevice::getServer();
        if (pServer && pServer->getConnectedCount() > 0) {
            if (!deviceConnected) {
                deviceConnected = true;
                // digitalWrite(LED_PIN, HIGH); // Let the centralized logic handle the LED
                Serial.println("[Emulator] Connection detected via server check");
                Serial.printf("[Emulator] Connected clients: %d\n", pServer->getConnectedCount());
                
                // Send a test message immediately
                if (pNusTxCharacteristic) {
                    const char* testMsg = "Hello from FarDriver Emulator!";
                    pNusTxCharacteristic->setValue((uint8_t*)testMsg, strlen(testMsg));
                    pNusTxCharacteristic->notify();
                    Serial.println("[Emulator] Sent initial test message");
                }
            }
        } else {
            if (deviceConnected) {
                deviceConnected = false;
                // digitalWrite(LED_PIN, LOW); // Let the centralized logic handle the LED
                Serial.println("[Emulator] Disconnection detected via server check");
            }
        }
        
        // Debug: Print connection status every 5 seconds
        static unsigned long lastStatusPrint = 0;
        if (currentTime - lastStatusPrint >= 5000) {
            lastStatusPrint = currentTime;
            Serial.printf("[Emulator] Status - deviceConnected: %s, Server clients: %d\n", 
                deviceConnected ? "true" : "false", 
                pServer ? pServer->getConnectedCount() : 0);
        }
    }
    
    // Handle LED state based on connection status
    if (!deviceConnected) {
        // Blink LED when not connected
        if (currentTime - lastBlinkTime >= LED_BLINK_INTERVAL) {
            ledState = !ledState;
            digitalWrite(LED_PIN, ledState);
            lastBlinkTime = currentTime;
        }
        delay(100);
        return;
    } else {
        // When connected, ensure LED stays solid ON
        digitalWrite(LED_PIN, HIGH);
        // Reset blink state for next disconnection
        ledState = false;
    }
    
    // Send data packets when connected
    uint8_t data[PACKET_SIZE];
    fill_packet(data, PACKET_INDICES[packetIndex], timestamp);
    
    // Send to both services
    if (pFarDriverCharacteristic) {
        pFarDriverCharacteristic->setValue(data, PACKET_SIZE);
        pFarDriverCharacteristic->notify();
    }
    
    if (pNusTxCharacteristic) {
        pNusTxCharacteristic->setValue(data, PACKET_SIZE);
        pNusTxCharacteristic->notify();
    }
    
    // Debug output (can be disabled for production)
    print_packet_debug(data, PACKET_INDICES[packetIndex]);
    
    // Update counters
    packetIndex = (packetIndex + 1) % NUM_PACKET_INDICES;
    timestamp += PACKET_UPDATE_INTERVAL;
    
    delay(PACKET_UPDATE_INTERVAL);
} 