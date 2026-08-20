/*
 * Control de TRIAC por ráfagas de ciclos completos (burst firing)
 * Ventana fija de 200 ms (10 ciclos para 50 Hz).
 * El potenciómetro ajusta el número de ciclos encendidos dentro de la ventana.
 * 
 * Conexiones:
 *   - D8: entrada del optoacoplador de cruce por cero (flanco de subida).
 *   - D3: salida del pulso de compuerta del TRIAC (activo en HIGH).
 *   - A2: potenciómetro para ajuste de potencia.
 * 
 * Funcionamiento:
 *   - La ISR cuenta los cruces por cero (flancos de subida) y mantiene un contador
 *     de 0 a (2 * CICLOS_POR_VENTANA - 1) que representa la posición dentro de la ventana.
 *   - Al inicio de cada ventana (contador = 0), el loop calcula el número de ciclos
 *     a encender según el potenciómetro (con curva de raíz cuadrada).
 *   - La ISR, en cada cruce, decide si el TRIAC debe estar encendido o apagado
 *     comparando el contador actual con 2 * ciclos_encendido.
 *   - El TRIAC se enciende durante los primeros 'ciclos_encendido' ciclos completos
 *     y se apaga durante el resto de la ventana.
 *   - Esto permite un control suave y sincronizado de la potencia.
 */

// Variables compartidas entre la ISR y el loop (volátiles)
volatile uint8_t contador_cruces = 0;     // Posición dentro de la ventana (0 a 2*CICLOS-1)
volatile uint8_t ciclos_encendido = 0;    // Número de ciclos a encender en la ventana actual
volatile bool nueva_ventana = true;       // Bandera para que el loop recalcule al inicio

// Constantes configurables
const uint8_t CICLOS_POR_VENTANA = 12;    // Para 50 Hz: 10 ciclos = 200 ms
// Para 60 Hz, cambiar a 12 ciclos (12 * 16.67 ms ≈ 200 ms)
const uint8_t CRUCES_POR_VENTANA = CICLOS_POR_VENTANA * 2;  // 2 cruces por ciclo

void setup() {
  // Configurar interrupción por cambio en el pin D8 (PCINT0)
  PCICR  |= (1 << PCIE0);    // Habilitar el grupo de interrupciones del puerto B
  PCMSK0 |= (1 << PCINT0);   // Seleccionar el pin D8 como fuente de interrupción

  pinMode(3, OUTPUT);
  digitalWrite(3, LOW);      // Asegurar TRIAC apagado al inicio
}

void loop() {
  // Si la ISR indica que estamos al inicio de una nueva ventana
  if (nueva_ventana) {
    nueva_ventana = false;   // Limpiar bandera

    // Leer el potenciómetro (0 a 1023)
    int valor_pot = analogRead(A2);

    // Calcular la fracción de potencia deseada usando raíz cuadrada
    // para compensar la percepción no lineal del ojo humano (potencia ∝ Vrms²)
    float fraccion = sqrt((float)valor_pot / 1023.0);

    // Convertir a número de ciclos a encender (redondeo al entero más cercano)
    uint8_t ciclos = (uint8_t)(fraccion * CICLOS_POR_VENTANA + 0.5);
    if (ciclos > CICLOS_POR_VENTANA) ciclos = CICLOS_POR_VENTANA;

    // Actualizar la variable global que usará la ISR
    ciclos_encendido = ciclos;

    // No es necesario hacer nada más; la ISR se encargará del patrón de encendido
    // a partir del próximo cruce por cero.
  }

  // Pequeña pausa para no saturar el CPU (opcional)
  // El loop solo se ejecuta cuando hay una nueva ventana, así que delay no es crítico.
  delay(1);
}

// Rutina de interrupción por cambio de estado en D8 (se ejecuta en cada flanco de subida)
ISR(PCINT0_vect) {
  static uint8_t ultimo_estado = 0;
  uint8_t estado = (PINB & B00000001) ? 1 : 0;

  // Detectar solo el flanco de subida (0 → 1), que corresponde al inicio del pulso del optoacoplador
  if (estado == 1 && ultimo_estado == 0) {
    // Incrementar el contador de cruces dentro de la ventana
    contador_cruces++;

    // Si hemos llegado al final de la ventana
    if (contador_cruces >= CRUCES_POR_VENTANA) {
      contador_cruces = 0;          // Reiniciar para la siguiente ventana
      nueva_ventana = true;         // Señalar al loop que calcule la nueva consigna
    }

    // Decidir si el TRIAC debe estar encendido en este cruce
    // Estará encendido durante los primeros 'ciclos_encendido' ciclos completos.
    // Como cada ciclo tiene 2 cruces, el TRIAC debe estar HIGH cuando el contador
    // sea menor que (2 * ciclos_encendido).
    if (contador_cruces < (ciclos_encendido * 2)) {
      // Estamos dentro de la parte encendida de la ventana
      // Si el TRIAC ya estaba encendido, no es necesario hacer nada, pero para asegurar,
      // podemos mantener HIGH. Sin embargo, como el TRIAC se apaga solo en el cruce,
      // necesitamos darle un pulso en cada cruce para mantenerlo encendido.
      // Opción 1: Dejar la compuerta siempre HIGH durante la fase de encendido.
      // Opción 2: Dar un pulso corto en cada cruce. La opción 1 es más simple y válida
      // porque el TRIAC se apaga en el cruce por cero y se necesita un nuevo pulso
      // para que conduzca en el siguiente semiciclo.
      // Por tanto, ponemos la salida en HIGH y la mantenemos.
      digitalWrite(3, HIGH);
    } else {
      // En la parte apagada, aseguramos que la compuerta esté LOW
      digitalWrite(3, LOW);
    }
  }

  ultimo_estado = estado;   // Actualizar para la próxima interrupción
}
