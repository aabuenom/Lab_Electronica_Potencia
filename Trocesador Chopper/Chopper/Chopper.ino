// Programa Chopper Tipo "A"
int pin_PWM = 6; // Pin de Salida frecuencia 980 Hz
// int pin_PWM = 3; // Pin de Salida frecuencia 490 Hz
int delta_pin = A2; // Pin del Potenciometro para definir delta
int output;
int delta;


void setup() {
  pinMode(pin_PWM, OUTPUT); /* set pin_PWM  as a output pin */
  pinMode(delta_pin,INPUT); /* ser pin A0 as a input pin */
}
void loop() {
  //Reading from potentiometer
  output = analogRead(delta_pin);
  //Mapping the Values between 0 to 255 because we can give output
  //from 0 -> 255 using the analogwrite funtion
  delta = map(output, 0, 1023, 0, 255);
  analogWrite(pin_PWM, delta);
  delay(10);
}
