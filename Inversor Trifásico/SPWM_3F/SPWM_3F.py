#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Generador PWM para inversor trifásico (Arduino Uno)
---------------------------------------------------
Este programa permite:
- Seleccionar el tipo de onda de referencia (SPWM, THIPWM, MPWM, Onda Cuadrada, SVPWM).
- Ajustar parámetros como frecuencia, índice de modulación, relación de frecuencias.
- Visualizar en tres gráficas: referencias+portadora, PWM de las tres fases (con offset), y tensiones de línea (con offset).
- Calcular el valor RMS y la distorsión armónica total (THD) de las tensiones de línea.
- Generar el código Arduino (.ino) con las tablas de modulación precalculadas para el Timer1 (D9, D10) y Timer2 (D11).

Dependencias: numpy, matplotlib, tkinter
Autor: Prof. Alexander Bueno (adaptado para trifásico)
Fecha: 08/2026
"""

import tkinter as tk
from tkinter import ttk, messagebox
import numpy as np
import matplotlib.pyplot as plt
import os

# =============================================================================
#  MÓDULO DE GENERACIÓN DE ONDAS DE REFERENCIA (MODULACIONES ESCALARES)
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
        # Normalizar para que el pico sea entre 1 y -1
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


def generar_referencias_trifasicas(tipo, ma, theta, params):
    """
    Genera las tres referencias de fase (va, vb, vc) para un conjunto de ángulos.
    Retorna: (va, vb, vc) arrays, cada uno escalado por ma y recortado a [-1,1].
    """
    # Referencias sin escalar
    ra = evaluar_referencia(tipo, theta, params)
    rb = evaluar_referencia(tipo, theta - 2*np.pi/3, params)
    rc = evaluar_referencia(tipo, theta + 2*np.pi/3, params)

    # Escalar por ma y recortar para evitar saturación
    va = np.clip(ma * ra, -1, 1)
    vb = np.clip(ma * rb, -1, 1)
    vc = np.clip(ma * rc, -1, 1)
    return va, vb, vc


# =============================================================================
#  MÓDULO SVPWM
# =============================================================================

def svpwm_generate(ma, theta):
    """
    Genera las tres señales de modulación usando Space Vector PWM.
    Retorna: (da, db, dc) arrays de ciclo de trabajo (0..1).
    """
    # Referencias senoidales
    va = ma * np.sin(theta)
    vb = ma * np.sin(theta - 2*np.pi/3)
    vc = ma * np.sin(theta + 2*np.pi/3)

    # Transformación alfa-beta (Clarke)
    v_alpha = va
    v_beta = (vb - vc) / np.sqrt(3)

    # Calcular sector (0..5)
    sector = np.floor((np.arctan2(v_beta, v_alpha) + np.pi) / (np.pi/3)) % 6
    sector = sector.astype(int)

    # Para cada punto, calcular T1, T2, T0
    # Usamos la convención: Vref = ma * exp(j*theta) con Vdc=1 (normalizado)
    # T1 = (sqrt(3)*ma*Ts) * sin(60 - theta_shift)
    # T2 = (sqrt(3)*ma*Ts) * sin(theta_shift)
    # T0 = Ts - T1 - T2
    # Luego asignar a los vectores activos según el sector.

    # Pre-calcular constantes
    sqrt3 = np.sqrt(3)
    Ts = 1.0  # período normalizado

    # Ángulo dentro del sector (0..60)
    theta_sec = np.arctan2(v_beta, v_alpha) - sector * np.pi/3 + np.pi/3
    # Ajustar para que esté en [0, pi/3]
    theta_sec = np.mod(theta_sec, np.pi/3)

    # Tiempos normalizados (en fracción de Ts)
    T1 = (sqrt3 * ma * Ts) * np.sin(np.pi/3 - theta_sec)
    T2 = (sqrt3 * ma * Ts) * np.sin(theta_sec)
    T0 = Ts - T1 - T2
    # Recortar por si ma > 1 (sobremodulación)
    T1 = np.clip(T1, 0, Ts)
    T2 = np.clip(T2, 0, Ts)
    T0 = np.clip(T0, 0, Ts)

    # Asignar tiempos a las fases según sector
    # Sector 0: V1(100), V2(110)
    # Sector 1: V3(010), V4(011)
    # Sector 2: V5(001), V6(101)
    # etc.
    # Inicializar arrays
    da = np.zeros_like(theta)
    db = np.zeros_like(theta)
    dc = np.zeros_like(theta)

    # Máscaras por sector
    mask_s0 = (sector == 0)
    mask_s1 = (sector == 1)
    mask_s2 = (sector == 2)
    mask_s3 = (sector == 3)
    mask_s4 = (sector == 4)
    mask_s5 = (sector == 5)

    # Sector 0: V1(100) y V2(110)
    da[mask_s0] = (T1[mask_s0] + T2[mask_s0] + T0[mask_s0]/2) / Ts
    db[mask_s0] = (T2[mask_s0] + T0[mask_s0]/2) / Ts
    dc[mask_s0] = (T0[mask_s0]/2) / Ts

    # Sector 1: V3(010) y V4(011)
    da[mask_s1] = (T0[mask_s1]/2) / Ts
    db[mask_s1] = (T1[mask_s1] + T2[mask_s1] + T0[mask_s1]/2) / Ts
    dc[mask_s1] = (T2[mask_s1] + T0[mask_s1]/2) / Ts

    # Sector 2: V5(001) y V6(101)
    da[mask_s2] = (T2[mask_s2] + T0[mask_s2]/2) / Ts
    db[mask_s2] = (T0[mask_s2]/2) / Ts
    dc[mask_s2] = (T1[mask_s2] + T2[mask_s2] + T0[mask_s2]/2) / Ts

    # Sector 3: V4(011) y V5(001)
    da[mask_s3] = (T0[mask_s3]/2) / Ts
    db[mask_s3] = (T1[mask_s3] + T0[mask_s3]/2) / Ts
    dc[mask_s3] = (T1[mask_s3] + T2[mask_s3] + T0[mask_s3]/2) / Ts

    # Sector 4: V6(101) y V1(100)
    da[mask_s4] = (T1[mask_s4] + T2[mask_s4] + T0[mask_s4]/2) / Ts
    db[mask_s4] = (T0[mask_s4]/2) / Ts
    dc[mask_s4] = (T2[mask_s4] + T0[mask_s4]/2) / Ts

    # Sector 5: V2(110) y V3(010)
    da[mask_s5] = (T2[mask_s5] + T0[mask_s5]/2) / Ts
    db[mask_s5] = (T1[mask_s5] + T2[mask_s5] + T0[mask_s5]/2) / Ts
    dc[mask_s5] = (T0[mask_s5]/2) / Ts

    # Recortar por si acaso
    da = np.clip(da, 0, 1)
    db = np.clip(db, 0, 1)
    dc = np.clip(dc, 0, 1)

    return da, db, dc


def generar_tablas(tipo, ma, mf, params):
    """
    Genera las tablas de ciclo de trabajo (0..1) para un periodo completo.
    Retorna: (da, db, dc) arrays de tamaño mf.
    """
    N = int(mf)
    theta = np.linspace(0, 2*np.pi, N, endpoint=False)

    if tipo == "SVPWM":
        da, db, dc = svpwm_generate(ma, theta)
    else:
        va, vb, vc = generar_referencias_trifasicas(tipo, ma, theta, params)
        da = (1 + va) / 2
        db = (1 + vb) / 2
        dc = (1 + vc) / 2

    # Asegurar que estén en [0,1]
    da = np.clip(da, 0, 1)
    db = np.clip(db, 0, 1)
    dc = np.clip(dc, 0, 1)

    return da, db, dc


# =============================================================================
#  MÓDULO DE CÁLCULO DEL TEMPORIZADOR Y GENERACIÓN DEL CÓDIGO ARDUINO
# =============================================================================

def calcular_parametros_timer(f_ref, mf):
    """
    Calcula la configuración óptima para Timer1 y Timer2 para un Arduino Uno (16 MHz)
    de modo que ambos timers operen a la misma frecuencia de portadora f_c = mf * f_ref.

    Timer1: Fast PWM mode 14 (TOP=ICR1), salidas OC1A (D9) y OC1B (D10)
    Timer2: Fast PWM mode 3 (TOP=0xFF), salida OC2A (D11)

    Retorna: (prescaler, ICR1, f_c_actual, N)
    """
    F_CLK = 16000000
    PRESCALER_OPTS = [1, 8, 64, 256, 1024]
    f_c = mf * f_ref

    # Para Timer2: f_c = F_CLK / (prescaler * 256)
    # Buscamos el prescaler que dé una frecuencia lo más cercana a f_c
    best_p = 1
    best_error = float('inf')
    for p in PRESCALER_OPTS:
        f_c_actual = F_CLK / (p * 256)
        error = abs(f_c_actual - f_c)
        if error < best_error:
            best_error = error
            best_p = p

    # Con ese prescaler, calculamos ICR1 para Timer1: f_c = F_CLK / (p * (ICR1+1))
    # Queremos que Timer1 tenga la misma frecuencia que Timer2
    ICR1 = int(round(F_CLK / (best_p * f_c) - 1))
    if ICR1 < 1:
        ICR1 = 1
    elif ICR1 > 65535:
        ICR1 = 65535

    # Recalcular frecuencia real de Timer1
    f_c_actual = F_CLK / (best_p * (ICR1 + 1))

    return best_p, ICR1, f_c_actual


def generar_archivo_ino(f_ref, ma, mf, tipo, params,
                        prescaler, ICR1, f_c_actual,
                        da, db, dc, rms_ab=0.0, thd_ab=0.0):
    """
    Escribe el archivo .ino en la raíz.
    Configura Timer1 y Timer2 en Fast PWM.
    """
    N = len(da)

    # Escalar a valores para OCR
    # Timer1: OCR1A = duty * ICR1, OCR1B = duty * ICR1
    OCR1A = np.round(da * ICR1).astype(int)
    OCR1B = np.round(db * ICR1).astype(int)
    # Timer2: OCR2A = duty * 255
    OCR2A = np.round(dc * 255).astype(int)

    # Asegurar límites
    OCR1A = np.clip(OCR1A, 0, ICR1)
    OCR1B = np.clip(OCR1B, 0, ICR1)
    OCR2A = np.clip(OCR2A, 0, 255)

    ruta = "SPWM_3F.ino"

    with open(ruta, "w") as f:
        f.write("// ================================================================\n")
        f.write("//  PWM para inversor trifásico (Arduino Uno)\n")
        f.write("//  Generado automáticamente por Python\n")
        f.write("//  Modo: Fast PWM, Timer1 (D9, D10) y Timer2 (D11)\n")
        f.write("// ================================================================\n")
        f.write(f"//  f_ref   = {f_ref:.2f} Hz\n")
        f.write(f"//  ma      = {ma:.3f}\n")
        f.write(f"//  mf      = {mf}\n")
        f.write(f"//  Tipo    = {tipo}\n")
        if params:
            f.write(f"//  Params  = {params}\n")
        f.write(f"//  f_c     = {f_c_actual:.2f} Hz (real)\n")
        f.write(f"//  Prescaler = {prescaler}, ICR1 = {ICR1}\n")
        f.write(f"//  Muestras = {N}\n")
        f.write(f"//  RMS (Vab) = {rms_ab:.4f}  (tensión de línea normalizada)\n")
        f.write(f"//  THD (Vab) = {thd_ab:.2f}%\n")
        f.write("// ================================================================\n\n")

        f.write("#include <avr/pgmspace.h>\n\n")

        f.write("void setup() {\n")
        f.write("  // ---- Configuración de pines como salidas (ya lo hacen los timers) ----\n")
        f.write("  // D9 (PB1), D10 (PB2), D11 (PB3)\n")
        f.write("  DDRB |= (1 << PB1) | (1 << PB2) | (1 << PB3);\n\n")

        f.write("  // ---- Timer1: Fast PWM, TOP = ICR1 (modo 14) ----\n")
        f.write("  TCCR1A = 0;\n")
        f.write("  TCCR1B = 0;\n")
        f.write("  // WGM13=1, WGM12=0, WGM11=1, WGM10=0 -> modo 14\n")
        f.write("  TCCR1A |= (1 << WGM11);\n")
        f.write("  TCCR1B |= (1 << WGM13);\n")
        f.write("  TCCR1B &= ~(1 << WGM12);\n")
        f.write("  TCCR1A &= ~(1 << WGM10);\n\n")

        f.write("  // OC1A no inversor (COM1A1=1, COM1A0=0)\n")
        f.write("  TCCR1A |= (1 << COM1A1);\n")
        f.write("  TCCR1A &= ~(1 << COM1A0);\n")
        f.write("  // OC1B no inversor (COM1B1=1, COM1B0=0)\n")
        f.write("  TCCR1A |= (1 << COM1B1);\n")
        f.write("  TCCR1A &= ~(1 << COM1B0);\n\n")

        f.write(f"  ICR1 = {ICR1};\n")
        f.write(f"  OCR1A = {OCR1A[0]};\n")
        f.write(f"  OCR1B = {OCR1B[0]};\n\n")

        f.write("  // ---- Timer2: Fast PWM, TOP = 0xFF (modo 3) ----\n")
        f.write("  TCCR2A = 0;\n")
        f.write("  TCCR2B = 0;\n")
        f.write("  // WGM22=1, WGM21=0, WGM20=1 -> modo 3 (Fast PWM, TOP=0xFF)\n")
        f.write("  TCCR2A |= (1 << WGM22) | (1 << WGM20);\n")
        f.write("  TCCR2A &= ~(1 << WGM21);\n")
        f.write("  // OC2A no inversor (COM2A1=1, COM2A0=0)\n")
        f.write("  TCCR2A |= (1 << COM2A1);\n")
        f.write("  TCCR2A &= ~(1 << COM2A0);\n")
        f.write(f"  OCR2A = {OCR2A[0]};\n\n")

        f.write("  // ---- Prescaler ----\n")
        if prescaler == 1:
            f.write("  TCCR1B |= (1 << CS10);\n")
            f.write("  TCCR2B |= (1 << CS20);\n")
        elif prescaler == 8:
            f.write("  TCCR1B |= (1 << CS11);\n")
            f.write("  TCCR2B |= (1 << CS21);\n")
        elif prescaler == 64:
            f.write("  TCCR1B |= (1 << CS11) | (1 << CS10);\n")
            f.write("  TCCR2B |= (1 << CS22);\n")
        elif prescaler == 256:
            f.write("  TCCR1B |= (1 << CS12);\n")
            f.write("  TCCR2B |= (1 << CS22) | (1 << CS21);\n")
        elif prescaler == 1024:
            f.write("  TCCR1B |= (1 << CS12) | (1 << CS10);\n")
            f.write("  TCCR2B |= (1 << CS22) | (1 << CS21) | (1 << CS20);\n")
        f.write("\n")

        f.write("  // Habilitar interrupción por desbordamiento de Timer1\n")
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

        f.write("const unsigned char OCR2A_table[N] PROGMEM = {\n")
        for i, v in enumerate(OCR2A):
            f.write(f"  {v}{',' if i < N-1 else ''}\n")
        f.write("};\n\n")

        f.write("volatile unsigned char index = 0;\n\n")

        f.write("ISR(TIMER1_OVF_vect) {\n")
        f.write("  index++;\n")
        f.write("  if (index >= N) index = 0;\n")
        f.write("  OCR1A = pgm_read_word(&OCR1A_table[index]);\n")
        f.write("  OCR1B = pgm_read_word(&OCR1B_table[index]);\n")
        f.write("  OCR2A = pgm_read_byte(&OCR2A_table[index]);\n")
        f.write("}\n\n")

        f.write("void loop() {\n")
        f.write("  // Todo el control se realiza por interrupción\n")
        f.write("}\n")

    print(f"Archivo generado: {ruta}")


# =============================================================================
#  MÓDULO DE SIMULACIÓN, CÁLCULO DE RMS Y THD, Y GRÁFICAS
# =============================================================================

def simular_senales(f_ref, ma, mf, ref_a, ref_b, ref_c, pts_por_periodo=200):
    """
    Simula las señales PWM para las tres fases y las tensiones de línea.
    Utiliza portadora triangular en [-1, 1] y comparación directa con la referencia.
    Retorna: t, outA, outB, outC, Vab, Vbc, Vca
    """
    f_c = mf * f_ref
    T_c = 1.0 / f_c
    num_periodos = 2 * mf
    tiempo_total = num_periodos * T_c
    n_pts = num_periodos * pts_por_periodo
    t = np.linspace(0, tiempo_total, n_pts, endpoint=False)

    # Portadora triangular en [-1, 1]
    fase = (t % T_c) / T_c
    portadora = 1 - 4 * np.abs(fase - 0.5)

    # Referencias repetidas para dos ciclos y expandidas
    ref_a_repetida = np.repeat(np.tile(ref_a, 2), pts_por_periodo)
    ref_b_repetida = np.repeat(np.tile(ref_b, 2), pts_por_periodo)
    ref_c_repetida = np.repeat(np.tile(ref_c, 2), pts_por_periodo)

    # PWM: 1 si referencia > portadora
    outA = (ref_a_repetida > portadora).astype(float)
    outB = (ref_b_repetida > portadora).astype(float)
    outC = (ref_c_repetida > portadora).astype(float)

    # Tensiones de línea (normalizadas)
    Vab = outA - outB
    Vbc = outB - outC
    Vca = outC - outA

    return t, outA, outB, outC, Vab, Vbc, Vca


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


def graficar_simulacion(f_ref, ma, mf, ref_a, ref_b, ref_c, tipo, params):
    """
    Muestra tres subplots en vertical:
      1) Referencias + portadora triangular
      2) PWM de las tres fases desplazadas verticalmente (offset aumentado)
      3) Tensiones de línea (Vab, Vbc, Vca) desplazadas verticalmente para mejor visualización
    Retorna (RMS_Vab, THD_Vab).
    """
    # Simulación
    t, outA, outB, outC, Vab, Vbc, Vca = simular_senales(f_ref, ma, mf, ref_a, ref_b, ref_c)

    # Calcular RMS y THD para Vab
    V_rms, _, thd = calcular_rms_thd(t, Vab, f_ref)

    # Referencia y portadora de alta resolución para la gráfica
    f_c = mf * f_ref
    T_c = 1.0 / f_c
    num_periodos = 2 * mf
    tiempo_total = num_periodos * T_c
    pts_high = 1000 * num_periodos
    t_high = np.linspace(0, tiempo_total, pts_high, endpoint=False)
    theta_high = 2 * np.pi * f_ref * t_high

    # Obtener referencias escaladas para la gráfica
    va_high, vb_high, vc_high = generar_referencias_trifasicas(tipo, ma, theta_high, params)

    # Portadora triangular
    fase_high = (t_high % T_c) / T_c
    portadora_high = 1 - 4 * np.abs(fase_high - 0.5)

    # Crear figura con 3 subplots verticales
    fig, axs = plt.subplots(3, 1, figsize=(14, 12))
    fig.suptitle(
        f'PWM Trifásico con portadora triangular - 2 ciclos completos\n'
        f'f_ref = {f_ref:.1f} Hz, ma = {ma:.2f}, mf = {mf}\n'
        f'Tipo: {tipo}  |  RMS(Vab) = {V_rms:.4f}  |  THD(Vab) = {thd:.2f}%',
        fontsize=14
    )

    # ---- Subplot 1: Referencias y portadora ----
    axs[0].plot(t_high, va_high, 'b', lw=1.5, label='Va')
    axs[0].plot(t_high, vb_high, 'g', lw=1.5, label='Vb')
    axs[0].plot(t_high, vc_high, 'r', lw=1.5, label='Vc')
    axs[0].plot(t_high, portadora_high, 'k', lw=0.6, alpha=0.5, label='Portadora')
    axs[0].axhline(y=0, color='gray', linestyle='--', linewidth=0.5)
    axs[0].set_ylabel('Amplitud')
    axs[0].grid(True)
    axs[0].legend()
    axs[0].set_title('Referencias + Portadora (alta resolución)')
    axs[0].set_xlim(t_high[0], t_high[-1])

    # ---- Subplot 2: PWM de las tres fases (desplazadas con offset mayor) ----
    offset_pwm = 1.5  # Aumentado para evitar superposición
    axs[1].plot(t, outA + 2*offset_pwm, 'b', drawstyle='steps-post', lw=0.8, label='Fase A (D9)')
    axs[1].plot(t, outB + offset_pwm, 'g', drawstyle='steps-post', lw=0.8, label='Fase B (D10)')
    axs[1].plot(t, outC, 'r', drawstyle='steps-post', lw=0.8, label='Fase C (D11)')
    axs[1].axhline(y=2*offset_pwm, color='gray', linestyle=':', linewidth=0.5)
    axs[1].axhline(y=offset_pwm, color='gray', linestyle=':', linewidth=0.5)
    axs[1].axhline(y=0, color='gray', linestyle=':', linewidth=0.5)
    axs[1].set_ylabel('Nivel desplazado')
    axs[1].set_xlabel('Tiempo (s)')
    axs[1].grid(True)
    axs[1].legend()
    axs[1].set_title('Señales PWM de las tres fases (desplazadas verticalmente)')
    axs[1].set_xlim(t[0], t[-1])
    # Ajustar límites y para que quede bien
    ymin = -0.5
    ymax = 2*offset_pwm + 1.2
    axs[1].set_ylim(ymin, ymax)

    # ---- Subplot 3: Tensiones de línea con desplazamiento vertical ----
    offset_linea = 2.5  # Desplazamiento para separar las tres tensiones
    axs[2].plot(t, Vab + offset_linea, 'b', drawstyle='steps-post', lw=0.8, label='Vab + offset')
    axs[2].plot(t, Vbc, 'g', drawstyle='steps-post', lw=0.8, label='Vbc')
    axs[2].plot(t, Vca - offset_linea, 'r', drawstyle='steps-post', lw=0.8, label='Vca - offset')
    axs[2].axhline(y=offset_linea, color='gray', linestyle=':', linewidth=0.5)
    axs[2].axhline(y=0, color='gray', linestyle=':', linewidth=0.5)
    axs[2].axhline(y=-offset_linea, color='gray', linestyle=':', linewidth=0.5)
    axs[2].set_ylabel('Tensión desplazada')
    axs[2].set_xlabel('Tiempo (s)')
    axs[2].grid(True)
    axs[2].legend()
    axs[2].set_title('Tensiones de línea (Vab, Vbc, Vca) desplazadas verticalmente')
    axs[2].set_xlim(t[0], t[-1])
    # Ajustar límites
    ymin = -offset_linea - 1.2
    ymax = offset_linea + 1.2
    axs[2].set_ylim(ymin, ymax)

    plt.tight_layout()
    plt.show()
    return V_rms, thd


# =============================================================================
#  INTERFAZ GRÁFICA (Tkinter)
# =============================================================================

class SPWMTrifasicoApp:
    """Aplicación principal con interfaz gráfica para inversor trifásico."""

    def __init__(self, root):
        self.root = root
        root.title("Generador PWM para Inversor Trifásico (Arduino Uno)")
        root.geometry("620x620")
        root.resizable(False, False)

        # Variables de los parámetros
        self.f_ref = tk.StringVar(value="60.0")
        self.ma = tk.StringVar(value="0.8")
        self.mf = tk.StringVar(value="12")
        self.tipo = tk.StringVar(value="SPWM")
        self.param_a3 = tk.StringVar(value="0.25")
        self.param_k = tk.StringVar(value="3.0")

        # Variables para mostrar resultados
        self.rms_label = tk.StringVar(value="RMS(Vab): ---")
        self.thd_label = tk.StringVar(value="THD(Vab): ---%")

        self._crear_widgets()

    def _crear_widgets(self):
        root = self.root
        row = 0

        tk.Label(root, text="Frecuencia de referencia (Hz):").grid(row=row, column=0, padx=10, pady=5, sticky='e')
        tk.Entry(root, textvariable=self.f_ref, width=15).grid(row=row, column=1, padx=10, pady=5, sticky='w')
        row += 1

        tk.Label(root, text="Índice de modulación ma (0-1.15):").grid(row=row, column=0, padx=10, pady=5, sticky='e')
        tk.Entry(root, textvariable=self.ma, width=15).grid(row=row, column=1, padx=10, pady=5, sticky='w')
        row += 1

        tk.Label(root, text="Índice de modulación mf (entero):").grid(row=row, column=0, padx=10, pady=5, sticky='e')
        tk.Entry(root, textvariable=self.mf, width=15).grid(row=row, column=1, padx=10, pady=5, sticky='w')
        row += 1

        tk.Label(root, text="Tipo de modulación:").grid(row=row, column=0, padx=10, pady=5, sticky='e')
        self.tipo_combo = ttk.Combobox(root, textvariable=self.tipo,
                                       values=["SPWM", "THIPWM", "MPWM", "Onda Cuadrada", "SVPWM"],
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
        for w in self.frame_params.winfo_children():
            w.destroy()

        tipo = self.tipo.get()
        if tipo == "THIPWM":
            tk.Label(self.frame_params, text="Amplitud 3ra armónica (0-1):").pack(side=tk.LEFT, padx=5)
            tk.Entry(self.frame_params, textvariable=self.param_a3, width=8).pack(side=tk.LEFT, padx=5)
        elif tipo == "MPWM":
            tk.Label(self.frame_params, text="Factor de forma k (1-10):").pack(side=tk.LEFT, padx=5)
            tk.Entry(self.frame_params, textvariable=self.param_k, width=8).pack(side=tk.LEFT, padx=5)

    def _obtener_parametros(self):
        f_ref = float(self.f_ref.get())
        ma = float(self.ma.get())
        mf = int(self.mf.get())
        tipo = self.tipo.get()
        params = {}
        if tipo == "THIPWM":
            params['a3'] = float(self.param_a3.get())
        elif tipo == "MPWM":
            params['k'] = float(self.param_k.get())
        return f_ref, ma, mf, tipo, params

    def _graficar(self):
        try:
            f_ref, ma, mf, tipo, params = self._obtener_parametros()

            if not (0 <= ma <= 1.15):
                raise ValueError("ma debe estar en [0, 1.15]")
            if mf < 1:
                mf = 1
                self.mf.set(str(mf))

            # Generar tablas de referencia
            theta = np.linspace(0, 2*np.pi, mf, endpoint=False)
            if tipo == "SVPWM":
                da, db, dc = svpwm_generate(ma, theta)
                # Para la gráfica, necesitamos las referencias equivalentes
                # Podemos usar las referencias senoidales originales para mostrarlas
                va = ma * np.sin(theta)
                vb = ma * np.sin(theta - 2*np.pi/3)
                vc = ma * np.sin(theta + 2*np.pi/3)
                # Pero para la simulación usamos las señales de modulación reales
                ref_a = 2*da - 1
                ref_b = 2*db - 1
                ref_c = 2*dc - 1
                # Para la gráfica de referencias, usamos las senoidales para claridad
                ref_a_plot = va
                ref_b_plot = vb
                ref_c_plot = vc
            else:
                va, vb, vc = generar_referencias_trifasicas(tipo, ma, theta, params)
                ref_a = va
                ref_b = vb
                ref_c = vc
                ref_a_plot = va
                ref_b_plot = vb
                ref_c_plot = vc

            # Graficar (pasar las referencias de modulación reales)
            V_rms, thd = graficar_simulacion(f_ref, ma, mf, ref_a, ref_b, ref_c, tipo, params)
            self.rms_label.set(f"RMS(Vab) = {V_rms:.4f}")
            self.thd_label.set(f"THD(Vab) = {thd:.2f}%")
            self.status.config(text="Gráficas actualizadas", fg="green")

        except Exception as e:
            messagebox.showerror("Error", str(e))
            self.status.config(text="Error en gráficas", fg="red")

    def _generar_codigo(self):
        try:
            f_ref, ma, mf, tipo, params = self._obtener_parametros()

            if not (0 <= ma <= 1.15):
                raise ValueError("ma debe estar en [0, 1.15]")
            if mf < 1:
                mf = 1
                self.mf.set(str(mf))

            # Generar tablas de ciclo de trabajo
            da, db, dc = generar_tablas(tipo, ma, mf, params)

            # Calcular RMS y THD para Vab (para el encabezado)
            theta = np.linspace(0, 2*np.pi, mf, endpoint=False)
            if tipo == "SVPWM":
                ref_a = 2*da - 1
                ref_b = 2*db - 1
                ref_c = 2*dc - 1
            else:
                va, vb, vc = generar_referencias_trifasicas(tipo, ma, theta, params)
                ref_a = va
                ref_b = vb
                ref_c = vc

            t, _, _, _, Vab, _, _ = simular_senales(f_ref, ma, mf, ref_a, ref_b, ref_c)
            V_rms, _, thd = calcular_rms_thd(t, Vab, f_ref)

            # Calcular parámetros del timer
            prescaler, ICR1, f_c_actual = calcular_parametros_timer(f_ref, mf)

            # Generar .ino
            generar_archivo_ino(f_ref, ma, mf, tipo, params,
                                prescaler, ICR1, f_c_actual,
                                da, db, dc, rms_ab=V_rms, thd_ab=thd)

            self.status.config(text="¡Código Arduino generado! (inversor_trifasico.ino)", fg="green")
            messagebox.showinfo("Éxito", "Archivo inversor_trifasico.ino generado en la raíz.")

        except Exception as e:
            messagebox.showerror("Error", str(e))
            self.status.config(text="Error al generar código", fg="red")


# =============================================================================
#  PUNTO DE ENTRADA
# =============================================================================

if __name__ == "__main__":
    root = tk.Tk()
    app = SPWMTrifasicoApp(root)
    root.mainloop()
