// Feather ESP32 V2 — Standalone Motor Control + Serial Interface + Homing Task
// - No BLE
// - Responds to serial motor commands: S (speed), T (toggle dir), X (stop), L (home)
// - Prints current motor angle periodically
// - Outputs CSV header for compatibility with GUI/recording tools

#include <Arduino.h>
#include <AccelStepper.h>

// ======================== USER CONFIG ========================
#define STEP_PIN    26
#define DIR_PIN     25
#define PROBE_PIN   14  // digital probe: LOW = present, HIGH = not present

const int motorInterfaceType = 1;
AccelStepper stepper(motorInterfaceType, STEP_PIN, DIR_PIN);

// ============== MOTOR STATE / SERIAL COMMANDS ===============
char command;
int  value;
bool running     = false;
bool dirInverted = false;
volatile bool homing = false;

// ================== BASIC STEPPER HELPERS ====================
static inline void take_one_step(bool direction) {
  digitalWrite(DIR_PIN, direction);
  digitalWrite(STEP_PIN, HIGH);
  delayMicroseconds(2000);
  digitalWrite(STEP_PIN, LOW);
  delayMicroseconds(2000);
}

bool is_probe_present() {
  return digitalRead(PROBE_PIN) == LOW;  // LOW = probe triggered
}

// =================== HOMING TASK (CORE 0) ===================
TaskHandle_t homingTaskHandle = nullptr;

void homingTask(void* arg) {
  Serial.printf("[HOMING] Task start on core %d\n", xPortGetCoreID());

  long steps_taken = 0;
  bool on_mark = false, was_on_mark = false;
  const bool homeDir = false;  // direction toward probe

  while (homing) {
    take_one_step(homeDir);
    on_mark = is_probe_present();

    if (on_mark && !was_on_mark) {
      steps_taken = 0;
    } else if (!on_mark && was_on_mark) {
      long steps_to_go_back = max(1L, steps_taken / 2);
      Serial.printf("[HOMING] Mark passed. Backing up %ld steps…\n", steps_to_go_back);
      for (long i = 0; i < steps_to_go_back && homing; i++) {
        take_one_step(!homeDir);
        vTaskDelay(pdMS_TO_TICKS(1));  // yield
      }
      stepper.setCurrentPosition(0);
      Serial.println("[HOMING] Complete. Origin set.");
      homing = false;
      break;
    }

    if (on_mark) steps_taken++;
    was_on_mark = on_mark;

    vTaskDelay(pdMS_TO_TICKS(1));
  }

  Serial.println("[HOMING] Task exit");
  vTaskDelete(nullptr);
}

// ========================= SETUP ============================
void setup() {
  Serial.begin(115200);
  delay(200);
  Serial.println("\n[INIT] Feather ESP32 V2 — Standalone Motor Control");
  Serial.println("seq,ms,ch0,ch2,ch3"); // keep same CSV header for GUI

  stepper.setMaxSpeed(40000.0);
  stepper.setAcceleration(50000.0);
  stepper.setCurrentPosition(0);

  pinMode(DIR_PIN, OUTPUT);
  pinMode(STEP_PIN, OUTPUT);
  digitalWrite(DIR_PIN, LOW);
  digitalWrite(STEP_PIN, LOW);

  pinMode(PROBE_PIN, INPUT);
}

// ========================== LOOP ============================
void loop() {
  // --- Serial motor commands ---
  if (!homing && Serial.available() > 0) {
    command = Serial.read();
    if (command == 'S') {
      while (Serial.available() == 0) {}
      value = Serial.parseInt();
      stepper.setSpeed(value);
      running = true;
    } else if (command == 'T') {
      dirInverted = !dirInverted;
      stepper.setPinsInverted(dirInverted, false, false);
      Serial.println("[MOTOR] Direction toggled.");
    } else if (command == 'X') {
      stepper.stop();
      running = false;
      Serial.println("[MOTOR] Stopped.");
    } else if (command == 'L') {
      if (!homing) {
        homing = true;
        Serial.println("[HOMING] Starting…");
        xTaskCreatePinnedToCore(homingTask, "homingTask", 4096, nullptr, 2, &homingTaskHandle, 0);
      }
    }
  }

  // --- Run motor ---
  uint32_t now = millis();
  if (running && !homing) {
    stepper.runSpeed();

    static uint32_t last_probe_ms = 0;
    if (now - last_probe_ms >= 500) {
      last_probe_ms = now;
      long pos = stepper.currentPosition();
      float stepsPerRev = 6400.0;
      float degrees = fmod(pos, stepsPerRev) * (360.0 / stepsPerRev);
      Serial.println(degrees);
    }
  } else {
    vTaskDelay(pdMS_TO_TICKS(2));
  }
}
