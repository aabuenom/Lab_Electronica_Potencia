/*
 *  CONTROL DE BRAZO ROBÓTICO CON JOYSTICKS Y CONTROL MANUAL POR SERVO
 *  ------------------------------------------------------------------
 *  - Cada servo puede estar en modo automático (joystick) o manual.
 *  - Comandos serie:
 *      S:ang1,ang2,ang3,ang4   → fija ángulos (solo para servos en manual)
 *      C:idx,modo              → cambia modo de un servo (idx 0-3, modo 0=auto, 1=manual)
 *      m                       → alterna todos los modos (global)
 *      teclas 1-9              → control manual (solo para servos en manual)
 *  - Envía ángulos en formato A:ang1,ang2,ang3,ang4
 *  - PCA9685 en canales 12-15.
 *  - Rango seguro: 22° a 180°.
 *  - Velocidad serie: 115200 baudios.
 */

#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>

// ---------- Pines analógicos para joysticks ----------
#define JOY1_X  A0
#define JOY1_Y  A1
#define JOY2_X  A2
#define JOY2_Y  A3

// ---------- Canales del PCA9685 ----------
#define CH_ART1   12
#define CH_ART2   13
#define CH_ART3   14
#define CH_GARRA  15

// ---------- Valores de pulso para 0°, 90° y 180° ----------
#define PULSE_0   102
#define PULSE_90  307
#define PULSE_180 512

// ---------- Límites de seguridad ----------
#define ANG_MIN   22      // Límite inferior real de los servos (22°)
#define ANG_MAX   180
#define STEP_DEG  5

// ---------- Modos de operación ----------
#define MODO_AUTO   0
#define MODO_MANUAL 1

// ---------- Objeto PCA9685 ----------
Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver(0x40);

// Variables globales
float angulos[4];          // [0]=art1, [1]=art2, [2]=art3, [3]=garra
int modos[4];              // 0=auto, 1=manual

// ----------------------------------------------------------------------------
//  setup()
//  Inicializa puerto serie, PCA9685 y coloca los servos en 90°.
// ----------------------------------------------------------------------------
void setup() {
  Serial.begin(115200);
  Serial.println(F("BRAZO ROBOTICO LISTO - MODO POR SERVO"));

  pwm.begin();
  pwm.setPWMFreq(50);
  delay(10);

  for (int i = 0; i < 4; i++) {
    angulos[i] = 90.0;
    modos[i] = MODO_AUTO;   // Inicialmente todos en automático
  }
  actualizarServos();
  enviarAngulos();
}

// ----------------------------------------------------------------------------
//  loop()
//  Lee comandos serie, actualiza ángulos según el modo, envía datos.
// ----------------------------------------------------------------------------
void loop() {
  if (Serial.available() > 0) {
    char c = Serial.read();

    // ---- Comando S: fijar ángulos (solo para servos en manual) ----
    if (c == 'S' || c == 's') {
      while (Serial.available() && Serial.read() != ':');   // esperar ':'
      float a1 = Serial.parseFloat();
      float a2 = Serial.parseFloat();
      float a3 = Serial.parseFloat();
      float a4 = Serial.parseFloat();

      if (!isnan(a1) && !isnan(a2) && !isnan(a3) && !isnan(a4)) {
        float vals[4] = {a1, a2, a3, a4};
        for (int i = 0; i < 4; i++) {
          if (modos[i] == MODO_MANUAL) {
            angulos[i] = constrain(vals[i], ANG_MIN, ANG_MAX);
          }
        }
      }
      while (Serial.available() && Serial.read() != '\n');   // limpiar buffer
    }
    // ---- Comando C: cambiar modo individual ----
    else if (c == 'C' || c == 'c') {
      while (Serial.available() && Serial.read() != ':');
      int idx = Serial.parseInt();
      if (Serial.read() == ',') {   // esperar la coma
        int modo = Serial.parseInt();
        if (idx >= 0 && idx < 4 && (modo == MODO_AUTO || modo == MODO_MANUAL)) {
          modos[idx] = modo;
          Serial.print(F("Modo servo "));
          Serial.print(idx);
          Serial.print(F(" -> "));
          Serial.println(modo == MODO_AUTO ? "AUTO" : "MANUAL");
        }
      }
      while (Serial.available() && Serial.read() != '\n');
    }
    // ---- Comando m: alternar todos los modos ----
    else if (c == 'm' || c == 'M') {
      cambiarModoGlobal();
    }
    // ---- Teclas para control manual ----
    else if (c >= '1' && c <= '9') {
      procesarTeclaManual(c);
    }
  }

  // Leer joysticks solo para servos en modo automático
  if (hayAlgunAuto()) {
    leerJoysticks();
  }

  actualizarServos();
  enviarAngulos();
  delay(10);
}

// ----------------------------------------------------------------------------
//  Funciones auxiliares de estado
// ----------------------------------------------------------------------------
bool hayAlgunAuto() {
  for (int i = 0; i < 4; i++) {
    if (modos[i] == MODO_AUTO) return true;
  }
  return false;
}

// ----------------------------------------------------------------------------
//  leerJoysticks()
//  Lee los ejes analógicos y mapea a ángulos SOLO para servos en AUTO.
// ----------------------------------------------------------------------------
void leerJoysticks() {
  int val1X = analogRead(JOY1_X);
  int val1Y = analogRead(JOY1_Y);
  int val2X = analogRead(JOY2_X);
  int val2Y = analogRead(JOY2_Y);

  float temp[4];
  temp[0] = mapFloat(val1X, 0, 1023, ANG_MAX, ANG_MIN);
  temp[3] = mapFloat(val1Y, 0, 1023, ANG_MIN, ANG_MAX);
  temp[1] = mapFloat(val2X, 0, 1023, ANG_MIN, ANG_MAX);
  temp[2] = mapFloat(val2Y, 0, 1023, ANG_MIN, ANG_MAX);

  for (int i = 0; i < 4; i++) {
    if (modos[i] == MODO_AUTO) {
      angulos[i] = constrain(temp[i], ANG_MIN, ANG_MAX);
    }
  }
}

// ----------------------------------------------------------------------------
//  procesarTeclaManual(char tecla)
//  Modifica ángulos en pasos de 5° SOLO para servos en MANUAL.
// ----------------------------------------------------------------------------
void procesarTeclaManual(char tecla) {
  int idx = -1;
  float delta = 0;

  switch (tecla) {
    case '1': idx = 3; delta = +STEP_DEG; break;   // garra +
    case '3': idx = 3; delta = -STEP_DEG; break;   // garra -
    case '2': idx = 1; delta = -STEP_DEG; break;   // art2 -
    case '8': idx = 1; delta = +STEP_DEG; break;   // art2 +
    case '4': idx = 0; delta = -STEP_DEG; break;   // art1 -
    case '6': idx = 0; delta = +STEP_DEG; break;   // art1 +
    case '7': idx = 2; delta = -STEP_DEG; break;   // art3 -
    case '9': idx = 2; delta = +STEP_DEG; break;   // art3 +
    case '5': // reset todos a 90° (solo si están en manual)
      for (int i = 0; i < 4; i++) {
        if (modos[i] == MODO_MANUAL) {
          angulos[i] = 90.0;
        }
      }
      Serial.println(F("RESET A 90° (solo manuales)"));
      return;
    default:
      return;
  }

  if (idx >= 0 && modos[idx] == MODO_MANUAL) {
    angulos[idx] = constrain(angulos[idx] + delta, ANG_MIN, ANG_MAX);
  }
}

// ----------------------------------------------------------------------------
//  cambiarModoGlobal()
//  Alterna todos los modos (0↔1) y envía mensaje.
// ----------------------------------------------------------------------------
void cambiarModoGlobal() {
  for (int i = 0; i < 4; i++) {
    modos[i] = (modos[i] == MODO_AUTO) ? MODO_MANUAL : MODO_AUTO;
  }
  Serial.println(F("MODOS GLOBAL ALTERNADOS"));
}

// ----------------------------------------------------------------------------
//  actualizarServos()
//  Convierte ángulos a pulsos y los envía al PCA9685.
// ----------------------------------------------------------------------------
void actualizarServos() {
  int pulsos[4];
  for (int i = 0; i < 4; i++) {
    pulsos[i] = anguloToPulse(angulos[i]);
  }
  pwm.setPWM(CH_ART1, 0, pulsos[0]);
  pwm.setPWM(CH_ART2, 0, pulsos[1]);
  pwm.setPWM(CH_ART3, 0, pulsos[2]);
  pwm.setPWM(CH_GARRA, 0, pulsos[3]);
}

// ----------------------------------------------------------------------------
//  enviarAngulos()
//  Envía los ángulos por serial en formato: A:val1,val2,val3,val4
// ----------------------------------------------------------------------------
void enviarAngulos() {
  Serial.print("A:");
  Serial.print(angulos[0], 1);
  Serial.print(",");
  Serial.print(angulos[1], 1);
  Serial.print(",");
  Serial.print(angulos[2], 1);
  Serial.print(",");
  Serial.println(angulos[3], 1);
}

// ----------------------------------------------------------------------------
//  mapFloat()   - Mapeo lineal con decimales
//  anguloToPulse() - Convierte grados a registro PWM
// ----------------------------------------------------------------------------
float mapFloat(float x, float in_min, float in_max, float out_min, float out_max) {
  return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min;
}

int anguloToPulse(float angulo) {
  return (int)(PULSE_0 + (angulo * (PULSE_180 - PULSE_0) / 180.0));
}
