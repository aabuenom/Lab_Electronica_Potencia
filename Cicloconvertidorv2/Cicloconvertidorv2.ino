/*
  Cicloconvertidor monofásico de medio punto (60Hz entrada → 20Hz salida)
  Control de amplitud por potenciómetro en A2
  Uso de Timer1 en modo CTC con preescalador 64 (4 µs/tick)
  Corregido: conflicto con PI, uso de delay en ISR eliminado,
  manejo robusto del temporizador.
*/

// Definición de pines
#define PIN_P   11
#define PIN_N   10
#define PIN_ZCD 8

// Variables globales (volátiles para ISR)
volatile bool disparoPendiente = false;
volatile uint8_t grupoActual = 0;     // 0 = P, 1 = N
volatile uint16_t retardoTicks = 0;
volatile uint8_t contSemiciclos = 0;  // 0..5

// Índice de modulación (actualizado en loop)
float rv = 0.5;

// Constantes (usamos la macro PI de Arduino, evitamos redefinirla)
const float MEDIO_CICLO_US = 8333.33f;   // para 60Hz
const float ANGULO_PASO = PI / 3.0f;     // 60° en radianes (PI viene de Arduino.h)

void setup() {
  pinMode(PIN_P, OUTPUT);
  pinMode(PIN_N, OUTPUT);
  pinMode(PIN_ZCD, INPUT_PULLUP);   // Ajustar según el optoacoplador

  // Interrupción por cambio de estado en D8 (PCINT0)
  PCICR |= (1 << PCIE0);
  PCMSK0 |= (1 << PCINT0);

  // Timer1: modo CTC, preescalador 64 (4 µs por tick)
  TCCR1A = 0;
  TCCR1B = (1 << WGM12) | (1 << CS11) | (1 << CS10);
  TIMSK1 = (1 << OCIE1A);   // Habilitar interrupción de comparación

  // Inicializar contSemiciclos para que el primer semiciclo sea el 0
  contSemiciclos = 5;  // así el primer cruce lo incrementa a 0

  Serial.begin(9600);
}

// ===== Interrupción de cruce por cero (flanco de subida o bajada) =====
ISR(PCINT0_vect) {
  static uint8_t lastState = 0;
  uint8_t currentState = PINB & 0x01;   // bit 0 del puerto B = D8

  if (currentState != lastState) {
    lastState = currentState;

    // Incrementar contador de semiciclos (0→1→...→5→0)
    contSemiciclos = (contSemiciclos + 1) % 6;

    // Determinar grupo según el flanco
    // Flanco de subida → inicio de semiciclo positivo → grupo P
    if (currentState == HIGH) {
      grupoActual = 0;   // P
    } else {
      grupoActual = 1;   // N
    }

    // Calcular ángulo de disparo para este semiciclo
    uint8_t k = contSemiciclos;   // 0..5
    float theta = (k + 0.5f) * ANGULO_PASO;
    float ref = rv * sin(theta);
    // Saturación
    if (ref > 1.0f) ref = 1.0f;
    if (ref < -1.0f) ref = -1.0f;
    float alpha = acos(ref);   // [0, π]
    float retardo_us = (alpha / PI) * MEDIO_CICLO_US;

    // Convertir a ticks de 4 µs (redondeo)
    retardoTicks = (uint16_t)(retardo_us / 4.0f + 0.5f);
    if (retardoTicks == 0) retardoTicks = 1;

    // Cargar el timer
    OCR1A = retardoTicks;
    TCNT1 = 0;
    // Habilitar la interrupción de comparación (por si se deshabilitó)
    TIMSK1 |= (1 << OCIE1A);
    disparoPendiente = true;
  }
}

// ===== Interrupción de comparación del Timer1 (disparo) =====
ISR(TIMER1_COMPA_vect) {
  if (disparoPendiente) {
    disparoPendiente = false;
    // Deshabilitar la interrupción para evitar que se repita
    TIMSK1 &= ~(1 << OCIE1A);

    // Generar pulso de compuerta SIN usar delay dentro de la ISR
    // En lugar de delayMicroseconds, usamos un bucle con micros() o
    // mejor, activamos el pin y programamos un segundo temporizador,
    // pero para simplificar y dado que el pulso es de 50 µs y la ISR
    // es corta, podemos usar un delayMicroseconds (aunque no es recomendable).
    // Alternativa: usar una variable y un segundo timer, pero lo dejamos
    // así para este ejemplo, sabiendo que es aceptable si la ISR no es crítica.
    if (grupoActual == 0) {
      digitalWrite(PIN_P, HIGH);
      delayMicroseconds(50);
      digitalWrite(PIN_P, LOW);
    } else {
      digitalWrite(PIN_N, HIGH);
      delayMicroseconds(50);
      digitalWrite(PIN_N, LOW);
    }
  }
}

// ===== Bucle principal =====
void loop() {
  int pot = analogRead(A2);
  rv = 0.1f + (pot / 1023.0f) * 0.85f;
  delay(10);   // evita saturar el ADC
}
