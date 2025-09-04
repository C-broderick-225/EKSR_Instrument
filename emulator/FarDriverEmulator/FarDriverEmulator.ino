/*
 * FarDriver BLE Emulator for EKSR Instrument
 * 
 * This emulator implements the FarDriver controller communication protocol
 * used by the EKSR Instrument firmware. The protocol uses 16-byte packets
 * with the following structure:
 * 
 * Packet Format:
 * - Byte 0: Header (0xAA)
 * - Byte 1: Packet Index (0, 1, 4, 13)
 * - Bytes 2-13: Data (12 bytes)
 * - Bytes 14-15: CRC-16/MODBUS Checksum (2 bytes, little-endian)
 * 
 * Packet Types:
 * - Index 0: Main data (RPM, gear, current iq/id)
 * - Index 1: Voltage data
 * - Index 4: Controller temperature
 * - Index 13: Motor temperature and throttle
 * 
 * The emulator provides realistic ebike simulation with dynamic
 * acceleration/deceleration patterns and proper data relationships.
 */

 #include <NimBLEDevice.h>
 #include <math.h>
 
 // Configuration constants
 #define DEVICE_NAME "FarDriver_Emu"
 #define LED_PIN 2
 #define LED_BLINK_INTERVAL 500
 #define PACKET_UPDATE_INTERVAL 20  // Reduced from 30ms to 20ms for faster updates
 #define PACKET_SIZE 16
 #define PACKET_HEADER 0xAA
 
 // Forward declarations
 void restart_ble_advertising();
 
 // Standard Nordic UART Service UUIDs
 #define NUS_SERVICE_UUID        "6E400001-B5A3-F393-E0A9-E50E24DCCA9E"
 #define NUS_TX_CHARACTERISTIC_UUID "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"
 #define NUS_RX_CHARACTERISTIC_UUID "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"
 
 // Custom FarDriver service (for EKSR Instrument compatibility)
 // Based on community findings and common FarDriver BLE implementations
 #define FARDIVER_SERVICE_UUID        "FFE0"
 #define FARDIVER_CHARACTERISTIC_UUID "FFEC"
 
 // Packet indices for different data types
 enum PacketIndex {
     INDEX_MAIN_DATA = 0,    // RPM, gear, current
     INDEX_VOLTAGE = 1,      // Voltage, power
     INDEX_CONTROLLER_TEMP = 4, // Controller temperature
     INDEX_MOTOR_THROTTLE = 13   // Motor temp, throttle
 };
 
 // Ebike simulation state
 struct EbikeState {
     float current_speed;      // Current speed in km/h
     float target_speed;       // Target speed for acceleration/deceleration
     float acceleration_rate;  // Acceleration rate in km/h per second
     float throttle_position;  // Throttle position (0.0 to 1.0)
     bool is_accelerating;     // Whether currently accelerating
     bool is_decelerating;     // Whether currently decelerating
     unsigned long last_update; // Last update timestamp
     int cycle_count;          // Cycle counter for pattern changes
 };
 
 // Global variables
 NimBLECharacteristic* pFarDriverCharacteristic = nullptr;
 NimBLECharacteristic* pNusTxCharacteristic = nullptr;
 NimBLECharacteristic* pNusRxCharacteristic = nullptr;
 bool deviceConnected = false;
 unsigned long lastBlinkTime = 0;
 bool ledState = false;
 
 // Ebike simulation state
 EbikeState ebike_state = {
     .current_speed = 0.0f,
     .target_speed = 0.0f,
     .acceleration_rate = 2.0f,  // 2 km/h per second
     .throttle_position = 0.0f,
     .is_accelerating = false,
     .is_decelerating = false,
     .last_update = 0,
     .cycle_count = 0
 };
 
 // Packet indices array - matches firmware expectations exactly
 static const uint8_t PACKET_INDICES[] = {0, 1, 4, 13};  // Firmware expects these exact indices
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
         
         // Restart advertising when client disconnects
         Serial.println("[Emulator] Client disconnected - restarting BLE advertising...");
         restart_ble_advertising();
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
 
 // CRC-16/MODBUS calculation function
 // Polynomial: 0xA001 (reversed 0x8005)
 // Initial value: 0xFFFF
 // No XOR out
 // No reverse input/output bytes
 uint16_t crc16_modbus(const uint8_t *data, size_t len) {
     uint16_t crc = 0xFFFF;
     for (size_t i = 0; i < len; i++) {
         crc ^= (uint16_t)data[i];
         for (int j = 0; j < 8; j++) {
             if ((crc & 0x0001) != 0) {
                 crc = (crc >> 1) ^ 0xA001;
             } else {
                 crc = crc >> 1;
             }
         }
     }
     return crc;
 }
 
 // Update ebike simulation state
 void update_ebike_simulation() {
     unsigned long current_time = millis();
     float delta_time = (current_time - ebike_state.last_update) / 1000.0f; // Convert to seconds
     ebike_state.last_update = current_time;
     
     // Start accelerating immediately when connected, don't wait for cycle counter
     if (deviceConnected && ebike_state.current_speed < 0.1f) {
         // Start acceleration phase immediately
         ebike_state.target_speed = 25.0f; // Target 25 km/h
         ebike_state.is_accelerating = true;
         ebike_state.is_decelerating = false;
         ebike_state.acceleration_rate = 2.0f; // 2 km/h per second
         ebike_state.cycle_count = 0; // Reset cycle counter
     }
     
     // Update cycle counter every 10 seconds (only after initial acceleration)
     if (current_time % 10000 < 30 && ebike_state.current_speed > 5.0f) { // Within 30ms window
         ebike_state.cycle_count++;
         
         // Change behavior every 30 seconds (3 cycles of 10 seconds each)
         if (ebike_state.cycle_count % 3 == 0) {
             // Start acceleration phase
             ebike_state.target_speed = 25.0f; // Target 25 km/h
             ebike_state.is_accelerating = true;
             ebike_state.is_decelerating = false;
             ebike_state.acceleration_rate = 2.0f; // 2 km/h per second
         } else if (ebike_state.cycle_count % 3 == 1) {
             // Maintain speed phase
             ebike_state.is_accelerating = false;
             ebike_state.is_decelerating = false;
         } else {
             // Deceleration phase
             ebike_state.target_speed = 0.0f;
             ebike_state.is_accelerating = false;
             ebike_state.is_decelerating = true;
             ebike_state.acceleration_rate = 1.5f; // Slower deceleration
         }
     }
     
     // Update speed based on current state
     if (ebike_state.is_accelerating) {
         ebike_state.current_speed += ebike_state.acceleration_rate * delta_time;
         if (ebike_state.current_speed >= ebike_state.target_speed) {
             ebike_state.current_speed = ebike_state.target_speed;
             ebike_state.is_accelerating = false;
         }
         // Increase throttle during acceleration
         ebike_state.throttle_position = min(1.0f, ebike_state.throttle_position + 0.1f * delta_time);
     } else if (ebike_state.is_decelerating) {
         ebike_state.current_speed -= ebike_state.acceleration_rate * delta_time;
         if (ebike_state.current_speed <= ebike_state.target_speed) {
             ebike_state.current_speed = ebike_state.target_speed;
             ebike_state.is_decelerating = false;
         }
         // Decrease throttle during deceleration
         ebike_state.throttle_position = max(0.0f, ebike_state.throttle_position - 0.15f * delta_time);
     } else {
         // Maintain speed - slight throttle adjustments
         ebike_state.throttle_position = 0.3f + 0.1f * sin(current_time / 2000.0f);
     }
     
     // Ensure speed doesn't go negative
     if (ebike_state.current_speed < 0.0f) {
         ebike_state.current_speed = 0.0f;
     }
 }
 
 // Optimized packet generation with dynamic ebike simulation
 void fill_packet(uint8_t* data, uint8_t index, uint32_t timestamp) {
     // Update ebike simulation
     update_ebike_simulation();
     
     // Initialize packet header and clear all bytes
     data[0] = PACKET_HEADER;  // 0xAA header
     data[1] = index;          // Packet index
     
     // Clear remaining bytes (payload and checksum area)
     memset(&data[2], 0, PACKET_SIZE - 2);
     
     switch(index) {
         case 0: {  // Index 0: RPM, gear, current
             // Gear bits (mid position) - bits 2-3 of byte 2 (data[2])
             // Firmware expects: ((pData[2] >> 2) & 0x03) then subtracts 1
             // 00=high, 11=mid, 10=low, (00=Disabled)
             // For mid gear (2), we need 11 in bits 2-3, so 0x0C
             data[2] = 0x0C;  // 11 = mid gear (bits 2-3)
             
             // Calculate RPM based on speed (realistic ebike relationship)
             // Assuming 4:1 gear ratio and 1.35m wheel circumference
             float wheel_rpm = (ebike_state.current_speed * 1000.0f) / (60.0f * 1.35f); // Convert km/h to m/min, then to RPM
             uint16_t rpm = (uint16_t)(wheel_rpm * 4.0f); // Apply gear ratio
             
             // Add some realistic variation
             rpm += (uint16_t)(50 * sin(timestamp / 500.0f));
             
             // Ensure RPM stays in reasonable range
             if (rpm < 50) rpm = 50;  // Lower minimum to allow for low speeds
             if (rpm > 3000) rpm = 3000;
             
             // RPM at bytes 4-5 (firmware expects: ((uint16_t)pData[4] << 8) | pData[5])
             // This means data[4] is MSB, data[5] is LSB (Big-endian)
             data[4] = (rpm >> 8) & 0xFF;
             data[5] = rpm & 0xFF;
             
             // Debug output for speed and RPM
             if (index == 0) { // Only for main data packet
                 Serial.printf("[Emulator] Speed: %.1f km/h, RPM: %d, Throttle: %.1f%%\n", 
                     ebike_state.current_speed, rpm, ebike_state.throttle_position * 100.0f);
             }
             
             // Calculate current values based on throttle and speed
             float power_factor = ebike_state.throttle_position * (ebike_state.current_speed / 25.0f);
             int16_t iq = (int16_t)(300 + 400 * power_factor); // 3A to 7A range
             int16_t id = (int16_t)(100 + 200 * power_factor); // 1A to 3A range
             
             // Add some variation
             iq += (int16_t)(20 * sin(timestamp / 300.0f));
             id += (int16_t)(10 * sin(timestamp / 400.0f));
             
             // Current values at bytes 8-11 (firmware expects: pData[8-9] for iq, pData[10-11] for id)
             // This means data[8] is MSB, data[9] is LSB for iq (Big-endian)
             // This means data[10] is MSB, data[11] is LSB for id (Big-endian)
             data[8] = (iq >> 8) & 0xFF;
             data[9] = iq & 0xFF;
             data[10] = (id >> 8) & 0xFF;
             data[11] = id & 0xFF;
             break;
         }
         
         case 1: {  // Index 1: Voltage
             // Voltage with slight variation based on load
             float voltage_variation = 1.0f - (ebike_state.throttle_position * 0.05f); // 5% drop under load
             uint16_t voltage = (uint16_t)(900 * voltage_variation); // Base 90.0V in 100mV steps
             
             // Voltage at bytes 0-1 (firmware expects: ((uint16_t)pData[0] << 8) | pData[1])
             // This means data[2] is MSB, data[3] is LSB (Big-endian)
             data[2] = (voltage >> 8) & 0xFF;
             data[3] = voltage & 0xFF;
             break;
         }
         
         case 4: {  // Index 4: Controller temperature
             // Temperature increases with power usage
             uint8_t temp = (uint8_t)(35 + ebike_state.throttle_position * 15); // 35-50°C range
             
             // Temperature at byte 2 (firmware expects: (float)pData[2]) - corresponds to data[4]
             data[4] = temp; // Corrected: pData[2] maps to data[4]
             break;
         }
         
         case 13: {  // Index 13: Motor temp, throttle
             // Motor temperature follows controller temp with slight delay
             uint8_t motor_temp = (uint8_t)(40 + ebike_state.throttle_position * 20); // 40-60°C range
             
             // Motor temp at byte 0 (firmware expects: (float)pData[0]) - corresponds to data[2]
             data[2] = motor_temp;
             
             // Convert throttle position to raw ADC value (0-4095)
             uint16_t throttle_raw = (uint16_t)(ebike_state.throttle_position * 4095.0f);
             
             // Throttle at bytes 2-3 (firmware expects: ((uint16_t)pData[2] << 8) | pData[3]) - corresponds to data[4-5]
             // This means data[4] is MSB, data[5] is LSB (Big-endian)
             data[4] = (throttle_raw >> 8) & 0xFF;
             data[5] = throttle_raw & 0xFF;
             break;
         }
     }
     
     // --- CRC-16/MODBUS CHECKSUM CALCULATION ---
     // Calculate CRC-16 over the first 14 bytes (data[0] to data[13])
     uint16_t crc = crc16_modbus(data, 14);
 
     // Place the 2-byte CRC at the end of the packet (little-endian)
     data[14] = crc & 0xFF;          // Low byte
     data[15] = (crc >> 8) & 0xFF;   // High byte
 }
 
 // Print packet data in hex format
 void print_packet_debug(const uint8_t* data, uint8_t index) {
     Serial.printf("[Emulator] Packet %d: ", index);
     for (int i = 0; i < PACKET_SIZE; ++i) {
         Serial.printf("%02X ", data[i]);
     }
     Serial.println();
 }
 
 // Validate packet format matches FarDriver protocol (for debug/self-check)
 void validate_packet_format(const uint8_t* data, uint8_t index) {
     // Check header
     if (data[0] != PACKET_HEADER) {
         Serial.printf("[Emulator] ERROR: Invalid packet header: 0x%02X (expected 0x%02X)\n", data[0], PACKET_HEADER);
     }
     
     // Check index
     if (data[1] != index) {
         Serial.printf("[Emulator] ERROR: Packet index mismatch: %d (expected %d)\n", data[1], index);
     }
     
     // Check packet size
     if (PACKET_SIZE != 16) {
         Serial.printf("[Emulator] ERROR: Invalid packet size: %d (expected 16)\n", PACKET_SIZE);
     }
     
     // Validate CRC-16/MODBUS checksum
     uint16_t calculated_crc = crc16_modbus(data, 14); // Calculate CRC over first 14 bytes
     uint16_t received_crc = ((uint16_t)data[15] << 8) | data[14]; // Reconstruct received CRC (little-endian)
 
     if (received_crc != calculated_crc) {
         Serial.printf("[Emulator] ERROR: CRC mismatch: 0x%04X (calculated 0x%04X)\n", 
                      received_crc, calculated_crc);
     }
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
     
     // Create Nordic UART Service (optional, remove if not needed by EKSR)
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
 
 // Restart BLE advertising with error checking
 void restart_ble_advertising() {
     NimBLEAdvertising* pAdvertising = NimBLEDevice::getAdvertising();
     
     if (pAdvertising) {
         // Stop advertising first if it's running
         if (pAdvertising->isAdvertising()) {
             pAdvertising->stop();
             delay(50); // Small delay to ensure stop completes
         }
         
         // Restart advertising
         if (pAdvertising->start()) {
             Serial.println("[Emulator] BLE advertising restarted successfully");
         } else {
             Serial.println("[Emulator] ERROR: Failed to restart BLE advertising");
         }
     } else {
         Serial.println("[Emulator] ERROR: Could not get advertising object");
     }
 }
 
 void setup() {
     Serial.begin(115200);
     Serial.println("[Emulator] Starting FarDriver BLE Emulator with Dynamic Ebike Simulation");
     
     // Initialize LED
     pinMode(LED_PIN, OUTPUT);
     digitalWrite(LED_PIN, LOW);
     
     // Initialize ebike simulation
     ebike_state.last_update = millis();
     Serial.println("[Emulator] Ebike simulation initialized");
     Serial.println("[Emulator] Pattern: Accelerate to 25 km/h -> Maintain -> Decelerate to 0 km/h (30s cycle)");
     
     // Initialize BLE
     NimBLEDevice::init(DEVICE_NAME);
     NimBLEDevice::setPower(ESP_PWR_LVL_P9);
     NimBLEDevice::setMTU(23); // Default MTU for BLE is 23 bytes, which fits our 16-byte packets.
                               // If larger packets are needed, MTU negotiation would be required.
     
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
         
         // Debug: Print connection status and simulation state every 5 seconds
         static unsigned long lastStatusPrint = 0;
         if (currentTime - lastStatusPrint >= 5000) {
             lastStatusPrint = currentTime;
             Serial.printf("[Emulator] Status - deviceConnected: %s, Server clients: %d\n", 
                 deviceConnected ? "true" : "false", 
                 pServer ? pServer->getConnectedCount() : 0);
             
             // Print ebike simulation state
             Serial.printf("[Emulator] Ebike State - Speed: %.1f km/h, Throttle: %.1f%%, Cycle: %d\n",
                 ebike_state.current_speed,
                 ebike_state.throttle_position * 100.0f,
                 ebike_state.cycle_count);
         }
     }
     
     // Handle LED state based on connection status
     if (!deviceConnected) {
         // Ensure advertising is running when not connected
         if (!NimBLEDevice::getAdvertising()->isAdvertising()) {
             Serial.println("[Emulator] Advertising stopped - restarting...");
             restart_ble_advertising();
         }
         
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
     
     // Validate packet format (can be disabled for production)
     validate_packet_format(data, PACKET_INDICES[packetIndex]);
     
     // Update counters
     packetIndex = (packetIndex + 1) % NUM_PACKET_INDICES;
     timestamp += PACKET_UPDATE_INTERVAL;
     
     delay(PACKET_UPDATE_INTERVAL);
 } 