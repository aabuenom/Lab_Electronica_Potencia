#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>

// Dirección I2C del PCA9685 (por defecto 0x40)
Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver(0x40);

// Frecuencia para servos (50 Hz)
#define SERVO_FREQ 50

// Mapeo de tics: 0° = 102, 180° = 512 (para pulsos de 0.5 ms a 2.5 ms)
#define TIC_0     102
#define TIC_180   512

// Canales de los servos
#define CHAN_ROTACION      0
#define CHAN_INCLINACION   1

// Límite mínimo para la inclinación
#define MIN_INCLINACION    21

// Ángulos actuales
float anguloRotacion = 90.0;
float anguloInclinacion = 90.0;

// Buffer para comandos seriales
String inputString = "";

void setup() {
  // Velocidad serie a 9600 baudios
  Serial.begin(9600);
  Serial.println("Iniciando PCA9685...");

  pwm.begin();
  pwm.setPWMFreq(SERVO_FREQ);  // 50 Hz para servos
  delay(10);

  // Colocar ambos servos en 90° al inicio
  moverServo(CHAN_ROTACION, anguloRotacion);
  moverServo(CHAN_INCLINACION, anguloInclinacion);

  Serial.println("Listo. Envía ángulos como: rotacion,inclinacion (ej: 45,120)");
  Serial.println("Rango rotación: 0-180°, inclinación: 21-180°.");
}

void loop() {
  // Leer comandos del monitor serie
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
}

void procesarComando(String cmd) {
  cmd.trim();
  if (cmd.length() == 0) return;

  // Buscar separadores: coma o espacio
  int sepIndex = cmd.indexOf(',');
  if (sepIndex == -1) {
    sepIndex = cmd.indexOf(' ');
  }
  if (sepIndex == -1) {
    Serial.println("Formato incorrecto. Usa: rotacion,inclinacion (ej: 45,120)");
    return;
  }

  String strRot = cmd.substring(0, sepIndex);
  String strInc = cmd.substring(sepIndex + 1);
  strRot.trim();
  strInc.trim();

  float rot = strRot.toFloat();
  float inc = strInc.toFloat();

  // Validar rotación (0-180)
  if (rot < 0.0 || rot > 180.0) {
    Serial.println("Ángulo de rotación fuera de rango (0-180).");
    return;
  }

  // Validar inclinación (21-180) y forzar mínimo si es necesario
  if (inc < MIN_INCLINACION) {
    Serial.print("Inclinación mínima es ");
    Serial.print(MIN_INCLINACION);
    Serial.println("°. Forzando a ese valor.");
    inc = MIN_INCLINACION;
  } else if (inc > 180.0) {
    Serial.println("Ángulo de inclinación fuera de rango (>180).");
    return;
  }

  // Actualizar ángulos
  anguloRotacion = rot;
  anguloInclinacion = inc;

  // Mover servos
  moverServo(CHAN_ROTACION, anguloRotacion);
  moverServo(CHAN_INCLINACION, anguloInclinacion);

  // Feedback
  Serial.print("Rotación: ");
  Serial.print(anguloRotacion);
  Serial.print("°, Inclinación: ");
  Serial.print(anguloInclinacion);
  Serial.println("°");
}

// Convierte grados a tics (lineal entre TIC_0 y TIC_180)
int gradosATics(float grados) {
  return (int)map(grados, 0.0, 180.0, TIC_0, TIC_180);
}

// Mueve un servo a un ángulo dado
void moverServo(int canal, float grados) {
  int tics = gradosATics(grados);
  // Asegurar límites (por si acaso)
  if (tics < TIC_0) tics = TIC_0;
  if (tics > TIC_180) tics = TIC_180;
  
  pwm.setPWM(canal, 0, tics);  // on=0, off=tics
}
