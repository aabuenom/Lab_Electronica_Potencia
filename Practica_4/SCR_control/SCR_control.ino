/* Control de SCR con potenciometro
 * Tutorial: http://www.ELECTRONOOBS.com/eng_circuitos_tut32.php
 * Gracias
 */

// Variables globales
int detectado = 0;
int valor = 0;
int last_CH1_state = 0;
unsigned k = 0;
int ks = 0;

void setup() {
  // Configuracion de interrupciones y registros de puerto
  PCICR |= (1 << PCIE0); // Habilitar escaneo PCMSK0
  PCMSK0 |= (1 << PCINT0); // Establecer pin D8 para activar una interrupcion en cambio de estado. Entrada desde optoacoplador
  pinMode(3, OUTPUT); // Definir D3 como salida para el pulso DIAC
}

void loop() {
  // Leer el valor del potenciometro y mapearlo de 10 a 7200 microsegundos
  valor = map(analogRead(A2), 0, 1024, 7200, 10); // Mapeo de la orden de disparo

  // Si se ha detectado un cambio de estado
  if (detectado) {
    k = k + 1;
    ks = k % 2; // Mapeo para que solo de orden de disparo en un ciclo

    // Controlar el disparo del SCR en funcion del valor de ks
    switch (ks) {
      case 0: {
        delayMicroseconds(valor); // Orden de disparo
        digitalWrite(3, HIGH);
        delayMicroseconds(100);
        digitalWrite(3, LOW);
        detectado = 0;
        break;
      }
      case 1: {
        delayMicroseconds(valor); // Inhibicion del disparo
        digitalWrite(3, LOW);
        detectado = 0;
        break;
      }
      default: {
        delayMicroseconds(valor); // Inhibicion del disparo
        digitalWrite(3, LOW);
        detectado = 0;
        break;
      }
    }
  }
}

// Rutina de interrupcion para el disparo
ISR(PCINT0_vect) {
  // Entrada desde optoacoplador
  if (PINB & B00000001) { // Verificar si el pin D8 esta en alto
    if (last_CH1_state == 0) { // Si el ultimo estado era 0, entonces tenemos un cambio de estado
      detectado = 1; // ¡Hemos detectado un cambio de estado 
    }
  } else if (last_CH1_state == 1) { // Si el pin D8 esta en bajo y el ultimo estado era alto, entonces tenemos un cambio de estado
    detectado = 1; // ¡Hemos detectado un cambio de estado 
    last_CH1_state = 0; // Almacenar el estado actual en el ultimo estado para el siguiente ciclo
  }
}
