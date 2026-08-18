/*
 * Inversor trifásico con dos metodologías de modulación.
 * 
 * Metodología 1: Modulación por vector espacial (SVPWM) basada en seno/coseno.
 * Metodología 2: Conmutación secuencial de seis pasos (tren de pulsos fijo).
 * 
 * Permite seleccionar el método y ajustar la frecuencia fundamental (Hz)
 * a través del monitor serie (9600 baudios).
 * 
 * Pines de salida:
 *   D9  -> PB1 (fase A)
 *   D10 -> PB2 (fase B)
 *   D11 -> PB3 (fase C)
 * 
 * Comandos por serial:
 *   M1  -> seleccionar metodología 1 (SVPWM)
 *   M2  -> seleccionar metodología 2 (seis pasos)
 *   Fxx -> ajustar frecuencia a xx Hz (ej. F50 para 50 Hz)
 */

#include <math.h>   // para cos() y sin()

// ----- Definición de pines y máscaras -----
#define PIN_PB1 PB1   // D9
#define PIN_PB2 PB2   // D10
#define PIN_PB3 PB3   // D11

#define MASK_PB1 (1 << PIN_PB1)
#define MASK_PB2 (1 << PIN_PB2)
#define MASK_PB3 (1 << PIN_PB3)
#define ALL_MASK (MASK_PB1 | MASK_PB2 | MASK_PB3)

// Tabla de estados para los 6 sectores del inversor.
// Cada entrada contiene los bits que deben estar en HIGH para ese sector.
const uint8_t stateMasks[6] = {
  MASK_PB1,                  // Sector 0: (1,0,0)
  MASK_PB1 | MASK_PB2,       // Sector 1: (1,1,0)
  MASK_PB2,                  // Sector 2: (0,1,0)
  MASK_PB2 | MASK_PB3,       // Sector 3: (0,1,1)
  MASK_PB3,                  // Sector 4: (0,0,1)
  MASK_PB1 | MASK_PB3        // Sector 5: (1,0,1)
};

// ----- Variables globales -----
uint8_t metodo = 1;            // 1 = SVPWM, 2 = seis pasos
float frecuencia = 60.0;       // frecuencia en Hz (valor por defecto 60 Hz)

// Variables para el método 1 (SVPWM)
const unsigned long sampleRate_ms = 1;   // periodo de muestreo en ms
unsigned long lastSampleTime = 0;
float phase = 0.0;                       // fase acumulada

// Variables para el método 2 (seis pasos)
unsigned long stepDuration_us;           // duración de cada paso en microsegundos
uint8_t stepIndex = 0;                   // sector actual (0..5)
unsigned long lastStepTime_us = 0;

// ----- Prototipos de funciones -----
void aplicarEstado(uint8_t sector);
void procesarComandoSerial();
void actualizarMetodo1();
void actualizarMetodo2();

// ----- Configuración inicial -----
void setup() {
  // Establecer pines D9, D10, D11 como salida
  DDRB |= ALL_MASK;

  // Inicializar comunicación serie
  Serial.begin(9600);
  Serial.println(F("Sistema de inversor trifásico iniciado."));
  Serial.println(F("Comandos: M1 (SVPWM), M2 (seis pasos), F<frecuencia> (ej. F50)"));
  
  // Calcular duración de paso para la frecuencia por defecto (60 Hz)
  actualizarDuracionPaso();
}

// ----- Bucle principal -----
void loop() {
  // Atender comandos del monitor serie
  procesarComandoSerial();

  // Ejecutar el método seleccionado
  if (metodo == 1) {
    actualizarMetodo1();
  } else {
    actualizarMetodo2();
  }
}

// ----- Aplicar estado (sector) a los pines de salida -----
void aplicarEstado(uint8_t sector) {
  // sector debe estar entre 0 y 5
  if (sector > 5) sector = 0;
  // Limpiar los bits de los tres pines y luego poner los correspondientes al sector
  PORTB = (PORTB & ~ALL_MASK) | stateMasks[sector];
}

// ----- Procesar comandos recibidos por serial -----
void procesarComandoSerial() {
  if (Serial.available() > 0) {
    char comando = Serial.read();
    // Leer el resto del mensaje (hasta nueva línea o fin)
    String parametro = Serial.readStringUntil('\n');
    parametro.trim();  // eliminar espacios y saltos de línea

    if (comando == 'M' || comando == 'm') {
      // Cambio de metodología: se espera '1' o '2'
      if (parametro.length() > 0) {
        char opcion = parametro.charAt(0);
        if (opcion == '1') {
          metodo = 1;
          Serial.println(F("Metodología cambiada a SVPWM (vector espacial)."));
        } else if (opcion == '2') {
          metodo = 2;
          // Reiniciar el contador de pasos para que comience desde el primer sector
          stepIndex = 0;
          lastStepTime_us = micros();
          Serial.println(F("Metodología cambiada a seis pasos fijos."));
        } else {
          Serial.println(F("Opción inválida. Use M1 o M2."));
        }
      }
    } 
    else if (comando == 'F' || comando == 'f') {
      // Cambio de frecuencia: se espera un número en Hz
      float nuevaFrec = parametro.toFloat();
      if (nuevaFrec > 0) {
        frecuencia = nuevaFrec;
        actualizarDuracionPaso();
        Serial.print(F("Frecuencia ajustada a "));
        Serial.print(frecuencia);
        Serial.println(F(" Hz"));
      } else {
        Serial.println(F("Frecuencia inválida. Ingrese un número positivo."));
      }
    }
    else {
      Serial.println(F("Comando no reconocido. Use M1, M2 o F<frecuencia>."));
    }
    // Vaciar el buffer por si quedan datos pendientes
    while (Serial.available()) Serial.read();
  }
}

// ----- Actualizar parámetros dependientes de la frecuencia -----
void actualizarDuracionPaso() {
  // Para el método 2: duración de cada paso = periodo / 6
  // periodo (ms) = 1000 / frecuencia
  // paso (us) = (periodo_ms * 1000) / 6 = (1000/frecuencia * 1000)/6 = 1e6 / (6 * frecuencia)
  stepDuration_us = (unsigned long)(1000000.0 / (6.0 * frecuencia));
  // Para el método 1: no se necesita precalcular, se usa directamente en el bucle
}

// ----- Actualización del método 1 (SVPWM) -----
void actualizarMetodo1() {
  unsigned long ahora = millis();
  if (ahora - lastSampleTime >= sampleRate_ms) {
    lastSampleTime = ahora;

    // Calcular las componentes seno y coseno de la fase actual
    float signalValue = cos(phase);      // componente en fase (Vd)
    float signalValue2 = sin(phase);     // componente en cuadratura (Vq)

    // Incremento de fase para la frecuencia deseada:
    // phase += 2*PI * sampleRate_ms / periodo_ms
    // periodo_ms = 1000 / frecuencia
    // => phase += 2*PI * 1 / (1000/f) = 2*PI * f / 1000
    phase += 2.0 * PI * frecuencia / 1000.0;
    // Mantener fase en rango [0, 2*PI) para evitar desbordamiento
    if (phase >= 2.0 * PI) phase -= 2.0 * PI;

    // Cálculo del sector según la modulación por vector espacial
    float fx = signalValue;
    float fy = signalValue2 / sqrt(3.0);
    // Determinar N (0..5) según la región del hexágono
    int N = 2.5 - (fy / abs(fy)) * ((fx > fy) + (fx > -fy) + 0.5);
    // Asegurar rango
    if (N < 0) N = 0;
    if (N > 5) N = 5;

    // Aplicar el estado correspondiente
    aplicarEstado((uint8_t)N);

    // (Opcional) Enviar datos al plotter serie si se desea
    // Serial.print(signalValue); Serial.print(",");
    // Serial.print(signalValue2); Serial.print(",");
    // Serial.println(N);
  }
}

// ----- Actualización del método 2 (seis pasos fijos) -----
void actualizarMetodo2() {
  unsigned long ahora_us = micros();
  // Verificar si ha pasado el tiempo para cambiar al siguiente paso
  if (ahora_us - lastStepTime_us >= stepDuration_us) {
    lastStepTime_us = ahora_us;

    // Avanzar al siguiente sector (0..5)
    stepIndex++;
    if (stepIndex >= 6) stepIndex = 0;

    // Aplicar el estado
    aplicarEstado(stepIndex);
  }
}
