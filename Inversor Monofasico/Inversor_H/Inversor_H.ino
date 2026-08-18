/*
  Generador de onda de 50/60 Hz con selección de método de disparo.
  Pines: 9 (PB1) y 10 (PB2) como salidas complementarias.
  Comandos por serial:
    F50  -> frecuencia 50 Hz
    F60  -> frecuencia 60 Hz
    M1   -> método 1 (digitalWrite)
    M2   -> método 2 (registros DDRB/PORTB con bits)
    M3   -> método 3 (asignación directa con máscara)
    H    -> muestra ayuda
*/

// Variables de configuración
int frecuencia = 50;          // 50 o 60 Hz
int metodo = 1;               // 1, 2 o 3
unsigned long semiPeriodoUs;  // duración de medio período en microsegundos

// Estado de la salida
bool d9High = true;           // true = D9 HIGH, D10 LOW; false = D9 LOW, D10 HIGH
unsigned long tiempoAnterior = 0;

// ---------- Funciones de escritura según método ----------
void setPinsMethod1(bool d9High) {
  if (d9High) {
    digitalWrite(9, HIGH);
    digitalWrite(10, LOW);
  } else {
    digitalWrite(9, LOW);
    digitalWrite(10, HIGH);
  }
}

void setPinsMethod2(bool d9High) {
  if (d9High) {
    PORTB |= (1 << PB1);      // D9 HIGH
    PORTB &= ~(1 << PB2);     // D10 LOW
  } else {
    PORTB &= ~(1 << PB1);     // D9 LOW
    PORTB |= (1 << PB2);      // D10 HIGH
  }
}

void setPinsMethod3(bool d9High) {
  if (d9High) {
    // Poner D9 HIGH, D10 LOW sin afectar otros bits de PORTB
    PORTB = (PORTB & ~((1 << PB1) | (1 << PB2))) | (1 << PB1);
  } else {
    PORTB = (PORTB & ~((1 << PB1) | (1 << PB2))) | (1 << PB2);
  }
}

// Función que llama al método seleccionado
void aplicarMetodo(bool d9High) {
  switch (metodo) {
    case 1: setPinsMethod1(d9High); break;
    case 2: setPinsMethod2(d9High); break;
    case 3: setPinsMethod3(d9High); break;
    default: setPinsMethod1(d9High); break;
  }
}

// ---------- Actualización de la frecuencia ----------
void actualizarFrecuencia(int freq) {
  frecuencia = freq;
  if (frecuencia == 50) {
    semiPeriodoUs = 10000;      // 10 ms
  } else if (frecuencia == 60) {
    semiPeriodoUs = 8333;       // 8.333 ms (aproximado)
  } else {
    semiPeriodoUs = 10000;      // fallback
  }
  // Reiniciamos la temporización para evitar transiciones bruscas
  tiempoAnterior = micros();
}

// ---------- Configuración inicial ----------
void setup() {
  Serial.begin(9600);
  while (!Serial) { ; } // esperar conexión (opcional)

  // Configurar pines 9 y 10 como salida
  pinMode(9, OUTPUT);
  pinMode(10, OUTPUT);
  // También configurar DDRB por si se usa método 2 o 3
  DDRB |= (1 << PB1) | (1 << PB2);

  // Inicializar con 50 Hz y método 1
  actualizarFrecuencia(50);
  metodo = 1;
  d9High = true;
  aplicarMetodo(d9High);
  tiempoAnterior = micros();

  // Mostrar mensaje de bienvenida
  Serial.println("Generador de onda 50/60 Hz");
  Serial.println("Comandos: F50, F60, M1, M2, M3, H");
  Serial.print("Frecuencia actual: ");
  Serial.print(frecuencia);
  Serial.println(" Hz");
  Serial.print("Método actual: ");
  Serial.println(metodo);
}

// ---------- Bucle principal ----------
void loop() {
  // 1. Manejo de comandos seriales
  if (Serial.available() > 0) {
    String comando = Serial.readStringUntil('\n');
    comando.trim();
    comando.toUpperCase();

    if (comando == "F50") {
      actualizarFrecuencia(50);
      Serial.println("Frecuencia cambiada a 50 Hz");
    } else if (comando == "F60") {
      actualizarFrecuencia(60);
      Serial.println("Frecuencia cambiada a 60 Hz");
    } else if (comando == "M1") {
      metodo = 1;
      Serial.println("Método cambiado a 1 (digitalWrite)");
    } else if (comando == "M2") {
      metodo = 2;
      Serial.println("Método cambiado a 2 (registros)");
    } else if (comando == "M3") {
      metodo = 3;
      Serial.println("Método cambiado a 3 (máscara)");
    } else if (comando == "H") {
      Serial.println("Comandos disponibles:");
      Serial.println("  F50  -> Frecuencia 50 Hz");
      Serial.println("  F60  -> Frecuencia 60 Hz");
      Serial.println("  M1   -> Método 1 (digitalWrite)");
      Serial.println("  M2   -> Método 2 (registros)");
      Serial.println("  M3   -> Método 3 (máscara)");
      Serial.println("  H    -> Mostrar esta ayuda");
      Serial.print("Estado actual: ");
      Serial.print(frecuencia);
      Serial.print(" Hz, Método ");
      Serial.println(metodo);
    } else {
      Serial.println("Comando no reconocido. Envie H para ayuda.");
    }
  }

  // 2. Generación de la onda (no bloqueante)
  unsigned long ahora = micros();
  if (ahora - tiempoAnterior >= semiPeriodoUs) {
    tiempoAnterior = ahora;
    // Cambiar estado
    d9High = !d9High;
    aplicarMetodo(d9High);
  }
}
