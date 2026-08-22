/*
  Rect_3F.ino – Control de fase trifásico con TRIACs (media onda) para RED DE 60 Hz
  Secuencia positiva: A → B → C (desfase 120°).
  Sincronización por detección de cruce por cero de la fase A (pin D8).
  Potenciómetro en A2 ajusta el ángulo de disparo (retardo desde el cruce).
  Autor: ELECTRONOOBS (adaptado y optimizado para 60 Hz)
*/

// ------------------------- Variables globales -----------------------------
volatile bool cruceDetectado = false;   // Flag activado por interrupción en cada flanco del cruce por cero
volatile uint8_t semiCiclo = 0;         // 0 o 1: selecciona el semiciclo en el que se dispara (media onda)
volatile uint8_t lastState = 0;         // Estado anterior del pin D8 para detección de flanco

// Pines de disparo para cada fase (conectados a los optoacopladores de los TRIACs)
const byte pinFaseA = 11;
const byte pinFaseB = 10;
const byte pinFaseC = 9;

// Constantes de tiempo para 60 Hz (periodo = 16.666 ms)
// 120° = 16.666ms / 3 = 5.555 ms (en microsegundos)
const uint16_t RETARDO_120 = 5555;      // <--- AJUSTADO PARA 60 Hz
const uint16_t ANCHO_PULSO = 100;       // Duración del pulso de disparo (microsegundos)

// ------------------------- Configuración inicial ---------------------------
void setup() {
  // Configurar pines de disparo como salidas
  pinMode(pinFaseA, OUTPUT);
  pinMode(pinFaseB, OUTPUT);
  pinMode(pinFaseC, OUTPUT);
  
  // Asegurar que los TRIACs estén apagados al inicio
  digitalWrite(pinFaseA, LOW);
  digitalWrite(pinFaseB, LOW);
  digitalWrite(pinFaseC, LOW);
  
  // Configurar la interrupción por cambio de estado en el pin D8 (PCINT0)
  PCICR  |= (1 << PCIE0);   // Habilitar el vector de interrupción para el puerto B
  PCMSK0 |= (1 << PCINT0);  // Habilitar la interrupción en el pin D8 (PCINT0)
  
  // (Opcional) Inicializar comunicación serie para depuración
  // Serial.begin(9600);
}

// ------------------------- Bucle principal --------------------------------
void loop() {
  // Esperar a que ocurra un cruce por cero (flag activado por ISR)
  if (cruceDetectado) {
    // Reiniciar el flag para evitar reprocesar el mismo evento
    cruceDetectado = false;

    // Leer el potenciómetro y mapear a un retardo en microsegundos (10 a 7000 µs)
    // Para 60 Hz, el semiciclo dura 8333 µs. Mapeamos hasta 7000 µs para evitar
    // disparar demasiado cerca del final y perder el siguiente cruce.
    // A mayor lectura (más giro), menor retardo → mayor ángulo de conducción.
    uint16_t retardoDisparo = map(analogRead(A2), 0, 1023, 7000, 10);
    
    // Solo disparar en un semiciclo (media onda): cuando semiCiclo = 1
    if (semiCiclo == 1) {
      // ----- Disparo de la fase A (referencia) -----
      delayMicroseconds(retardoDisparo);    // Esperar el ángulo de disparo desde el cruce de A
      digitalWrite(pinFaseA, HIGH);
      delayMicroseconds(ANCHO_PULSO);
      digitalWrite(pinFaseA, LOW);
      
      // ----- Disparo de la fase B (retrasada 120° respecto a A) -----
      delayMicroseconds(RETARDO_120);
      digitalWrite(pinFaseB, HIGH);
      delayMicroseconds(ANCHO_PULSO);
      digitalWrite(pinFaseB, LOW);
      
      // ----- Disparo de la fase C (retrasada 240° respecto a A, o 120° respecto a B) -----
      delayMicroseconds(RETARDO_120);
      digitalWrite(pinFaseC, HIGH);
      delayMicroseconds(ANCHO_PULSO);
      digitalWrite(pinFaseC, LOW);
    } else {
      // En el semiciclo no operativo, mantener todas las salidas en LOW (los TRIACs no conducen)
      digitalWrite(pinFaseA, LOW);
      digitalWrite(pinFaseB, LOW);
      digitalWrite(pinFaseC, LOW);
    }
  }
  // (El bucle continúa; no se usan delay() largos que bloqueen la interrupción)
}

// ------------------------- Rutina de interrupción -------------------------
// Se ejecuta en cada flanco (subida o bajada) del pin D8 (PCINT0)
ISR(PCINT0_vect) {
  // Leer el estado actual del pin D8 (bit 0 del puerto B)
  bool currentState = (PINB & (1 << PCINT0)) ? 1 : 0;
  
  // Detectar flanco: si el estado actual es diferente al anterior
  if (currentState != lastState) {
    // Actualizar el flag para el bucle principal
    cruceDetectado = true;
    
    // Incrementar el contador de flancos para alternar semiciclos
    static unsigned int contadorFlancos = 0;  // Se conserva entre llamadas
    contadorFlancos++;
    semiCiclo = contadorFlancos % 2;          // 0,1,0,1...
    
    // Guardar el estado actual como "anterior" para la próxima interrupción
    lastState = currentState;
  }
  // Si no hay cambio de estado, no se hace nada (evita falsos disparos)
}
