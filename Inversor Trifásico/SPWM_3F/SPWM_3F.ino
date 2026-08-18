// ================================================================
//  PWM para inversor trifásico (Arduino Uno)
//  Generado automáticamente por Python
//  Modo: Fast PWM, Timer1 (D9, D10) y Timer2 (D11)
// ================================================================
//  f_ref   = 50.00 Hz
//  ma      = 0.800
//  mf      = 12
//  Tipo    = MPWM
//  Params  = {'k': 3.0}
//  f_c     = 600.96 Hz (real)
//  Prescaler = 256, ICR1 = 103
//  Muestras = 12
//  RMS (Vab) = 0.7192  (tensión de línea normalizada)
//  THD (Vab) = 64.61%
// ================================================================

#include <avr/pgmspace.h>

void setup() {
  // ---- Configuración de pines como salidas (ya lo hacen los timers) ----
  // D9 (PB1), D10 (PB2), D11 (PB3)
  DDRB |= (1 << PB1) | (1 << PB2) | (1 << PB3);

  // ---- Timer1: Fast PWM, TOP = ICR1 (modo 14) ----
  TCCR1A = 0;
  TCCR1B = 0;
  // WGM13=1, WGM12=0, WGM11=1, WGM10=0 -> modo 14
  TCCR1A |= (1 << WGM11);
  TCCR1B |= (1 << WGM13);
  TCCR1B &= ~(1 << WGM12);
  TCCR1A &= ~(1 << WGM10);

  // OC1A no inversor (COM1A1=1, COM1A0=0)
  TCCR1A |= (1 << COM1A1);
  TCCR1A &= ~(1 << COM1A0);
  // OC1B no inversor (COM1B1=1, COM1B0=0)
  TCCR1A |= (1 << COM1B1);
  TCCR1A &= ~(1 << COM1B0);

  ICR1 = 103;
  OCR1A = 52;
  OCR1B = 11;

  // ---- Timer2: Fast PWM, TOP = 0xFF (modo 3) ----
  TCCR2A = 0;
  TCCR2B = 0;
  // WGM22=1, WGM21=0, WGM20=1 -> modo 3 (Fast PWM, TOP=0xFF)
  TCCR2A |= (1 << WGM22) | (1 << WGM20);
  TCCR2A &= ~(1 << WGM21);
  // OC2A no inversor (COM2A1=1, COM2A0=0)
  TCCR2A |= (1 << COM2A1);
  TCCR2A &= ~(1 << COM2A0);
  OCR2A = 229;

  // ---- Prescaler ----
  TCCR1B |= (1 << CS12);
  TCCR2B |= (1 << CS22) | (1 << CS21);

  // Habilitar interrupción por desbordamiento de Timer1
  TIMSK1 |= (1 << TOIE1);
}

const int N = 12;

const unsigned int OCR1A_table[N] PROGMEM = {
  52,
  89,
  92,
  93,
  92,
  89,
  52,
  14,
  11,
  10,
  11,
  14
};

const unsigned int OCR1B_table[N] PROGMEM = {
  11,
  10,
  11,
  14,
  52,
  89,
  92,
  93,
  92,
  89,
  52,
  14
};

const unsigned char OCR2A_table[N] PROGMEM = {
  229,
  220,
  128,
  35,
  26,
  25,
  26,
  35,
  127,
  220,
  229,
  230
};

volatile unsigned char index = 0;

ISR(TIMER1_OVF_vect) {
  index++;
  if (index >= N) index = 0;
  OCR1A = pgm_read_word(&OCR1A_table[index]);
  OCR1B = pgm_read_word(&OCR1B_table[index]);
  OCR2A = pgm_read_byte(&OCR2A_table[index]);
}

void loop() {
  // Todo el control se realiza por interrupción
}
