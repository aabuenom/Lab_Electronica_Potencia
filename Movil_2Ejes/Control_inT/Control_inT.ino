// =====================================================================
// Control_A.ino - Control de pán-tilt con PCA9685 + IR (KY-022)
// Modo inicial: REMOTO (R). Cambia con T, J o R por monitor serie.
// =====================================================================

#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>
#include <IRremote.h>

// ========== CONFIGURACIÓN PCA9685 ==========
Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver(0x40);
#define SERVO_FREQ 50
#define TIC_0     102
#define TIC_180   512

#define CHAN_ROTACION    0
#define CHAN_INCLINACION 1
#define MIN_INCLINACION  21

// ========== CONFIGURACIÓN JOYSTICK ==========
#define PIN_JOY_X   A0
#define PIN_JOY_Y   A1

// ========== CONFIGURACIÓN IR ==========
#define PIN_IR      11
#define PASO_IR     5.0          // grados por pulsación
#define IR_BTN_4    0xF708FF00   // rotación +
#define IR_BTN_6    0xA55AFF00   // rotación -
#define IR_BTN_2    0xE718FF00   // inclinación +
#define IR_BTN_8    0xAD52FF00   // inclinación -

// ========== VARIABLES GLOBALES ==========
float anguloRotacion = 90.0;
float anguloInclinacion = 90.0;
char modoControl = 'R';          // <--- AHORA EMPIEZA EN REMOTO
String inputString = "";

unsigned long lastIrTime = 0;
uint32_t lastIrCode = 0;

// ========== FUNCIONES ==========
int gradosATics(float grados) {
  return (int)map(grados, 0.0, 180.0, TIC_0, TIC_180);
}

void moverServo(int canal, float grados) {
  if (grados < 0.0) grados = 0.0;
  if (grados > 180.0) grados = 180.0;
  int tics = gradosATics(grados);
  if (tics < TIC_0) tics = TIC_0;
  if (tics > TIC_180) tics = TIC_180;
  pwm.setPWM(canal, 0, tics);
}

void leerJoystick() {
  int rawX = analogRead(PIN_JOY_X);
  int rawY = analogRead(PIN_JOY_Y);
  float rot = map(rawX, 0, 1023, 0, 180);
  float inc = map(rawY, 0, 1023, 0, 180);
  if (inc < MIN_INCLINACION) inc = MIN_INCLINACION;
  anguloRotacion = rot;
  anguloInclinacion = inc;
  moverServo(CHAN_ROTACION, anguloRotacion);
  moverServo(CHAN_INCLINACION, anguloInclinacion);
}

void procesarComando(String cmd) {
  cmd.trim();
  if (cmd.length() == 0) return;

  if (cmd.length() == 1) {
    char c = cmd.charAt(0);
    if (c == 'T' || c == 't') {
      modoControl = 'T';
      Serial.println("Modo: Terminal (envía pares rot,inc)");
      return;
    } else if (c == 'J' || c == 'j') {
      modoControl = 'J';
      Serial.println("Modo: Joystick (A0 y A1)");
      leerJoystick();
      return;
    } else if (c == 'R' || c == 'r') {
      modoControl = 'R';
      Serial.println("Modo: Remoto IR (botones 4,6,2,8)");
      return;
    } else if (c == '?') {
      Serial.println("Comandos: T (Terminal), J (Joystick), R (Remoto), ? (ayuda)");
      return;
    } else {
      Serial.println("Comando no válido. Usa T, J, R o ?");
      return;
    }
  }

  // Modo terminal: procesar "rot,inc"
  if (modoControl != 'T') {
    Serial.println("No estás en modo Terminal. Envía 'T' primero.");
    return;
  }

  int sepIndex = cmd.indexOf(',');
  if (sepIndex == -1) sepIndex = cmd.indexOf(' ');
  if (sepIndex == -1) {
    Serial.println("Formato: rotacion,inclinacion (ej: 45,120)");
    return;
  }

  float rot = cmd.substring(0, sepIndex).toFloat();
  float inc = cmd.substring(sepIndex + 1).toFloat();

  if (rot < 0 || rot > 180) {
    Serial.println("Rotación fuera de rango (0-180)");
    return;
  }
  if (inc < MIN_INCLINACION) {
    Serial.print("Inclinación mínima: ");
    Serial.println(MIN_INCLINACION);
    inc = MIN_INCLINACION;
  } else if (inc > 180) {
    Serial.println("Inclinación >180");
    return;
  }

  anguloRotacion = rot;
  anguloInclinacion = inc;
  moverServo(CHAN_ROTACION, anguloRotacion);
  moverServo(CHAN_INCLINACION, anguloInclinacion);

  Serial.print(anguloRotacion);
  Serial.print(",");
  Serial.println(anguloInclinacion);
}

// ========== SETUP ==========
void setup() {
  Serial.begin(9600);
  Serial.println("Iniciando PCA9685...");

  pwm.begin();
  pwm.setPWMFreq(SERVO_FREQ);
  delay(10);

  moverServo(CHAN_ROTACION, 90.0);
  moverServo(CHAN_INCLINACION, 90.0);
  anguloRotacion = 90.0;
  anguloInclinacion = 90.0;

  IrReceiver.begin(PIN_IR, DISABLE_LED_FEEDBACK);

  // Enviar posición inicial
  Serial.print(anguloRotacion);
  Serial.print(",");
  Serial.println(anguloInclinacion);

  Serial.println("Sistema listo.");
  Serial.println("Modo inicial: REMOTO (usa el mando)");
  Serial.println("Envía T, J o R por el monitor para cambiar de modo.");
}

// ========== LOOP ==========
void loop() {
  // --- Procesar comandos serie ---
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n' || c == '\r') {
      if (inputString.length() > 0) {
        procesarComando(inputString);
        inputString = "";
      }
    } else {
      inputString += c;
    }
  }

  // --- Modo Joystick ---
  if (modoControl == 'J') {
    leerJoystick();
    Serial.print(anguloRotacion);
    Serial.print(",");
    Serial.println(anguloInclinacion);
    delay(20);  // pausa para no saturar
  }

  // --- Modo Remoto IR ---
  if (modoControl == 'R') {
    if (IrReceiver.decode()) {
      uint32_t code = IrReceiver.decodedIRData.decodedRawData;
      bool isRepeat = (IrReceiver.decodedIRData.flags & IRDATA_FLAGS_IS_REPEAT);

      // Ignoramos repeticiones y hacemos debounce (150ms)
      if (!isRepeat && code != 0 && (millis() - lastIrTime > 150)) {
        bool moved = false;

        if (code == IR_BTN_4) {
          anguloRotacion += PASO_IR;
          if (anguloRotacion > 180.0) anguloRotacion = 180.0;
          moverServo(CHAN_ROTACION, anguloRotacion);
          moved = true;
        } else if (code == IR_BTN_6) {
          anguloRotacion -= PASO_IR;
          if (anguloRotacion < 0.0) anguloRotacion = 0.0;
          moverServo(CHAN_ROTACION, anguloRotacion);
          moved = true;
        } else if (code == IR_BTN_2) {
          anguloInclinacion += PASO_IR;
          if (anguloInclinacion > 180.0) anguloInclinacion = 180.0;
          moverServo(CHAN_INCLINACION, anguloInclinacion);
          moved = true;
        } else if (code == IR_BTN_8) {
          anguloInclinacion -= PASO_IR;
          if (anguloInclinacion < MIN_INCLINACION) anguloInclinacion = MIN_INCLINACION;
          moverServo(CHAN_INCLINACION, anguloInclinacion);
          moved = true;
        }

        if (moved) {
          Serial.print(anguloRotacion);
          Serial.print(",");
          Serial.println(anguloInclinacion);
          lastIrTime = millis();
        }
      }
      IrReceiver.resume();  // siempre reanudar
    }
  }

  // --- Envío periódico de posición (cada 500ms) para Python ---
  static unsigned long lastSend = 0;
  if (millis() - lastSend > 500) {
    lastSend = millis();
    Serial.print(anguloRotacion);
    Serial.print(",");
    Serial.println(anguloInclinacion);
  }

  delay(10);  // pequeña pausa para estabilizar el I2C y evitar sobrecarga
}
