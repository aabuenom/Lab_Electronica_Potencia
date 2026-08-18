// ================================================================
//  PWM para inversor monofásico con puente H (Arduino Uno)
//  Generado automáticamente por Python
//  Modo: Phase Correct PWM con portadora triangular [0,1]
//  MODULACIÓN UNIPOLAR
// ================================================================
//  f_ref   = 60.00 Hz
//  ma      = 0.800
//  mf      = 12
//  Tipo    = SPWM
//  f_c     = 720.01 Hz (real)
//  Prescaler = 1, ICR1 = 11110
//  Tmuerto = 2.0 us (32 tics)
//  Muestras = 12
//  RMS     = 0.7047  (tensión de salida D9-D10 normalizada)
//  THD     = 68.75%
// ================================================================

#include <avr/pgmspace.h>

void setup() {
  pinMode(9, OUTPUT);   // Rama A del puente H
  pinMode(10, OUTPUT);  // Rama B del puente H

  // ---- Configuración del Timer1 en modo Phase Correct PWM con TOP = ICR1 ----
  TCCR1A = 0;
  TCCR1B = 0;
  // Modo 10: Phase Correct PWM, TOP=ICR1
  TCCR1A |= (1 << WGM11);
  TCCR1B |= (1 << WGM13);
  TCCR1B &= ~(1 << WGM12);
  TCCR1A &= ~(1 << WGM10);

  // OC1A: no inversor (COM1A1=1, COM1A0=0)
  TCCR1A |= (1 << COM1A1);
  TCCR1A &= ~(1 << COM1A0);
  // OC1B: no inversor (COM1B1=1, COM1B0=0)  <-- MODULACIÓN UNIPOLAR
  TCCR1A |= (1 << COM1B1);
  TCCR1A &= ~(1 << COM1B0);

  // ---- Prescaler ----
  TCCR1B |= (1 << CS10);

  ICR1 = 11110;
  OCR1A = 5523;
  OCR1B = 5523;

  TIMSK1 |= (1 << TOIE1);
}

const int N = 12;

const unsigned int OCR1A_table[N] PROGMEM = {
  5523,
  7744,
  9371,
  9967,
  9371,
  7745,
  5523,
  3301,
  1674,
  1078,
  1674,
  3300
};

const unsigned int OCR1B_table[N] PROGMEM = {
  5523,
  3301,
  1674,
  1078,
  1674,
  3300,
  5522,
  7744,
  9371,
  9967,
  9371,
  7745
};

volatile unsigned char index = 0;

ISR(TIMER1_OVF_vect) {
  index++;
  if (index >= N) index = 0;
  OCR1A = pgm_read_word(&OCR1A_table[index]);
  OCR1B = pgm_read_word(&OCR1B_table[index]);
}

void loop() {
  // Todo el control se realiza por interrupción
}
