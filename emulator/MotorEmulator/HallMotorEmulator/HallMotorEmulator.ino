// --- ESP32 Hall Sensor Emulator for BLDC Motor Controllers ---
// This project provides a simple yet effective way to emulate the Hall sensor 
// signals of a Brushless DC (BLDC) motor using an ESP32 development board.
// Designed for developers and hobbyists who need to bench test motor controllers
// (such as Sabvoton, FarDriver, Kelly, etc.) without a physical motor attached.

#include <Arduino.h>

// Define the GPIO pins connected to the controller's Hall signal lines
#define HALL_A_PIN 25
#define HALL_B_PIN 26
#define HALL_C_PIN 27

// Define the delay between steps. This controls the simulated RPM.
// 20ms is a good starting point, simulating a slow, healthy spin.
// Smaller values (e.g., 10) simulate a faster motor.
// Larger values (e.g., 50) simulate a slower motor.
#define STEP_DELAY_MS 20

// The standard 6-step BLDC commutation sequence for Hall sensors.
// The order of states determines the direction of rotation.
const int hall_sequence[6][3] = {
  {1, 0, 1}, // Step 1
  {0, 0, 1}, // Step 2
  {0, 1, 1}, // Step 3
  {0, 1, 0}, // Step 4
  {1, 1, 0}, // Step 5
  {1, 0, 0}  // Step 6
};

int current_step = 0;
unsigned long step_count = 0;

void setup() {
  Serial.begin(115200);
  Serial.println("=== ESP32 Hall Sensor Emulator for BLDC Motor Controllers ===");
  Serial.println("Starting ESP32 Hall Sensor Emulator...");
  Serial.printf("Step delay: %d ms (simulated RPM: ~%d)\n", 
                STEP_DELAY_MS, 
                60000 / (STEP_DELAY_MS * 6)); // Approximate RPM calculation

  // Set all Hall pins to OUTPUT mode
  pinMode(HALL_A_PIN, OUTPUT);
  pinMode(HALL_B_PIN, OUTPUT);
  pinMode(HALL_C_PIN, OUTPUT);

  Serial.println("Emulator running. Connect to controller and power cycle it.");
  Serial.println("Expected behavior: Controller should power on without Hall fault beeps.");
  Serial.println("Debug output will show current Hall sensor states.");
  Serial.println("---");
}

void loop() {
  // Set the GPIO pins to the values for the current step in the sequence
  digitalWrite(HALL_A_PIN, hall_sequence[current_step][0]);
  digitalWrite(HALL_B_PIN, hall_sequence[current_step][1]);
  digitalWrite(HALL_C_PIN, hall_sequence[current_step][2]);

  // Print the current state to the Serial Monitor for debugging
  Serial.printf("Step %d: Hall A=%d, Hall B=%d, Hall C=%d (Cycle %lu)\n",
                current_step + 1,
                hall_sequence[current_step][0],
                hall_sequence[current_step][1],
                hall_sequence[current_step][2],
                step_count / 6 + 1);

  // Move to the next step in the sequence
  current_step++;
  if (current_step >= 6) {
    current_step = 0; // Reset to the beginning of the sequence
  }
  
  step_count++;

  // Wait for the defined interval before proceeding to the next step
  delay(STEP_DELAY_MS);
}
