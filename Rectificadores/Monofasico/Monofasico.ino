/*
 * Rectificador monofásico controlado con tiristores (SCR)
 * Detección de cruce por cero mediante interrupción en pin 8 (PCINT0)
 * Ajuste del ángulo de disparo mediante potenciómetro en A2
 * Salidas: pin 11 (SCR P) y pin 10 (SCR N)
 * 
 * El potenciómetro entrega un valor de 0 a 1023, mapeado a un retardo
 * de 10 a 7200 microsegundos (máximo 7.2 ms, adecuado para 50/60 Hz).
 * Cuanto mayor es la lectura, menor es el retardo (mayor ángulo de conducción).
 * 
 * Autor: Optimizado a partir de código original de ELECTRONOOBS
 */

// ===== Variables globales =====
const int pinDeteccion = 8;   // PCINT0 (D8) – entrada del optoacoplador
//int fa=11;
//int fb=10;
const int pinSCR_P = 11;      // Compuerta del SCR para semiciclo positivo (fa)
const int pinSCR_N = 10;      // Compuerta del SCR para semiciclo negativo (fb)
const int pinPot = A2;        // Potenciómetro para control de ángulo

volatile bool cruceDetectado = false;  // Bandera activada por la ISR
volatile bool ultimoEstado = false;    // Para detectar solo flanco de subida

int semiciclo = 0;            // Contador de cruces (0: P, 1: N, 2: P...)

// ===== Configuración inicial =====
void setup() {
  // Configurar pines de salida para las compuertas
  pinMode(pinSCR_P, OUTPUT);
  pinMode(pinSCR_N, OUTPUT);
  // Asegurar ambas compuertas en LOW inicialmente
  digitalWrite(pinSCR_P, LOW);
  digitalWrite(pinSCR_N, LOW);

  // Configurar interrupción por cambio en el pin 8 (PCINT0)
  PCICR |= (1 << PCIE0);     // Habilitar el grupo de interrupciones PCINT0
  PCMSK0 |= (1 << PCINT0);   // Habilitar la interrupción en el pin 8 (PCINT0)

  // Opcional: inicializar monitor serie para depuración
  // Serial.begin(9600);
}

// ===== Bucle principal =====
void loop() {
  // Solo actuar cuando se haya detectado un cruce por cero
  if (cruceDetectado) {
    // Leer el potenciómetro (0-1023) y mapear a retardo en µs
    // Nota: se invierte la relación para que a mayor lectura, menor retardo
    int retardo = map(analogRead(pinPot), 0, 1023, 7200, 10);

    // Esperar el tiempo correspondiente al ángulo de disparo
    delayMicroseconds(retardo);

    // Determinar qué SCR disparar según el semiciclo actual
    if (semiciclo % 2 == 0) {
      // Semiciclo par → disparar SCR P (pin 11)
      digitalWrite(pinSCR_P, HIGH);
      delayMicroseconds(100);   // Pulso de compuerta (mínimo 50 µs para SCR)
      digitalWrite(pinSCR_P, LOW);
    } else {
      // Semiciclo impar → disparar SCR N (pin 10)
      digitalWrite(pinSCR_N, HIGH);
      delayMicroseconds(100);
      digitalWrite(pinSCR_N, LOW);
    }

    // Incrementar el contador de semiciclos para el próximo cruce
    semiciclo++;

    // Resetear la bandera de detección
    cruceDetectado = false;
  }
}

// ===== Rutina de interrupción =====
// Se ejecuta en cada cambio de estado del pin 8
ISR(PCINT0_vect) {
  // Leer el estado actual del pin 8 (bit 0 del registro PINB)
  bool estadoActual = (PINB & (1 << PCINT0)) != 0;

  // Detectar solo el flanco de subida (LOW → HIGH)
  // Esto evita que un pulso largo genere dos interrupciones por cruce
  if (estadoActual && !ultimoEstado) {
    cruceDetectado = true;
  }

  // Actualizar el último estado para la próxima comparación
  ultimoEstado = estadoActual;
}
