/*
 *  CONTROL DE BRAZO ROBÓTICO DE 3 ARTICULACIONES + GARRA
 *  -----------------------------------------------------
 *  - Dos joysticks analógicos (modo automático).
 *  - Control manual por teclado numérico desde el monitor serie.
 *  - Servos mediante PCA9685 (canales 12, 13, 14, 15).
 *  - Rango de seguridad: 22° a 180°.
 *  - Paso de ajuste manual: 5°.
 *
 *  Conexiones:
 *    PCA9685: SDA → A4, SCL → A5, VCC → 5V, GND → GND
 *    Joystick1: X → A0 (art1), Y → A1 (garra)
 *    Joystick2: X → A2 (art2), Y → A3 (art3)
 *    Servos en canales: 12 (art1), 13 (art2), 14 (art3), 15 (garra)
 */

#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>

// ---------- Definición de pines analógicos para los joysticks ----------
#define JOY1_X  A0
#define JOY1_Y  A1
#define JOY2_X  A2
#define JOY2_Y  A3

// ---------- Canales del PCA9685 para cada servo ----------
#define CH_ART1   12
#define CH_ART2   13
#define CH_ART3   14
#define CH_GARRA  15

// ---------- Valores de pulso (registro de 12 bits) para 0°, 90° y 180° ----------
#define PULSE_0   102
#define PULSE_90  307
#define PULSE_180 512

// ---------- Límites de seguridad (ángulos en grados) ----------
#define ANG_MIN   22
#define ANG_MAX   180

// ---------- Cálculo de pulsos para los límites ----------
#define PULSE_MIN (PULSE_0 + (ANG_MIN * (PULSE_180 - PULSE_0) / 180))
#define PULSE_MAX PULSE_180

// ---------- Paso de ajuste manual ----------
#define STEP_DEG 5

// ---------- Modos de operación ----------
#define MODO_AUTO   0
#define MODO_MANUAL 1

// ---------- Objeto PCA9685 ----------
Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver(0x40);

// ---------- Variables globales ----------
float angulos[4];          // [0]=art1, [1]=art2, [2]=art3, [3]=garra
int modoActual = MODO_AUTO;

// ----------------------------------------------------------------------------
//  setup()
//  Inicializa puerto serie, PCA9685, coloca todos los servos a 90° y muestra
//  mensaje de inicio con las instrucciones de control.
// ----------------------------------------------------------------------------
void setup() {
  Serial.begin(9600);
  Serial.println(F("=== CONTROL DE BRAZO ROBÓTICO ==="));
  Serial.println(F("Modo automático (joysticks) por defecto."));
  Serial.println(F("Presione 'm' para cambiar a modo manual, y nuevamente 'm' para volver a automático."));
  Serial.println(F("\n--- Modo manual ---"));
  Serial.println(F("  Teclas:"));
  Serial.println(F("    4/6  → Art1 (disminuye/aumenta)"));
  Serial.println(F("    2/8  → Art2 (disminuye/aumenta)"));
  Serial.println(F("    7/9  → Art3 (disminuye/aumenta)"));
  Serial.println(F("    1/3  → Garra (aumenta/disminuye)"));
  Serial.println(F("    5    → Todos a 90°"));
  Serial.println(F("  Paso: 5°"));
  Serial.println(F("----------------------------------------\n"));

  // Inicializar PCA9685
  pwm.begin();
  pwm.setPWMFreq(50);
  delay(10);

  // Poner todos los servos en 90°
  for (int i = 0; i < 4; i++) {
    angulos[i] = 90.0;
  }
  actualizarServos();

  // Mostrar los ángulos iniciales
  mostrarAngulos();
}

// ----------------------------------------------------------------------------
//  loop()
//  Lee joysticks (si modo auto), procesa comandos serie, actualiza servos
//  y muestra ángulos periódicamente.
// ----------------------------------------------------------------------------
void loop() {
  // 1. Procesar comandos del monitor serie
  if (Serial.available() > 0) {
    char c = Serial.read();

    // Si es 'm' o 'M', cambiar de modo
    if (c == 'm' || c == 'M') {
      cambiarModo();
    }
    // Si estamos en modo manual, procesar teclas numéricas
    else if (modoActual == MODO_MANUAL) {
      procesarTeclaManual(c);
    }
    // En modo automático, ignoramos cualquier otra tecla (solo 'm' tiene efecto)
  }

  // 2. Actualizar ángulos según el modo activo
  if (modoActual == MODO_AUTO) {
    leerJoysticks();
  }
  // En modo manual, los ángulos ya se modifican en procesarTeclaManual()
  // y se mantienen hasta nuevo comando.

  // 3. Enviar órdenes a los servos
  actualizarServos();

  // 4. Mostrar los ángulos en el monitor serie (cada ~50 ms)
  //    Se imprime solo si no hay datos en el buffer (para no interferir con la entrada)
  //    Se usa un contador para no saturar.
  static unsigned long lastPrint = 0;
  if (millis() - lastPrint > 50) {
    mostrarAngulos();
    lastPrint = millis();
  }

  // Pequeña pausa para estabilidad
  delay(20);
}

// ----------------------------------------------------------------------------
//  leerJoysticks()
//  Lee los cuatro ejes analógicos y convierte los valores en ángulos dentro
//  del rango [ANG_MIN, ANG_MAX]. Se usa para el modo automático.
// ----------------------------------------------------------------------------
void leerJoysticks() {
  int val1X = analogRead(JOY1_X);
  int val1Y = analogRead(JOY1_Y);
  int val2X = analogRead(JOY2_X);
  int val2Y = analogRead(JOY2_Y);

  // Art1: mapeo invertido (derecha → ángulo mayor)
  angulos[0] = mapFloat(val1X, 0, 1023, ANG_MAX, ANG_MIN);
  // Garra: mapeo directo (arriba → cerrado = ángulo bajo)
  angulos[3] = mapFloat(val1Y, 0, 1023, ANG_MIN, ANG_MAX);
  // Art2 y Art3: mapeo directo
  angulos[1] = mapFloat(val2X, 0, 1023, ANG_MIN, ANG_MAX);
  angulos[2] = mapFloat(val2Y, 0, 1023, ANG_MIN, ANG_MAX);

  // Limitar por si hay ruido
  for (int i = 0; i < 4; i++) {
    angulos[i] = constrain(angulos[i], ANG_MIN, ANG_MAX);
  }
}

// ----------------------------------------------------------------------------
//  procesarTeclaManual(char tecla)
//  Interpreta las teclas numéricas en modo manual y modifica los ángulos
//  correspondientes en pasos de STEP_DEG.
// ----------------------------------------------------------------------------
void procesarTeclaManual(char tecla) {
  switch (tecla) {
    case '1':   // Incrementar garra
      angulos[3] += STEP_DEG;
      break;
    case '3':   // Decrementar garra
      angulos[3] -= STEP_DEG;
      break;
    case '2':   // Decrementar art2
      angulos[1] -= STEP_DEG;
      break;
    case '8':   // Incrementar art2
      angulos[1] += STEP_DEG;
      break;
    case '4':   // Decrementar art1
      angulos[0] -= STEP_DEG;
      break;
    case '6':   // Incrementar art1
      angulos[0] += STEP_DEG;
      break;
    case '7':   // Decrementar art3
      angulos[2] -= STEP_DEG;
      break;
    case '9':   // Incrementar art3
      angulos[2] += STEP_DEG;
      break;
    case '5':   // Resetear todos a 90°
      for (int i = 0; i < 4; i++) {
        angulos[i] = 90.0;
      }
      Serial.println(F(">>> Todos los servos a 90°"));
      break;
    default:
      // Ignorar otras teclas
      return;
  }

  // Limitar todos los ángulos al rango seguro
  for (int i = 0; i < 4; i++) {
    angulos[i] = constrain(angulos[i], ANG_MIN, ANG_MAX);
  }
}

// ----------------------------------------------------------------------------
//  actualizarServos()
//  Convierte los cuatro ángulos a pulsos y los envía al PCA9685.
// ----------------------------------------------------------------------------
void actualizarServos() {
  int pulsoArt1 = anguloToPulse(angulos[0]);
  int pulsoArt2 = anguloToPulse(angulos[1]);
  int pulsoArt3 = anguloToPulse(angulos[2]);
  int pulsoGarra = anguloToPulse(angulos[3]);

  pwm.setPWM(CH_ART1, 0, pulsoArt1);
  pwm.setPWM(CH_ART2, 0, pulsoArt2);
  pwm.setPWM(CH_ART3, 0, pulsoArt3);
  pwm.setPWM(CH_GARRA, 0, pulsoGarra);
}

// ----------------------------------------------------------------------------
//  mostrarAngulos()
//  Envía al monitor serie los cuatro ángulos con un decimal, precedidos
//  por el modo actual.
// ----------------------------------------------------------------------------
void mostrarAngulos() {
  Serial.print(modoActual == MODO_AUTO ? "[AUTO] " : "[MANUAL] ");
  Serial.print("Art1: ");
  Serial.print(angulos[0], 1);
  Serial.print("°  Art2: ");
  Serial.print(angulos[1], 1);
  Serial.print("°  Art3: ");
  Serial.print(angulos[2], 1);
  Serial.print("°  Garra: ");
  Serial.print(angulos[3], 1);
  Serial.println("°");
}

// ----------------------------------------------------------------------------
//  cambiarModo()
//  Alterna entre MODO_AUTO y MODO_MANUAL. Al cambiar, se mantienen los
//  ángulos actuales. En modo automático, los joysticks toman el control
//  inmediatamente (sobrescriben los ángulos en el siguiente ciclo).
// ----------------------------------------------------------------------------
void cambiarModo() {
  if (modoActual == MODO_AUTO) {
    modoActual = MODO_MANUAL;
    Serial.println(F("\n--- MODO MANUAL ACTIVADO ---"));
    Serial.println(F("Use las teclas numéricas indicadas para mover cada articulación."));
    Serial.println(F("Presione 'm' para volver a modo automático.\n"));
  } else {
    modoActual = MODO_AUTO;
    Serial.println(F("\n--- MODO AUTOMÁTICO ACTIVADO ---"));
    Serial.println(F("Los joysticks controlan el brazo. Presione 'm' para manual.\n"));
  }
}

// ----------------------------------------------------------------------------
//  mapFloat()
//  Interpolación lineal con decimales.
// ----------------------------------------------------------------------------
float mapFloat(float x, float in_min, float in_max, float out_min, float out_max) {
  return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min;
}

// ----------------------------------------------------------------------------
//  anguloToPulse()
//  Convierte grados (0-180) al valor de registro PWM de 12 bits.
// ----------------------------------------------------------------------------
int anguloToPulse(float angulo) {
  return (int)(PULSE_0 + (angulo * (PULSE_180 - PULSE_0) / 180.0));
}