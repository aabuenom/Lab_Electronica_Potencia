#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>

// Instanciamos el objeto para el PCA9685 usando la dirección I2C por defecto (0x40)
Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver();

// Valores de pulso para los servos (Estos varían según el modelo del servo)
// Si tus servos no llegan a 0 o a 180, ajusta estos dos valores:
#define SERVOMIN  102 // Pulso mínimo (equivale a 0 grados)
#define SERVOMAX  512 // Pulso máximo (equivale a 180 grados)

// Definimos los canales del PCA9685 para los servos
const int canalServoX = 0;
const int canalServoY = 1;

// Definimos los pines analógicos del Joystick
const int pinJoyX = A0;
const int pinJoyY = A1;

// Variables para almacenar los ángulos
int anguloX = 90; // Empezamos en el centro
int anguloY = 90;

// Variable de control de modo (True = Joystick, False = Teclado)
bool modoJoystick = true; 

void setup() {
  Serial.begin(9600);
  
  // Iniciamos el módulo PCA9685
  pwm.begin();
  // La frecuencia estándar para los servomotores analógicos es de 50 Hz
  pwm.setPWMFreq(50); 
  
  // Mensaje de bienvenida
  Serial.println("=== CONTROL PCA9685 INICIADO ===");
  Serial.println("Modo actual: JOYSTICK");
  Serial.println("Envía 'S' para modo Serie (Teclado).");
  Serial.println("Envía 'J' para volver a modo Joystick.");
  Serial.println("----------------------------------");
}

// Función auxiliar que convierte los grados (0-180) al pulso que necesita el PCA9685
int calcularPulso(int angulo) {
  return map(angulo, 0, 180, SERVOMIN, SERVOMAX);
}

void loop() {
  // 1. Revisar comandos por el Monitor Serie
  if (Serial.available() > 0) {
    char comando = Serial.peek(); 
    
    if (comando == 'S' || comando == 's') {
      modoJoystick = false;
      Serial.read(); 
      Serial.println("\n*** MODO SERIE ACTIVADO ***");
      Serial.println("Escribe los angulos: X,Y (Ejemplo: 45,120)");
      
    } else if (comando == 'J' || comando == 'j') {
      modoJoystick = true;
      Serial.read(); 
      Serial.println("\n*** MODO JOYSTICK ACTIVADO ***");
      
    } else if (!modoJoystick) {
      int nuevoX = Serial.parseInt();
      int nuevoY = Serial.parseInt();
      
      while(Serial.available() > 0) { Serial.read(); }
      
      if (nuevoX >= 0 && nuevoX <= 180) anguloX = nuevoX;
      if (nuevoY >= 0 && nuevoY <= 180) anguloY = nuevoY;
      
      Serial.print("Teclado -> X: ");
      Serial.print(anguloX);
      Serial.print("° | Y: ");
      Serial.println(anguloY);
    } else {
      while(Serial.available() > 0) { Serial.read(); }
    }
  }

  // 2. Lógica del Modo Joystick
  if (modoJoystick) {
    int valorJoyX = analogRead(pinJoyX);
    int valorJoyY = analogRead(pinJoyY);
    
    anguloX = map(valorJoyX, 0, 1023, 0, 180);
    anguloY = map(valorJoyY, 0, 1023, 0, 180);
    
    // Se han descomentado las siguientes líneas para imprimir la posición:
    Serial.print("Joystick -> X: ");
    Serial.print(anguloX);
    Serial.print("° | Y: ");
    Serial.println(anguloY);
  }
  
  // 3. Enviar la instrucción al PCA9685
  // La función setPWM recibe: (Canal, inicio_pulso, fin_pulso)
  pwm.setPWM(canalServoX, 0, calcularPulso(anguloX));
  pwm.setPWM(canalServoY, 0, calcularPulso(anguloY));
  
  // 4. Pausa de estabilidad
  delay(50); 
}
