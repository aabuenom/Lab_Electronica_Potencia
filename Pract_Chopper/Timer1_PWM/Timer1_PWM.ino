#define f 5000  // Defino mi frecuencia en 5kHz
#define tmuerto_2  80   //tiempo muerto 10us

unsigned int conv = 0;
unsigned int maximo = 0; 

void setup() {
  // put your setup code here, to run once:
  DDRB |= (1 << DDB1) | (1 << DDB2);    // habilita las salidas 9 y 10 como salidas
  //TCCR1A = 0B10000000;  // Timer 1 Como salida PWM FFC y Habilito el pin OC1A como salida PWM
  TCCR1A = 0B10110000;  // Timer 1 Como salida PWM FFC y Habilito el pin OC1A como salida PWM y OC1B con salida PWM negada
  TCCR1B = 0B00010001;  // reloj del timer 16MHz ftmier=fsys / N

  maximo = (16e6/(2*f))-1;   //defino la frecuencia de la PWM fPWM=ftimer/(2*(MAX+1))
  ICR1 =  maximo;
  OCR1A = maximo >> 1;    //Divido maximo entre 2 (shift hacia la derecha)
//  OCR1B = maximo >> 1;    //Divido maximo entre 2 (shift hacia la derecha)

  TIMSK1 = 0B00100000;   //Habilito la interrupcion comparacion con ICR1
  sei();                //Habilita las interrupciones globales

}

void loop() {
  // put your main code here, to run repeatedly:

}

ISR (TIMER1_CAPT_vect){
conv = analogRead(A2);        //leer el valor del potenciometro
conv = map(conv, 0, 1023, 50, maximo);   //ciclo de trabajo entre 0% y 100%
//OCR1A = conv;      //actalizamos el valor del registro OCR1A
OCR1A = conv - tmuerto_2;			//actalizamos el valor del registro OCR1A
OCR1B = conv + tmuerto_2;      //actalizamos el valor del registro OCR1B
}
