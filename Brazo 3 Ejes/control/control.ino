/*
 *  CONTROL DE BRAZO ROBÓTICO DE 3 ARTICULACIONES + GARRA
 *  -----------------------------------------------------
 *  - Dos joysticks analógicos.
 *  - Servos controlados mediante módulo PCA9685 (I2C).
 *  - Monitor serie a 9600 baudios para visualizar ángulos.
 *  - Rango de seguridad: 0° a 180° (evita topes).
 *
 *  Conexiones:
 *    PCA9685: SDA → A4, SCL → A5, VCC → 5V, GND → GND
 *    Joystick1: X → A0 (art1), Y → A1 (garra)
 *    Joystick2: X → A2 (art2), Y → A3 (art3)
 *    Servos en canales: 12 (art1), 13 (art2), 14 (art3), 15 (garra)
 */

#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>   // Librería para PCA9685

// ---------- Definición de pines analógicos para los joysticks ----------
#define JOY1_X  A0   // Eje X del joystick 1 → articulación 1
#define JOY1_Y  A1   // Eje Y del joystick 1 → garra
#define JOY2_X  A2   // Eje X del joystick 2 → articulación 2
#define JOY2_Y  A3   // Eje Y del joystick 2 → articulación 3

// ---------- Canales del PCA9685 para cada servo ----------
#define CH_ART1   12  // base
#define CH_ART2   13  // art 1
#define CH_ART3   14  // art 2
#define CH_GARRA  15  // Garra

// ---------- Valores de pulso (registro de 12 bits) para 0°, 90° y 180° ----------
#define PULSE_0   102   // 0°
#define PULSE_90  307   // 90°
#define PULSE_180 512   // 180°

// ---------- Límites de seguridad para los servos (ángulos en grados) ----------
#define ANG_MIN   0    // Ángulo mínimo (evita fuerzas excesivas)
#define ANG_MAX   180   // Ángulo máximo

// ---------- Cálculo de pulsos correspondientes a ANG_MIN y ANG_MAX ----------
// La relación es lineal: pulso = 102 + ángulo * (512-102)/180
#define PULSE_MIN (PULSE_0 + (ANG_MIN * (PULSE_180 - PULSE_0) / 180))
#define PULSE_MAX PULSE_180   // 512

// ---------- Objeto para manejar el PCA9685 (dirección I2C por defecto 0x40) ----------
Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver(0x40);

// Variables globales para almacenar los ángulos actuales (con decimales)
float anguloArt1, anguloArt2, anguloArt3, anguloGarra;

// ----------------------------------------------------------------------------
//  setup()
//  Inicializa el puerto serie, el PCA9685 y coloca todos los servos en 90°.
// ----------------------------------------------------------------------------
void setup() {
  Serial.begin(9600);
  Serial.println("Iniciando control de brazo robótico con joysticks...");

  // Inicializar el módulo PCA9685
  pwm.begin();
  pwm.setPWMFreq(50);   // Frecuencia de 50 Hz (periodo de 20 ms)
  delay(10);            // Pequeña pausa para estabilización

  // Posición inicial segura: todos los servos a 90° (centro)
  pwm.setPWM(CH_ART1, 0, PULSE_90);
  pwm.setPWM(CH_ART2, 0, PULSE_90);
  pwm.setPWM(CH_ART3, 0, PULSE_90);
  pwm.setPWM(CH_GARRA, 0, PULSE_90);
  delay(100);
}

// ----------------------------------------------------------------------------
//  loop()
//  Lee los joysticks, convierte a ángulos, actualiza los servos y muestra
//  los valores por el monitor serie.
// ----------------------------------------------------------------------------
void loop() {
  // ---------- 1. Lectura de los ejes analógicos (0 a 1023) ----------
  int valJoy1X = analogRead(JOY1_X);
  int valJoy1Y = analogRead(JOY1_Y);
  int valJoy2X = analogRead(JOY2_X);
  int valJoy2Y = analogRead(JOY2_Y);

  // ---------- 2. Mapeo a ángulos (22° a 180°) ----------
  // Se usa la función mapFloat() que permite mapeo con decimales.
  // El orden de los valores de salida (out_min, out_max) se invierte si se desea
  // cambiar el sentido de giro al mover el joystick.
  //
  // Para art1: se ha invertido (out_max=22, out_min=180) de modo que al mover
  // el joystick a la derecha (valor alto) el ángulo aumente (hacia 180°).
  anguloArt1 = mapFloat(valJoy1X, 0, 1023, ANG_MAX, ANG_MIN);
  
  // Garra: se mapea de forma directa (valores bajos → ángulo bajo = cerrado,
  // valores altos → ángulo alto = abierto). Se puede invertir cambiando el orden.
  anguloGarra = mapFloat(valJoy1Y, 0, 1023, ANG_MIN, ANG_MAX);
  
  // Art2: directo (eje X del joystick 2)
  anguloArt2 = mapFloat(valJoy2X, 0, 1023, ANG_MIN, ANG_MAX);
  
  // Art3: directo (eje Y del joystick 2)
  anguloArt3 = mapFloat(valJoy2Y, 0, 1023, ANG_MIN, ANG_MAX);

  // ---------- 3. Limitación por seguridad (por si hay ruido) ----------
  anguloArt1 = constrain(anguloArt1, ANG_MIN, ANG_MAX);
  anguloArt2 = constrain(anguloArt2, ANG_MIN, ANG_MAX);
  anguloArt3 = constrain(anguloArt3, ANG_MIN, ANG_MAX);
  anguloGarra = constrain(anguloGarra, ANG_MIN, ANG_MAX);

  // ---------- 4. Conversión de ángulo a pulso (registro PWM) ----------
  int pulsoArt1 = anguloToPulse(anguloArt1);
  int pulsoArt2 = anguloToPulse(anguloArt2);
  int pulsoArt3 = anguloToPulse(anguloArt3);
  int pulsoGarra = anguloToPulse(anguloGarra);

  // ---------- 5. Envío de las órdenes al PCA9685 ----------
  pwm.setPWM(CH_ART1, 0, pulsoArt1);
  pwm.setPWM(CH_ART2, 0, pulsoArt2);
  pwm.setPWM(CH_ART3, 0, pulsoArt3);
  pwm.setPWM(CH_GARRA, 0, pulsoGarra);

  // ---------- 6. Visualización en el monitor serie ----------
  Serial.print("Art1: ");
  Serial.print(anguloArt1, 1);    // 1 decimal
  Serial.print("°  Art2: ");
  Serial.print(anguloArt2, 1);
  Serial.print("°  Art3: ");
  Serial.print(anguloArt3, 1);
  Serial.print("°  Garra: ");
  Serial.print(anguloGarra, 1);
  Serial.println("°");

  // Pequeño retardo para no saturar el bus I2C y dar tiempo a la lectura
  // Ajustable según la velocidad de respuesta deseada (50 ms ≈ 20 Hz).
  delay(50);
}

// ----------------------------------------------------------------------------
//  mapFloat()
//  Mapea un valor de entrada (x) dentro del rango [in_min, in_max] al rango
//  de salida [out_min, out_max] usando interpolación lineal con precisión float.
//  Útil para trabajar con decimales.
// ----------------------------------------------------------------------------
float mapFloat(float x, float in_min, float in_max, float out_min, float out_max) {
  return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min;
}

// ----------------------------------------------------------------------------
//  anguloToPulse()
//  Convierte un ángulo en grados (dentro del rango 0-180) al valor de registro
//  de 12 bits que debe enviarse al PCA9685.
//  La fórmula se basa en los valores calibrados: 102 ↔ 0°, 512 ↔ 180°.
// ----------------------------------------------------------------------------
int anguloToPulse(float angulo) {
  // Se fuerza la conversión a entero (redondeo natural)
  return (int)(PULSE_0 + (angulo * (PULSE_180 - PULSE_0) / 180.0));
}
