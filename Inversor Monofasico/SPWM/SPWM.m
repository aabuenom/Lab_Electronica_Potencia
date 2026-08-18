% Generador de código Arduino para SPWM en puente H (pines 9 y 10)
% CON TIEMPO MUERTO POR SOFTWARE - CORREGIDO (sin operador ternario)

% 1. Solicitud de parámetros del inversor
f_ref = input("Ingrese la frecuencia de referencia (Hz): ");
ma = input("Ingrese el índice de modulación de amplitud (0-1): ");
mf = input("Ingrese el índice de modulación de frecuencia (entero): ");
dead_time_us = input("Ingrese el tiempo muerto en microsegundos (ej. 2.0): ");

mf = round(mf);
if mf < 1
    mf = 1;
end
if ma < 0 || ma > 1
    error("El índice de modulación debe estar entre 0 y 1");
end

f_c = mf * f_ref;                       % frecuencia portadora deseada

% 2. Configuración del temporizador (Arduino Uno, 16 MHz)
f_clk = 16000000;
prescaler_options = [1, 8, 64, 256, 1024];
best_prescaler = 1;
best_ICR = 0;
best_error = inf;

for p = prescaler_options
    ICR = (f_clk / (p * f_c)) - 1;
    if ICR >= 1 && ICR <= 65535
        ICR_rounded = round(ICR);
        f_c_actual = f_clk / (p * (ICR_rounded + 1));
        error = abs(f_c_actual - f_c);
        if error < best_error
            best_error = error;
            best_prescaler = p;
            best_ICR = ICR_rounded;
        end
    end
end

if best_error == inf
    error("No se pudo encontrar una configuración válida del temporizador.");
end

f_c_actual = f_clk / (best_prescaler * (best_ICR + 1));

% 3. Cálculo del tiempo muerto en tics del temporizador
dead_ticks = round(dead_time_us * 1e-6 * f_clk / best_prescaler);
if dead_ticks > best_ICR / 2
    dead_ticks = floor(best_ICR / 4);
    printf("ATENCIÓN: Tiempo muerto muy grande, se ajusta a %.2f us\n", ...
           dead_ticks * best_prescaler / f_clk * 1e6);
end

% 4. Generación de la tabla seno (N = mf muestras por ciclo)
N = mf;
t = (0:N-1) / N;
sine = ma * sin(2 * pi * t);

% Valores OCR sin tiempo muerto
OCR1A_raw = round((1 + sine) / 2 * (best_ICR + 1));
OCR1B_raw = round((1 - sine) / 2 * (best_ICR + 1));

% Aplicación del tiempo muerto (clamp entre dead_ticks y best_ICR - dead_ticks)
OCR1A_table = max(dead_ticks, min(best_ICR - dead_ticks, OCR1A_raw));
OCR1B_table = max(dead_ticks, min(best_ICR - dead_ticks, OCR1B_raw));

% 5. Escritura del archivo .ino
fid = fopen("SPWM.ino", "w");

fprintf(fid, "// Generado por Octave para SPWM en puente H (D9 y D10)\n");
fprintf(fid, "// f_ref = %.2f Hz, ma = %.3f, mf = %d\n", f_ref, ma, mf);
fprintf(fid, "// f_c real = %.2f Hz, prescaler = %d, ICR1 = %d\n", f_c_actual, best_prescaler, best_ICR);
fprintf(fid, "// Tiempo muerto = %.2f us (%d tics)\n", dead_time_us, dead_ticks);
fprintf(fid, "// N = %d muestras\n", N);
fprintf(fid, "\n#include <avr/pgmspace.h>\n\n");

fprintf(fid, "void setup() {\n");
fprintf(fid, "  pinMode(9, OUTPUT);  // Rama A\n");
fprintf(fid, "  pinMode(10, OUTPUT); // Rama B\n");
fprintf(fid, "  // Configurar Timer1 en modo Fast PWM con TOP = ICR1\n");
fprintf(fid, "  TCCR1A = 0;\n");
fprintf(fid, "  TCCR1B = 0;\n");
fprintf(fid, "  TCCR1A |= (1 << WGM11);\n");
fprintf(fid, "  TCCR1B |= (1 << WGM13) | (1 << WGM12);\n");
fprintf(fid, "  TCCR1A |= (1 << COM1A1) | (1 << COM1B1); // PWM no inversor\n");

% Bits del prescaler
switch best_prescaler
    case 1
        fprintf(fid, "  TCCR1B |= (1 << CS10);\n");
    case 8
        fprintf(fid, "  TCCR1B |= (1 << CS11);\n");
    case 64
        fprintf(fid, "  TCCR1B |= (1 << CS11) | (1 << CS10);\n");
    case 256
        fprintf(fid, "  TCCR1B |= (1 << CS12);\n");
    case 1024
        fprintf(fid, "  TCCR1B |= (1 << CS12) | (1 << CS10);\n");
end

fprintf(fid, "  ICR1 = %d;\n", best_ICR);
fprintf(fid, "  OCR1A = %d;\n", OCR1A_table(1));
fprintf(fid, "  OCR1B = %d;\n", OCR1B_table(1));
fprintf(fid, "  TIMSK1 |= (1 << TOIE1); // Interrupción por overflow\n");
fprintf(fid, "}\n\n");

% Tablas en PROGMEM - CORREGIDO (sin operador ternario)
fprintf(fid, "const int N = %d;\n", N);
fprintf(fid, "const unsigned int OCR1A_table[N] PROGMEM = {\n");
for i = 1:N
    if i < N
        fprintf(fid, "  %d,\n", OCR1A_table(i));
    else
        fprintf(fid, "  %d\n", OCR1A_table(i));
    end
end
fprintf(fid, "};\n");

fprintf(fid, "const unsigned int OCR1B_table[N] PROGMEM = {\n");
for i = 1:N
    if i < N
        fprintf(fid, "  %d,\n", OCR1B_table(i));
    else
        fprintf(fid, "  %d\n", OCR1B_table(i));
    end
end
fprintf(fid, "};\n\n");

fprintf(fid, "volatile unsigned char index = 0;\n\n");

fprintf(fid, "ISR(TIMER1_OVF_vect) {\n");
fprintf(fid, "  index++;\n");
fprintf(fid, "  if (index >= N) index = 0;\n");
fprintf(fid, "  OCR1A = pgm_read_word(&OCR1A_table[index]);\n");
fprintf(fid, "  OCR1B = pgm_read_word(&OCR1B_table[index]);\n");
fprintf(fid, "}\n\n");

fprintf(fid, "void loop() {\n");
fprintf(fid, "  // Bucle vacío: todo se maneja por interrupción\n");
fprintf(fid, "}\n");

fclose(fid);

disp("Archivo 'SPWM.ino' generado exitosamente con tiempo muerto por software.");
