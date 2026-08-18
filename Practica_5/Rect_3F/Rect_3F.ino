/*TRIAC control with potentiometer; author: ELECTRONOOBS 
 * Subscribe: http://www.youtube.com/c/ELECTRONOOBS
 * Tutorial: http://www.ELECTRONOOBS.com/eng_circuitos_tut32.php
 * Thank you
*/
int detectado = 0;
int valor=0;
int last_CH1_state = 0;
unsigned k=0; // Contadores
int ks=0;     // semiciclo operativo
// Pines de control para cada fase del convertidor
int fa=11;
int fb=10;
int fc=9;

void setup() {
  /*
   * Port registers allow for lower-level and faster manipulation of the i/o pins of the microcontroller on an Arduino board. 
   * The chips used on the Arduino board (the ATmega8 and ATmega168) have three ports:
     -B (digital pin 8 to 13)
     -C (analog input pins)
     -D (digital pins 0 to 7)   
  //All Arduino (Atmega) digital pins are inputs when you begin...
  */  
   
  PCICR |= (1 << PCIE0);    //enable PCMSK0 scan                                                 
  PCMSK0 |= (1 << PCINT0);  //Set pin D8 trigger an interrupt on state change. Input from optocoupler
  pinMode(fa, OUTPUT); // Definir D3 como salida fase a
  pinMode(fb, OUTPUT); // Definir D4 como salida fase b
  pinMode(fc, OUTPUT); // Definir D4 como salida fase c
//  Serial.begin(9600);

}

void loop() {
   //Read the value of the pot and map it from 10 to 10.000 us. AC frequency is 50Hz, so period is 20ms. We want to control the power
   //of each half period, so the maximum is 10ms or 10.000us. In my case I've maped it up to 7.200us since 10.000 was too much
   //Serial.println(ks);
   valor = map(analogRead(A2),0,1024,5200,10); // Mapeo Orden de Disparo
    if (detectado)
    {      
        if (ks){
        delayMicroseconds(valor); // Orden de disparo
        digitalWrite(fa, HIGH);  // Encender el pin fase a
        delayMicroseconds(100);
        digitalWrite(fa, LOW);
        delay(5); // Retardo de 5.555 ms
        delayMicroseconds(455);
        digitalWrite(fb, HIGH); // Encender el pin fase b
        delayMicroseconds(100);
        digitalWrite(fb, LOW);
        delay(5); // Retardo de 5.555 ms
        delayMicroseconds(455);
        digitalWrite(fc, HIGH); // Encender el pin fase  c
        delayMicroseconds(100);
        digitalWrite(fc, LOW);
        ks=0;
        }
        else {
        digitalWrite(fa, LOW);  // Apagar el pin fase b
        digitalWrite(fb, LOW); // Apagar el pin fase b
        digitalWrite(fc, LOW); // Apagar el pin fase c
        }
        }
      } 






//This is the interruption routine para disparo
//----------------------------------------------

ISR(PCINT0_vect){
  /////////////////////////////////////               //Input from optocoupler
  if(PINB & B00000001){                               //We make an AND with the pin state register, We verify if pin 8 is HIGH???
    if(last_CH1_state == 0){                          //If the last state was 0, then we have a state change...
      detectado=1;                                    //We haev detected a state change!
      k=k+1;
      ks=k % 2;   // Determina el semiciclo de trabajo 
    }
  }
  else if(last_CH1_state == 1){                       //If pin 8 is LOW and the last state was HIGH then we have a state change      
    detectado=1;                                      //We haev detected a state change!
    k=k+1;
    ks=k % 2;   // Determina el semiciclo de trabajo 
    last_CH1_state = 0;                               //Store the current state into the last state for the next loop
    }
     }
