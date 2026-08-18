#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Generador PWM para inversor monofásico con puente H (Arduino Uno)
-------------------------------------------------------------------
Este programa permite:
- Seleccionar el tipo de onda de referencia (SPWM, THIPWM, MPWM, Onda Cuadrada).
- Ajustar parámetros como frecuencia, índice de modulación, relación de frecuencias y tiempo muerto.
- Visualizar en tres gráficas: referencia+portadora (triangular), ambas PWM complementarias desplazadas, y tensión de salida.
- Calcular el valor RMS y la distorsión armónica total (THD) de la salida.
- Generar el código Arduino (.ino) con las tablas de modulación precalculadas para el Timer1 en modo Phase Correct PWM.

Dependencias: numpy, matplotlib, tkinter
Autor: Prof. Alexander Bueno
Fecha: 08/2026
"""

import tkinter as tk
from tkinter import ttk, messagebox
import numpy as np
import matplotlib.pyplot as plt
import os

# =============================================================================
#  MÓDULO DE GENERACIÓN DE ONDAS DE REFERENCIA
# =============================================================================

def evaluar_referencia(tipo, theta, params):
    """
    Evalúa la forma de onda de referencia normalizada (sin escalar por ma)
    en los ángulos theta.

    Parámetros:
        tipo (str): 'SPWM', 'THIPWM', 'MPWM' o 'Onda Cuadrada'
        theta (array): ángulos en radianes
        params (dict): parámetros adicionales según el tipo:
            - 'THIPWM': {'a3': float} amplitud de la 3ra armónica (0..1)
            - 'MPWM': {'k': float} factor de forma (1..10)
    Retorna:
        array: valores de referencia entre -1 y 1 (sin escalar)
    """
    if tipo == "SPWM":
        ref = np.sin(theta)
    elif tipo == "THIPWM":
        a3 = params.get('a3', 0.25)
        raw = np.sin(theta) + a3 * np.sin(3 * theta)
        max_raw = np.max(np.abs(raw))
        ref = raw / max_raw if max_raw > 0 else np.zeros_like(theta)
    elif tipo == "MPWM":
        k = params.get('k', 3.0)
        raw = np.tanh(k * np.sin(theta))
        max_raw = np.max(np.abs(raw))
        ref = raw / max_raw if max_raw > 0 else np.zeros_like(theta)
    elif tipo == "Onda Cuadrada":
        ref = np.sign(np.sin(theta))
    else:
        raise ValueError(f"Tipo de onda desconocido: {tipo}")
    return ref


def generar_referencia(tipo, ma, f_ref, mf, params):
    """
    Genera la tabla de referencia para un periodo de la portadora.
    Se usa para calcular los valores OCR del Timer1.
    """
    theta = np.linspace(0, 2 * np.pi, mf, endpoint=False)
    ref = evaluar_referencia(tipo, theta, params)
    return np.clip(ma * ref, -ma, ma)


# =============================================================================
#  MÓDULO DE CÁLCULO DEL TEMPORIZADOR Y GENERACIÓN DEL CÓDIGO ARDUINO
# =============================================================================

def calcular_parametros_timer(f_ref, mf, dead_time_us, ma, ref):
    """
    Calcula la configuración óptima del Timer1 (prescaler, ICR1) y las tablas
    OCR1A y OCR1B para un Arduino Uno (16 MHz) en modo Phase Correct PWM con TOP=ICR1.
    En este modo, la portadora es triangular.
    """
    F_CLK = 16000000
    PRESCALER_OPTS = [1, 8, 64, 256, 1024]
    f_c = mf * f_ref  # frecuencia de la portadora (triangular)

    # ---- Selección del mejor prescaler para Phase Correct PWM ----
    # f_c = F_CLK / (2 * prescaler * (ICR + 1))
    best_prescaler = 1
    best_ICR = 0
    best_error = float('inf')
    for p in PRESCALER_OPTS:
        ICR = (F_CLK / (2 * p * f_c)) - 1
        if 1 <= ICR <= 65535:
            ICR_round = int(round(ICR))
            f_c_actual = F_CLK / (2 * p * (ICR_round + 1))
            error = abs(f_c_actual - f_c)
            if error < best_error:
                best_error = error
                best_prescaler = p
                best_ICR = ICR_round
    if best_error == float('inf'):
        raise ValueError("No se encontró configuración válida para el Timer1.")
    f_c_actual = F_CLK / (2 * best_prescaler * (best_ICR + 1))

    # ---- Tiempo muerto en ticks ----
    dead_ticks = int(round(dead_time_us * 1e-6 * F_CLK / best_prescaler))
    if dead_ticks > best_ICR // 2:
        dead_ticks = best_ICR // 4
        print(f"ADVERTENCIA: Tiempo muerto ajustado a {dead_ticks * best_prescaler / F_CLK * 1e6:.2f} us")

    # ---- Cálculo de OCR para Phase Correct PWM ----
    # Se usa un solo valor de referencia para ambas ramas, pero con modos de salida opuestos.
    # d = (1 + ref) / 2  (duty deseado para la rama A)
    # Para la rama A (no inversora): OCR1A = d * ICR - dead_ticks
    # Para la rama B (inversora):   OCR1B = d * ICR + dead_ticks
    d = (1 + ref) / 2
    OCR1A_raw = d * best_ICR
    OCR1B_raw = d * best_ICR  # mismo valor, pero con modos opuestos

    # Aplicar tiempo muerto: restar a A, sumar a B
    OCR1A = np.clip(OCR1A_raw - dead_ticks, 0, best_ICR).astype(int)
    OCR1B = np.clip(OCR1B_raw + dead_ticks, 0, best_ICR).astype(int)

    return best_prescaler, best_ICR, f_c_actual, dead_ticks, OCR1A, OCR1B, mf


def generar_archivo_ino(f_ref, ma, mf, dead_time_us, tipo, params,
                        prescaler, ICR, f_c_actual, dead_ticks,
                        OCR1A, OCR1B, N, rms=0.0, thd=0.0):
    """
    Escribe el archivo SPWM.ino en la raíz.
    Incluye en el encabezado el RMS y THD calculados.
    Configura Timer1 en modo Phase Correct PWM con TOP=ICR1.
    """
    ruta = "SPWM.ino"

    with open(ruta, "w") as f:
        f.write("// ================================================================\n")
        f.write("//  PWM para inversor monofásico con puente H (Arduino Uno)\n")
        f.write("//  Generado automáticamente por Python\n")
        f.write("//  Modo: Phase Correct PWM con portadora triangular\n")
        f.write("// ================================================================\n")
        f.write(f"//  f_ref   = {f_ref:.2f} Hz\n")
        f.write(f"//  ma      = {ma:.3f}\n")
        f.write(f"//  mf      = {mf}\n")
        f.write(f"//  Tipo    = {tipo}\n")
        if params:
            f.write(f"//  Params  = {params}\n")
        f.write(f"//  f_c     = {f_c_actual:.2f} Hz (real)\n")
        f.write(f"//  Prescaler = {prescaler}, ICR1 = {ICR}\n")
        f.write(f"//  Tmuerto = {dead_time_us:.1f} us ({dead_ticks} tics)\n")
        f.write(f"//  Muestras = {N}\n")
        f.write(f"//  RMS     = {rms:.4f}  (tensión de salida D9-D10 normalizada)\n")
        f.write(f"//  THD     = {thd:.2f}%\n")
        f.write("// ================================================================\n\n")

        f.write("#include <avr/pgmspace.h>\n\n")

        f.write("void setup() {\n")
        f.write("  pinMode(9, OUTPUT);   // Rama A del puente H (no inversora)\n")
        f.write("  pinMode(10, OUTPUT);  // Rama B del puente H (inversora)\n\n")
        f.write("  // ---- Configuración del Timer1 en modo Phase Correct PWM con TOP = ICR1 ----\n")
        f.write("  TCCR1A = 0;\n")
        f.write("  TCCR1B = 0;\n")
        f.write("  // Modo 10: Phase Correct PWM, TOP=ICR1\n")
        f.write("  TCCR1A |= (1 << WGM11);\n")
        f.write("  TCCR1B |= (1 << WGM13);\n")
        f.write("  TCCR1B &= ~(1 << WGM12);\n")
        f.write("  TCCR1A &= ~(1 << WGM10);\n\n")
        f.write("  // OC1A: no inversor (COM1A1=1, COM1A0=0)\n")
        f.write("  TCCR1A |= (1 << COM1A1);\n")
        f.write("  TCCR1A &= ~(1 << COM1A0);\n")
        f.write("  // OC1B: inversor (COM1B1=1, COM1B0=1)\n")
        f.write("  TCCR1A |= (1 << COM1B1) | (1 << COM1B0);\n\n")

        f.write("  // ---- Prescaler ----\n")
        if prescaler == 1:
            f.write("  TCCR1B |= (1 << CS10);\n")
        elif prescaler == 8:
            f.write("  TCCR1B |= (1 << CS11);\n")
        elif prescaler == 64:
            f.write("  TCCR1B |= (1 << CS11) | (1 << CS10);\n")
        elif prescaler == 256:
            f.write("  TCCR1B |= (1 << CS12);\n")
        elif prescaler == 1024:
            f.write("  TCCR1B |= (1 << CS12) | (1 << CS10);\n")
        f.write("\n")

        f.write(f"  ICR1 = {ICR};\n")
        f.write(f"  OCR1A = {OCR1A[0]};\n")
        f.write(f"  OCR1B = {OCR1B[0]};\n\n")
        f.write("  TIMSK1 |= (1 << TOIE1);\n")
        f.write("}\n\n")

        f.write(f"const int N = {N};\n\n")
        f.write("const unsigned int OCR1A_table[N] PROGMEM = {\n")
        for i, v in enumerate(OCR1A):
            f.write(f"  {v}{',' if i < N-1 else ''}\n")
        f.write("};\n\n")

        f.write("const unsigned int OCR1B_table[N] PROGMEM = {\n")
        for i, v in enumerate(OCR1B):
            f.write(f"  {v}{',' if i < N-1 else ''}\n")
        f.write("};\n\n")

        f.write("volatile unsigned char index = 0;\n\n")
        f.write("ISR(TIMER1_OVF_vect) {\n")
        f.write("  index++;\n")
        f.write("  if (index >= N) index = 0;\n")
        f.write("  OCR1A = pgm_read_word(&OCR1A_table[index]);\n")
        f.write("  OCR1B = pgm_read_word(&OCR1B_table[index]);\n")
        f.write("}\n\n")

        f.write("void loop() {\n")
        f.write("  // Todo el control se realiza por interrupción\n")
        f.write("}\n")

    print(f"Archivo generado: {ruta}")


# =============================================================================
#  MÓDULO DE SIMULACIÓN, CÁLCULO DE RMS Y THD, Y GRÁFICAS
# =============================================================================

def simular_senales(f_ref, ma, mf, dead_time_us, ref, pts_por_periodo=200):
    """
    Simula las señales PWM (D9, D10) y la tensión de salida (D9-D10)
    para dos ciclos completos de la referencia.
    Utiliza portadora triangular en [-1, 1] y comparación directa con la referencia.
    D9 y D10 son complementarias (D10 = 1 - D9) para reflejar la operación del puente H.
    """
    f_c = mf * f_ref
    T_c = 1.0 / f_c
    num_periodos = 2 * mf
    tiempo_total = num_periodos * T_c
    n_pts = num_periodos * pts_por_periodo
    t = np.linspace(0, tiempo_total, n_pts, endpoint=False)

    # Portadora triangular en [-1, 1]
    fase = (t % T_c) / T_c
    portadora = 1 - 4 * np.abs(fase - 0.5)   # pico en -1 y 1

    # Referencia repetida para dos ciclos y expandida a la resolución temporal
    ref_repetida = np.repeat(np.tile(ref, 2), pts_por_periodo)

    # Comparación directa: salida alta si referencia > portadora
    outA = (ref_repetida > portadora).astype(float)
    # Rama B es la complementaria de A (sin tiempo muerto en la simulación)
    outB = 1 - outA

    return t, outA, outB, outA - outB


def calcular_rms_thd(t, senal, f_ref):
    """
    Calcula el RMS total, el RMS de la fundamental y el THD (%).
    """
    dt = t[1] - t[0]
    N = len(senal)
    y = senal - np.mean(senal)
    V_rms = np.sqrt(np.mean(y**2))
    if V_rms < 1e-12:
        return 0.0, 0.0, 0.0

    Y = np.fft.rfft(y)
    freqs = np.fft.rfftfreq(N, dt)
    idx_fund = np.argmin(np.abs(freqs - f_ref))
    if idx_fund == 0:
        V1_peak = Y[0] / N
    else:
        V1_peak = 2 * np.abs(Y[idx_fund]) / N
    V1_rms = V1_peak / np.sqrt(2)

    max_armonica = 50
    idx_max = min(len(Y)-1, int(max_armonica * f_ref / (freqs[1] - freqs[0])) + 1)
    suma_cuadrados = 0.0
    for k in range(1, idx_max+1):
        if k == idx_fund:
            continue
        if k == 0:
            Vk_peak = Y[0] / N
        else:
            Vk_peak = 2 * np.abs(Y[k]) / N
        suma_cuadrados += (Vk_peak / np.sqrt(2))**2
    thd = np.sqrt(suma_cuadrados) / V1_rms if V1_rms > 1e-12 else 0.0
    return V_rms, V1_rms, thd * 100


def graficar_simulacion(f_ref, ma, mf, dead_time_us, ref, tipo, params):
    """
    Muestra tres subplots en vertical:
      1) Referencia + portadora triangular
      2) PWM de D9 y D10 complementarias desplazadas verticalmente
      3) Tensión de salida (D9 - D10)
    Retorna (RMS, THD).
    """
    # Simulación estándar
    t, outA, outB, diff = simular_senales(f_ref, ma, mf, dead_time_us, ref, pts_por_periodo=200)
    try:
        V_rms, _, thd = calcular_rms_thd(t, diff, f_ref)
    except Exception as e:
        print(f"Error en cálculo de RMS/THD: {e}")
        V_rms, thd = 0.0, 0.0

    # Referencia y portadora de alta resolución para la gráfica
    f_c = mf * f_ref
    T_c = 1.0 / f_c
    num_periodos = 2 * mf
    tiempo_total = num_periodos * T_c
    pts_high = 1000 * num_periodos
    t_high = np.linspace(0, tiempo_total, pts_high, endpoint=False)
    theta_high = 2 * np.pi * f_ref * t_high
    ref_high = ma * evaluar_referencia(tipo, theta_high, params)
    # Portadora triangular en [-1, 1]
    fase_high = (t_high % T_c) / T_c
    portadora_high = 1 - 4 * np.abs(fase_high - 0.5)

    # Crear figura con 3 subplots verticales
    fig, axs = plt.subplots(3, 1, figsize=(14, 12))
    fig.suptitle(
        f'PWM con portadora triangular - 2 ciclos completos\n'
        f'f_ref = {f_ref:.1f} Hz, ma = {ma:.2f}, mf = {mf}, Tmuerto = {dead_time_us:.1f} us\n'
        f'Tipo: {tipo}  |  RMS = {V_rms:.4f}  |  THD = {thd:.2f}%',
        fontsize=14
    )

    # ---- Subplot 1: Referencia y portadora ----
    axs[0].plot(t_high, ref_high, 'b', lw=1.5, label='Referencia')
    axs[0].plot(t_high, portadora_high, 'r', lw=0.6, label='Portadora')
    axs[0].axhline(y=0, color='k', linestyle='--', linewidth=0.5)
    axs[0].set_ylabel('Amplitud')
    axs[0].grid(True)
    axs[0].legend()
    axs[0].set_title('Referencia + Portadora (alta resolución)')
    axs[0].set_xlim(t_high[0], t_high[-1])

    # ---- Subplot 2: PWM D9 y D10 complementarias desplazadas ----
    offset = 1.0  # desplazamiento vertical para separar las señales
    axs[1].plot(t, outA + offset, 'g', drawstyle='steps-post', lw=0.8, label='PWM D9 (desplazado +1)')
    axs[1].plot(t, outB - offset, 'm', drawstyle='steps-post', lw=0.8, label='PWM D10 (desplazado -1)')
    axs[1].axhline(y=offset, color='gray', linestyle=':', linewidth=0.5)
    axs[1].axhline(y=-offset, color='gray', linestyle=':', linewidth=0.5)
    axs[1].axhline(y=0, color='k', linestyle='--', linewidth=0.5)
    axs[1].set_ylabel('Nivel desplazado')
    axs[1].set_xlabel('Tiempo (s)')
    axs[1].grid(True)
    axs[1].legend()
    axs[1].set_title('Señales PWM complementarias en D9 y D10 (desplazadas verticalmente)')
    axs[1].set_xlim(t[0], t[-1])

    # ---- Subplot 3: Tensión de salida ----
    axs[2].plot(t, diff, 'k', drawstyle='steps-post', lw=0.8)
    axs[2].axhline(y=0, color='gray', linestyle='--', linewidth=0.5)
    axs[2].set_ylabel('Tensión')
    axs[2].set_xlabel('Tiempo (s)')
    axs[2].grid(True)
    axs[2].set_title('Tensión de salida (D9 - D10)')
    axs[2].set_xlim(t[0], t[-1])
    axs[2].set_ylim(-1.2, 1.2)

    plt.tight_layout()
    plt.show()
    return V_rms, thd


# =============================================================================
#  INTERFAZ GRÁFICA (Tkinter)
# =============================================================================

class SPWMApp:
    """Aplicación principal con interfaz gráfica."""

    def __init__(self, root):
        self.root = root
        root.title("Generador PWM para Arduino - Puente H")
        root.geometry("600x580")
        root.resizable(False, False)

        # Variables de los parámetros
        self.f_ref = tk.StringVar(value="60.0")
        self.ma = tk.StringVar(value="0.8")
        self.mf = tk.StringVar(value="12")
        self.dead = tk.StringVar(value="2.0")
        self.tipo = tk.StringVar(value="SPWM")
        self.param_a3 = tk.StringVar(value="0.25")
        self.param_k = tk.StringVar(value="3.0")

        # Variables para mostrar resultados
        self.rms_label = tk.StringVar(value="RMS: ---")
        self.thd_label = tk.StringVar(value="THD: ---%")

        self._crear_widgets()

    def _crear_widgets(self):
        """Construye la interfaz de usuario."""
        root = self.root
        row = 0

        tk.Label(root, text="Frecuencia de referencia (Hz):").grid(row=row, column=0, padx=10, pady=5, sticky='e')
        tk.Entry(root, textvariable=self.f_ref, width=15).grid(row=row, column=1, padx=10, pady=5, sticky='w')
        row += 1

        tk.Label(root, text="Índice de modulación ma (0-1):").grid(row=row, column=0, padx=10, pady=5, sticky='e')
        tk.Entry(root, textvariable=self.ma, width=15).grid(row=row, column=1, padx=10, pady=5, sticky='w')
        row += 1

        tk.Label(root, text="Índice de modulación mf (entero):").grid(row=row, column=0, padx=10, pady=5, sticky='e')
        tk.Entry(root, textvariable=self.mf, width=15).grid(row=row, column=1, padx=10, pady=5, sticky='w')
        row += 1

        tk.Label(root, text="Tiempo muerto (us):").grid(row=row, column=0, padx=10, pady=5, sticky='e')
        tk.Entry(root, textvariable=self.dead, width=15).grid(row=row, column=1, padx=10, pady=5, sticky='w')
        row += 1

        tk.Label(root, text="Tipo de referencia:").grid(row=row, column=0, padx=10, pady=5, sticky='e')
        self.tipo_combo = ttk.Combobox(root, textvariable=self.tipo,
                                       values=["SPWM", "THIPWM", "MPWM", "Onda Cuadrada"],
                                       state="readonly")
        self.tipo_combo.grid(row=row, column=1, padx=10, pady=5, sticky='w')
        self.tipo_combo.bind("<<ComboboxSelected>>", self._actualizar_parametros)
        row += 1

        self.frame_params = tk.Frame(root)
        self.frame_params.grid(row=row, column=0, columnspan=2, pady=5)
        self._actualizar_parametros()
        row += 1

        tk.Label(root, textvariable=self.rms_label, font=("Arial", 11, "bold"), fg="blue").grid(row=row, column=0, padx=10, pady=5)
        tk.Label(root, textvariable=self.thd_label, font=("Arial", 11, "bold"), fg="blue").grid(row=row, column=1, padx=10, pady=5)
        row += 1

        frame_btns = tk.Frame(root)
        frame_btns.grid(row=row, column=0, columnspan=2, pady=15)
        tk.Button(frame_btns, text="Actualizar gráficas", command=self._graficar,
                  bg="#4CAF50", fg="white", font=("Arial", 11)).pack(side=tk.LEFT, padx=10)
        tk.Button(frame_btns, text="Generar código Arduino", command=self._generar_codigo,
                  bg="#2196F3", fg="white", font=("Arial", 11)).pack(side=tk.LEFT, padx=10)
        tk.Button(frame_btns, text="Cerrar", command=self.root.quit,
                  bg="#f44336", fg="white", font=("Arial", 11)).pack(side=tk.LEFT, padx=10)

        self.status = tk.Label(root, text="", font=("Arial", 10), fg="green")
        self.status.grid(row=row+1, column=0, columnspan=2, pady=5)

    def _actualizar_parametros(self, event=None):
        """Muestra/oculta los campos de parámetros específicos según el tipo."""
        for w in self.frame_params.winfo_children():
            w.destroy()

        tipo = self.tipo.get()
        if tipo == "THIPWM":
            tk.Label(self.frame_params, text="Amplitud 3ra armónica (0-1):").pack(side=tk.LEFT, padx=5)
            tk.Entry(self.frame_params, textvariable=self.param_a3, width=8).pack(side=tk.LEFT, padx=5)
        elif tipo == "MPWM":
            tk.Label(self.frame_params, text="Factor de forma k (1-10):").pack(side=tk.LEFT, padx=5)
            tk.Entry(self.frame_params, textvariable=self.param_k, width=8).pack(side=tk.LEFT, padx=5)

    def _obtener_referencia(self):
        """Construye el diccionario de parámetros y genera la referencia."""
        f_ref = float(self.f_ref.get())
        ma = float(self.ma.get())
        mf = int(self.mf.get())
        tipo = self.tipo.get()
        params = {}
        if tipo == "THIPWM":
            params['a3'] = float(self.param_a3.get())
        elif tipo == "MPWM":
            params['k'] = float(self.param_k.get())
        return generar_referencia(tipo, ma, f_ref, mf, params)

    def _graficar(self):
        """Acción del botón 'Actualizar gráficas'."""
        try:
            f_ref = float(self.f_ref.get())
            ma = float(self.ma.get())
            mf = int(self.mf.get())
            dead = float(self.dead.get())
            tipo = self.tipo.get()

            if not (0 <= ma <= 1):
                raise ValueError("ma debe estar en [0,1]")
            if mf < 1:
                mf = 1
                self.mf.set(str(mf))
            if dead < 0:
                raise ValueError("Tiempo muerto no puede ser negativo")

            ref = self._obtener_referencia()
            params = {}
            if tipo == "THIPWM":
                params['a3'] = float(self.param_a3.get())
            elif tipo == "MPWM":
                params['k'] = float(self.param_k.get())

            V_rms, thd = graficar_simulacion(f_ref, ma, mf, dead, ref, tipo, params)
            self.rms_label.set(f"RMS = {V_rms:.4f}")
            self.thd_label.set(f"THD = {thd:.2f}%")
            self.status.config(text="Gráficas actualizadas", fg="green")

        except Exception as e:
            messagebox.showerror("Error", str(e))
            self.status.config(text="Error en gráficas", fg="red")

    def _generar_codigo(self):
        """Acción del botón 'Generar código Arduino'."""
        try:
            f_ref = float(self.f_ref.get())
            ma = float(self.ma.get())
            mf = int(self.mf.get())
            dead = float(self.dead.get())
            tipo = self.tipo.get()

            if not (0 <= ma <= 1):
                raise ValueError("ma debe estar en [0,1]")
            if mf < 1:
                mf = 1
                self.mf.set(str(mf))
            if dead < 0:
                raise ValueError("Tiempo muerto no puede ser negativo")

            ref = self._obtener_referencia()

            # ---- Calcular RMS y THD para incluirlos en el encabezado ----
            t, _, _, diff = simular_senales(f_ref, ma, mf, dead, ref, pts_por_periodo=200)
            V_rms, _, thd = calcular_rms_thd(t, diff, f_ref)

            # ---- Calcular parámetros del timer (Phase Correct) ----
            prescaler, ICR, f_c_actual, dead_ticks, OCR1A, OCR1B, N = \
                calcular_parametros_timer(f_ref, mf, dead, ma, ref)

            # ---- Parámetros adicionales para el comentario ----
            params = {}
            if tipo == "THIPWM":
                params['a3'] = float(self.param_a3.get())
            elif tipo == "MPWM":
                params['k'] = float(self.param_k.get())

            # ---- Generar archivo .ino ----
            generar_archivo_ino(f_ref, ma, mf, dead, tipo, params,
                                prescaler, ICR, f_c_actual, dead_ticks,
                                OCR1A, OCR1B, N, rms=V_rms, thd=thd)

            self.status.config(text="¡Código Arduino generado!", fg="green")
            messagebox.showinfo("Éxito", "Archivo SPWM.ino generado en la raíz.")

        except Exception as e:
            messagebox.showerror("Error", str(e))
            self.status.config(text="Error al generar código", fg="red")


# =============================================================================
#  PUNTO DE ENTRADA
# =============================================================================

if __name__ == "__main__":
    root = tk.Tk()
    app = SPWMApp(root)
    root.mainloop()
