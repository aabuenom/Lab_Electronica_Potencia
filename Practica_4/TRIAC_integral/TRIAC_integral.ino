// Control de un puente AC-AC mediante control integral con ventana de 200ms (12 Ciclos)
// Declaracion de variables globales
int detectado = 0; // Variable para indicar si se ha detectado un cambio de estado en el pin D8
int valor = 0; // Variable para almacenar el valor mapeado del potenciometro
int last_CH1_state = 0; // Variable para almacenar el Ultimo estado registrado del pin D8

// Funcion setup() - Se ejecuta una vez al inicio del programa
void setup() {
  // Configuracion de registros de interrupcion y pines de entrada/salida
  PCICR |= (1 << PCIE0); // Habilita el escaneo de PCMSK0 para configurar interrupciones por cambio de estado en los pines
  PCMSK0 |= (1 << PCINT0); // Establece que el pin D8 (PCINT0) activara una interrupcion cuando cambie su estado
  pinMode(3, OUTPUT); // Configura el pin D3 como salida para enviar un pulso al TRIAC
}

// Funcion loop() - Se ejecuta continuamente mientras el microcontrolador este encendido
void loop() {
  // Lectura y mapeo del valor del potenciometro
  valor = map(analogRead(A2), 0, 1024, 0, 200); // Mapea el valor del potenciometro a un rango de 0 a 200 ms

  // Control del TRIAC
  digitalWrite(3, HIGH); // Envia un pulso alto al pin D3 (TRIAC)
  delay(valor); // Espera un tiempo determinado por el valor del potenciometro
  digitalWrite(3, LOW); // Cambia el pin D3 a bajo, finalizando el pulso
  delay(200 - valor); // Espera el tiempo restante hasta completar los 200 ms
}

// Rutina de interrupcion ISR(PCINT0_vect) - Se ejecuta automaticamente cuando se detecta un cambio de estado en el pin D8
ISR(PCINT0_vect) {
  // Verificacion del estado del pin D8
  if (PINB & B00000001) { // Si el pin D8 esta en alto
    if (last_CH1_state == 0) { // Si el Ultimo estado registrado era bajo, se ha producido un cambio de estado
      detectado = 1; // Establece la variable 'detectado' en 1 para indicar que se ha detectado un cambio de estado
    }
  } else if (last_CH1_state == 1) { // Si el pin D8 esta en bajo y el Ultimo estado registrado era alto, se ha producido un cambio de estado
    detectado = 1; // Establece la variable 'detectado' en 1 para indicar que se ha detectado un cambio de estado
    last_CH1_state = 0; // Actualiza el Ultimo estado registrado a 0 (bajo) para la proxima iteracion
  }
}
