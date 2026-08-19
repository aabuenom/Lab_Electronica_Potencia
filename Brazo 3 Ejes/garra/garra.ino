#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>

// Dirección I2C del PCA9685 (por defecto 0x40)
#define PCA9685_ADDRESS 0x40

// Canal del servo (0-15)
#define SERVO_CHANNEL 15

// Valores de pulso (escala 0-4095) para los extremos
#define PULSE_0DEG   102
#define PULSE_180DEG 512

Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver(PCA9685_ADDRESS);

int currentAngle = 90;         // Ángulo actual del servo
int lastPrintedAngle = -1;     // Último ángulo impreso (para evitar duplicados)

void setup() {
  Serial.begin(9600);
  pwm.begin();
  pwm.setPWMFreq(50);  // Frecuencia de 50 Hz para servos
  delay(10);

  // Posición inicial: 90° (centro)
  setServoAngle(90);
  lastPrintedAngle = currentAngle;

  // Mensaje de bienvenida e instrucciones
  Serial.println("=== Control de servo por monitor serie ===");
  Serial.println("Comandos:");
  Serial.println("  - Enviar un número (0-180) para posicionar directamente");
  Serial.println("  - Enviar '4' para decrementar 5°");
  Serial.println("  - Enviar '6' para incrementar 5°");
  Serial.print("Ángulo actual: ");
  Serial.println(currentAngle);
}

void loop() {
  if (Serial.available() > 0) {
    String input = Serial.readStringUntil('\n');
    input.trim();  // Elimina espacios y saltos de línea

    if (input.length() > 0) {
      bool commandProcessed = false;

      // Comandos de un solo carácter '4' y '6'
      if (input == "4") {
        currentAngle = constrain(currentAngle - 5, 0, 180);
        setServoAngle(currentAngle);
        commandProcessed = true;
      } 
      else if (input == "6") {
        currentAngle = constrain(currentAngle + 5, 0, 180);
        setServoAngle(currentAngle);
        commandProcessed = true;
      }
      else {
        // Intentar interpretar como número entero
        int angle = input.toInt();
        if (angle >= 0 && angle <= 180) {
          setServoAngle(angle);
          commandProcessed = true;
        }
      }

      // Si no se procesó ningún comando válido, mostrar error
      if (!commandProcessed) {
        Serial.println("Error: comando no válido. Use un número (0-180), '4' o '6'.");
      }
    }
  }

  // Imprimir el ángulo si ha cambiado (por si se modificó desde setServoAngle)
  if (currentAngle != lastPrintedAngle) {
    Serial.print("Ángulo: ");
    Serial.println(currentAngle);
    lastPrintedAngle = currentAngle;
  }
}

// Función que convierte ángulo a pulso y lo envía al PCA9685
void setServoAngle(int angle) {
  // Mapeo lineal: 0° -> 102, 180° -> 512
  int pulse = map(angle, 0, 180, PULSE_0DEG, PULSE_180DEG);
  pulse = constrain(pulse, PULSE_0DEG, PULSE_180DEG);
  pwm.setPWM(SERVO_CHANNEL, 0, pulse);
  currentAngle = angle;   // Actualiza la variable global
}
