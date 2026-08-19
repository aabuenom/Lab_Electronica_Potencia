#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>

Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver();

// Rango de pulsos (ajustable)
int SERVO_MIN_PULSE = 102;
int SERVO_MAX_PULSE = 512;
const int SERVO_MIN_ANGLE = 0;
const int SERVO_MAX_ANGLE = 180;

int currentChannel = 0;
int currentAngle = 90;
bool joystickMode = true;
int lastPrintedAngle = -1;
int lastPrintedChannel = -1;

void setup() {
  Serial.begin(9600);
  Serial.println("=== Control de servo con PCA9685 (calibrable) ===");
  Serial.println("Comandos (escribir y pulsar Enter):");
  Serial.println("  c <canal>          -> cambiar canal (0-15)");
  Serial.println("  a <ángulo>         -> fijar ángulo (0-180) [modo serie]");
  Serial.println("  j                  -> modo joystick (A0)");
  Serial.println("  pmin <pulso>       -> pulso mínimo (0-4095)");
  Serial.println("  pmax <pulso>       -> pulso máximo (0-4095)");
  Serial.println("  estado             -> mostrar configuración");
  Serial.println("-------------------------------------");

  pwm.begin();
  pwm.setOscillatorFrequency(27000000);
  pwm.setPWMFreq(50);
  delay(10);

  moveServo(currentChannel, currentAngle);
  printStatus();
}

void loop() {
  handleSerialCommands();

  if (joystickMode) {
    int raw = analogRead(A0);
    int angle = map(raw, 0, 1023, SERVO_MIN_ANGLE, SERVO_MAX_ANGLE);
    angle = constrain(angle, SERVO_MIN_ANGLE, SERVO_MAX_ANGLE);
    currentAngle = angle;
  }

  moveServo(currentChannel, currentAngle);

  if (currentAngle != lastPrintedAngle || currentChannel != lastPrintedChannel) {
    printStatus();
    lastPrintedAngle = currentAngle;
    lastPrintedChannel = currentChannel;
  }
  delay(15);
}

// ------------------------------------------------------------
void moveServo(int channel, int angle) {
  angle = constrain(angle, SERVO_MIN_ANGLE, SERVO_MAX_ANGLE);
  int pulse = map(angle, SERVO_MIN_ANGLE, SERVO_MAX_ANGLE, SERVO_MIN_PULSE, SERVO_MAX_PULSE);
  pulse = constrain(pulse, SERVO_MIN_PULSE, SERVO_MAX_PULSE);
  pwm.setPWM(channel, 0, pulse);
}

// ------------------------------------------------------------
void printStatus() {
  int pulse = map(currentAngle, SERVO_MIN_ANGLE, SERVO_MAX_ANGLE, SERVO_MIN_PULSE, SERVO_MAX_PULSE);
  Serial.print("Canal ");
  Serial.print(currentChannel);
  Serial.print(" | Ángulo: ");
  Serial.print(currentAngle);
  Serial.print("° | Pulso: ");
  Serial.print(pulse);
  Serial.print(" | Modo: ");
  Serial.println(joystickMode ? "JOYSTICK" : "SERIE");
}

// ------------------------------------------------------------
void handleSerialCommands() {
  if (!Serial.available()) return;

  // Leer toda la línea hasta '\n' o '\r'
  String line = Serial.readStringUntil('\n');
  line.trim();
  if (line.length() == 0) return;

  // Separar comando y argumento
  int spaceIdx = line.indexOf(' ');
  String cmd = (spaceIdx == -1) ? line : line.substring(0, spaceIdx);
  String arg = (spaceIdx == -1) ? "" : line.substring(spaceIdx + 1);
  cmd.toLowerCase();

  if (cmd == "c") {
    int ch = arg.toInt();
    if (ch >= 0 && ch <= 15) {
      currentChannel = ch;
      Serial.print("Canal cambiado a ");
      Serial.println(ch);
      lastPrintedChannel = -1;
    } else {
      Serial.println("Canal inválido (0-15)");
    }
  }
  else if (cmd == "a") {
    int angle = arg.toInt();
    if (angle >= SERVO_MIN_ANGLE && angle <= SERVO_MAX_ANGLE) {
      joystickMode = false;
      currentAngle = angle;
      Serial.print("Ángulo fijado a ");
      Serial.print(angle);
      Serial.println("° (modo SERIE)");
      lastPrintedAngle = -1;
      moveServo(currentChannel, currentAngle);
      printStatus();
    } else {
      Serial.print("Ángulo debe estar entre ");
      Serial.print(SERVO_MIN_ANGLE);
      Serial.print(" y ");
      Serial.println(SERVO_MAX_ANGLE);
    }
  }
  else if (cmd == "j") {
    joystickMode = true;
    Serial.println("Modo JOYSTICK activado");
    lastPrintedAngle = -1;
  }
  else if (cmd == "pmin") {
    int val = arg.toInt();
    if (val >= 0 && val <= 4095 && val < SERVO_MAX_PULSE) {
      SERVO_MIN_PULSE = val;
      Serial.print("Pulso mínimo ajustado a ");
      Serial.println(val);
      lastPrintedAngle = -1;
    } else {
      Serial.println("Valor inválido (0-4095 y < pmax)");
    }
  }
  else if (cmd == "pmax") {
    int val = arg.toInt();
    if (val >= 0 && val <= 4095 && val > SERVO_MIN_PULSE) {
      SERVO_MAX_PULSE = val;
      Serial.print("Pulso máximo ajustado a ");
      Serial.println(val);
      lastPrintedAngle = -1;
    } else {
      Serial.println("Valor inválido (0-4095 y > pmin)");
    }
  }
  else if (cmd == "estado") {
    Serial.println("=== CONFIGURACIÓN ===");
    Serial.print("Canal: "); Serial.println(currentChannel);
    Serial.print("Pulso mínimo: "); Serial.println(SERVO_MIN_PULSE);
    Serial.print("Pulso máximo: "); Serial.println(SERVO_MAX_PULSE);
    Serial.print("Ángulo actual: "); Serial.println(currentAngle);
    Serial.print("Modo: "); Serial.println(joystickMode ? "JOYSTICK" : "SERIE");
  }
  else {
    Serial.println("Comando no reconocido. Opciones: c, a, j, pmin, pmax, estado");
  }
}
