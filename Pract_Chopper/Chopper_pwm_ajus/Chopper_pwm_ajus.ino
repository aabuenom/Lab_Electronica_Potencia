#include <PWM.h>                    // Inicia la codificacion
int32_t frequency = 1000;          // Establezca la Frecuencia en Hertz (Hz), se pueden operar frecuencias 
                                    // de entre 10Hz a 300kHz aproximadamente.
int pin_PWM = 3;                   // Pin de modulacion    
int delta_pin = A2; // Pin del Potenciometro para definir delta
int delta;                                  
void setup()
{
  InitTimersSafe();                  
  bool success = SetPinFrequencySafe(pin_PWM, frequency);   //Establece la frecuencia para el pin especificado
  if(success) {              //Si la frecuencia en el pin se configuro correctamente, que se encienda el pin 13.
    pinMode(13, OUTPUT);
    digitalWrite(13, HIGH);    
  }
}
void loop()
{                                               //Potenciometro de 10Kohms para ajustar el DUTY CYCLE (D)
  int sensorValue = analogRead(delta_pin);      //Conectar las dos terminales laterales del potenciometro a +5V y Gnd 
  delta = map(sensorValue, 0, 1023, 0, 255);     //(Lado izquierdo(pin 1) a GND y lado derecho (Pin 3) a +5V
  pwmWrite(pin_PWM, delta);                      //la terminal de enmedio(2) conectarla a una entrada analogica (A5) o la que se desee.
  delay(30);                                    //La salida PWM será el pin digital (9) con respecto a tierra.
}                                               // FIN DE LA CODIFICACION
