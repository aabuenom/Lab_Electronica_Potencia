/*
 * Control de TRIAC como SCR (disparo en un solo semiciclo)
 * Usa detección de cruce por cero mediante optoacoplador (pulso en D8).
 * Al no detectar polaridad, se dispara en cruces alternados.
 * Esto asegura que el TRIAC siempre conduzca en la misma polaridad.
 */

volatile bool disparar = false;          // Bandera para ejecutar el disparo
volatile bool siguiente_disparo = true;  // Alterna para disparar cada 2 cruces

void setup() {
  // Habilitar interrupción por cambio en el puerto PCIE0 (pines D8 a D13)
  PCICR |= (1 << PCIE0);
  PCMSK0 |= (1 << PCINT0);   // Pin D8 (PCINT0)

  pinMode(3, OUTPUT);        // Salida del pulso de compuerta
  digitalWrite(3, LOW);
}

void loop() {
  if (disparar) {
    disparar = false;   // Limpiar bandera inmediatamente

    // Leer el potenciómetro (A2). Ajusta los límites según tu red:
    // 50Hz -> máx 10000us, 60Hz -> máx 8333us. Aquí uso 8000 como tope práctico.
    int retardo = map(analogRead(A2), 0, 1023, 8000, 50);

    delayMicroseconds(retardo);   // Espera para definir el ángulo de disparo
    digitalWrite(3, HIGH);
    delayMicroseconds(100);       // Ancho del pulso (100us es suficiente para la mayoría de triacs)
    digitalWrite(3, LOW);
  }
}

// Rutina de interrupción: se ejecuta en CADA flanco de subida del pulso del optoacoplador
ISR(PCINT0_vect) {
  static uint8_t ultimo_estado = 0;
  uint8_t estado_actual = (PINB & B00000001) ? 1 : 0;

  // Detectar solo el flanco de subida (cuando el pulso del optoacoplador comienza)
  if (estado_actual == 1 && ultimo_estado == 0) {
    // Alternar la bandera: si es true, se dispara; si es false, se salta.
    if (siguiente_disparo) {
      disparar = true;
    }
    siguiente_disparo = !siguiente_disparo; // Invertir para el próximo cruce
  }

  ultimo_estado = estado_actual;
}
