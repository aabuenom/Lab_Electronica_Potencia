#include <Servo.h>

// Creamos los objetos para controlar los dos servos
Servo servoX;
Servo servoY;

// Definimos los pines analógicos del Joystick
const int pinJoyX = A0;
const int pinJoyY = A1;

// Definimos los pines digitales para los servomotores
const int pinServoX = 9;
const int pinServoY = 10;

// Variables para almacenar los ángulos
int anguloX = 90; // Empezamos en el centro (90 grados)
int anguloY = 90;

// Variable para controlar el modo de funcionamiento (True = Joystick, False = Teclado)
bool modoJoystick = true; 

void setup() {
  servoX.attach(pinServoX);
  servoY.attach(pinServoY);
  
  Serial.begin(9600);
  
  // Mensaje de bienvenida con instrucciones
  Serial.println("=== CONTROL DE SERVOS INICIADO ===");
  Serial.println("Modo actual: JOYSTICK");
  Serial.println("Envía 'S' para modo Serie (Teclado).");
  Serial.println("Envía 'J' para volver a modo Joystick.");
  Serial.println("----------------------------------");
}

void loop() {
  // 1. Revisar si ha llegado algún comando por el Monitor Serie
  if (Serial.available() > 0) {
    char comando = Serial.peek(); // Miramos el primer carácter sin sacarlo del buffer
    
    if (comando == 'S' || comando == 's') {
      modoJoystick = false;
      Serial.read(); // Limpiamos la 'S' del buffer
      Serial.println("\n*** MODO SERIE ACTIVADO ***");
      Serial.println("Escribe los angulos en formato: X,Y (Ejemplo: 45,120)");
      
    } else if (comando == 'J' || comando == 'j') {
      modoJoystick = true;
      Serial.read(); // Limpiamos la 'J' del buffer
      Serial.println("\n*** MODO JOYSTICK ACTIVADO ***");
      
    } else if (!modoJoystick) {
      // Si estamos en modo teclado y llega texto, asumimos que son los ángulos
      // Usamos parseInt() que busca automáticamente el primer número que encuentre
      int nuevoX = Serial.parseInt();
      int nuevoY = Serial.parseInt();
      
      // Limpiamos el salto de línea que queda en el buffer
      while(Serial.available() > 0) { Serial.read(); }
      
      // Validamos que los números estén entre 0 y 180
      if (nuevoX >= 0 && nuevoX <= 180) anguloX = nuevoX;
      if (nuevoY >= 0 && nuevoY <= 180) anguloY = nuevoY;
      
      Serial.print("Nuevos ángulos por teclado -> X: ");
      Serial.print(anguloX);
      Serial.print("° | Y: ");
      Serial.println(anguloY);
      Serial.println("°");
    } else {
      // Si estamos en modo joystick y mandan otra letra, la ignoramos y limpiamos el buffer
      while(Serial.available() > 0) { Serial.read(); }
    }
  }

  // 2. Lógica del Modo Joystick
  if (modoJoystick) {
    int valorJoyX = analogRead(pinJoyX);
    int valorJoyY = analogRead(pinJoyY);
    
    anguloX = map(valorJoyX, 0, 1023, 0, 180);
    anguloY = map(valorJoyY, 0, 1023, 0, 180);
    
    // Imprimimos la posición del joystick en tiempo real (puedes comentar esto si es mucho texto)
    Serial.print("Joystick -> X: ");
    Serial.print(anguloX);
    Serial.print("° | Y: ");
    Serial.println(anguloY);
  }
  
  // 3. Enviar la instrucción de movimiento a los servos (aplica para ambos modos)
  servoX.write(anguloX);
  servoY.write(anguloY);
  
  // 4. Pausa. En modo joystick una pausa corta, en teclado no importa tanto.
  delay(100); 
}
