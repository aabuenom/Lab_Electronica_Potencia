/*
 * Control de TRIAC - Disparo en cada cruce por cero
 * Detecta SOLO el flanco de subida del optoacoplador.
 * Estable y eficiente.
 * 
 * Conexiones:
 *   - Pin D8 (PCINT0): Entrada del optoacoplador de cruce por cero.
 *   - Pin D3: Salida del pulso de compuerta para el TRIAC.
 *   - Pin A2: Potenciómetro para control de ángulo de disparo.
 * 
 * Funcionamiento:
 *   - El optoacoplador genera un pulso corto en cada cruce por cero de la red.
 *   - La interrupción por cambio de estado captura el flanco de subida del pulso.
 *   - En el loop se espera el retardo correspondiente al ángulo de disparo,
 *     se envía un pulso a la compuerta y se reinicia la bandera.
 *   - El mapeo del potenciómetro permite ajustar la potencia de 0 a casi 100%.
 */

volatile bool disparar = false;   // Bandera para indicar al loop que debe disparar
                                  // Se declara volatile porque se modifica desde la ISR

void setup() {
  // Configurar la interrupción por cambio de estado en el puerto PCIE0
  // (pines D8 a D13 del Arduino Uno / Nano)
  PCICR  |= (1 << PCIE0);   // Habilita el grupo de interrupciones PCIE0
  PCMSK0 |= (1 << PCINT0);  // Selecciona el pin D8 (PCINT0) como origen de la interrupción

  pinMode(3, OUTPUT);       // Configura D3 como salida para el pulso de compuerta
  digitalWrite(3, LOW);     // Estado inicial: compuerta apagada
}

void loop() {
  // Si hay un disparo pendiente (detectado en la ISR)
  if (disparar) {
    disparar = false;   // Limpiar la bandera inmediatamente para evitar disparos repetidos

    // Leer el valor del potenciómetro (0-1023) y mapearlo a microsegundos de retardo.
    // Ajusta los límites según tu red:
    //   - 50 Hz: medio ciclo = 10,000 µs. Usamos 8000 como máximo práctico (deja margen).
    //   - 60 Hz: medio ciclo = 8,333 µs. Usa 7000 como máximo.
    // El valor mínimo (50 µs) evita disparos demasiado cercanos al cruce (puede causar inestabilidad).
    int retardo = map(analogRead(A2), 0, 1023, 8000, 50);

    // Esperar el ángulo de disparo (retraso desde el cruce por cero)
    delayMicroseconds(retardo);

    // Generar pulso de compuerta para el TRIAC
    digitalWrite(3, HIGH);
    delayMicroseconds(100);   // Ancho del pulso (100 µs es suficiente para la mayoría de TRIACs)
    digitalWrite(3, LOW);

    // El TRIAC se apagará en el próximo cruce por cero, y la ISR volverá a activar la bandera.
  }
}

/*
 * Rutina de interrupción por cambio de estado en PCINT0 (pin D8)
 * Se ejecuta en cada flanco de subida y bajada del pulso del optoacoplador.
 * Solo se dispara en el flanco de subida para evitar dobles disparos.
 */
ISR(PCINT0_vect) {
  // Variable estática para recordar el estado anterior del pin entre llamadas
  static uint8_t ultimo_estado = 0;

  // Leer el estado actual del pin D8 (bit 0 del puerto B)
  uint8_t estado = (PINB & B00000001) ? 1 : 0;

  // Detectar flanco de subida: pasó de 0 a 1
  if (estado == 1 && ultimo_estado == 0) {
    disparar = true;   // Señalizar al loop que debe disparar en este semiciclo
  }

  // Actualizar el estado anterior para la próxima interrupción
  ultimo_estado = estado;
}

/*
 * NOTAS SOBRE LA ESTABILIDAD:
 * - Al detectar solo el flanco de subida, se evita que el pulso del optoacoplador
 *   (que tiene una cierta duración) genere dos interrupciones por cada cruce,
 *   lo que provocaría disparos dobles y comportamiento errático.
 * - La ISR es muy rápida: solo lee el pin, compara y actualiza una variable.
 * - El retardo y el pulso se realizan en el loop, evitando bloqueos prolongados en la ISR.
 * 
 * AJUSTES RECOMENDADOS:
 * - Si el optoacoplador entrega un pulso activo por nivel (no por flanco), 
 *   puedes cambiar la condición a flanco de bajada: 
 *   if (estado == 0 && ultimo_estado == 1)
 * - Si tu TRIAC requiere un pulso más largo, aumenta delayMicroseconds(100) a 200 o 300.
 * - Para red de 60 Hz, cambia el límite superior del map a 7000.
 */
