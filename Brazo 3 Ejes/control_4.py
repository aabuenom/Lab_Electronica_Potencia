# =====================================================================
# control_brazo.py - Interfaz gráfica para brazo robótico de 4 servos
#                   con control individual (auto/manual) e IR.
#                   SIN gráfica de evolución temporal.
#                   Muestra ángulos numéricos en tiempo real.
#                   + Ventana de configuración con tkinter (puerto + ayuda)
# =====================================================================

import serial
import serial.tools.list_ports
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.widgets import Slider, Button
import matplotlib.gridspec as gridspec
import numpy as np
import threading
import time
from mpl_toolkits.mplot3d import Axes3D
import tkinter as tk
from tkinter import ttk

# ===== CONFIGURACIÓN =====
PUERTO = None          # Se asignará desde la ventana tkinter
BAUDRATE = 115200
TIMEOUT = 0.1
STEP = 5
DEBUG = False
OFFSET = 90.0

# ===== VARIABLES GLOBALES =====
ser = None
corriendo = True
ang_actual = [90.0, 90.0, 90.0, 90.0]
modos_servo = [True, True, True, True]  # False=auto, True=manual
necesita_actualizar_interfaz = False
ultimo_ang_actual = [None]*4
lock = threading.Lock()

# ==================================================
# VENTANA DE CONFIGURACIÓN CON TKINTER
# ==================================================
def ventana_configuracion():
    root = tk.Tk()
    root.title("Configuración del Brazo Robótico")
    root.geometry("500x400")
    root.resizable(False, False)

    # Frame principal
    frame = ttk.Frame(root, padding=20)
    frame.pack(fill="both", expand=True)

    # Título
    ttk.Label(frame, text="Selecciona el puerto serie", font=("Arial", 14)).pack(pady=10)

    # Detectar puertos disponibles
    puertos = [port.device for port in serial.tools.list_ports.comports()]
    if not puertos:
        puertos = ["/dev/ttyUSB0", "/dev/ttyACM0", "COM1"]  # valores por defecto

    var_puerto = tk.StringVar(value=puertos[0] if puertos else "")
    combo = ttk.Combobox(frame, textvariable=var_puerto, values=puertos, state="readonly", width=30)
    combo.pack(pady=10)

    # Botón Conectar
    def conectar():
        global PUERTO
        PUERTO = var_puerto.get()
        if not PUERTO:
            tk.messagebox.showerror("Error", "Selecciona un puerto válido")
            return
        root.destroy()   # Cierra la ventana y continúa con el programa principal

    btn_conectar = ttk.Button(frame, text="Conectar", command=conectar)
    btn_conectar.pack(pady=10)

    # Separador
    ttk.Separator(frame, orient="horizontal").pack(fill="x", pady=15)

    # Ayuda del control remoto
    ttk.Label(frame, text="Ayuda del control remoto", font=("Arial", 12, "bold")).pack(anchor="w", pady=5)
    texto_ayuda = (
        "Teclas numéricas 1-9: funcionalidad del brazo \n"
        "Flecha izquierda / derecha:  Mueven la articulación 1 (Art1) en pasos de ±5°\n"
        "Flecha arriba / abajo:       Mueven la articulación 2 (Art2) en pasos de ±5°\n"
        "Tecla 'r':                   Resetea todos los ángulos a 90°\n"
        "Control IR:  Botones 4,6,2,8,0,200+, CH-, CH+, EQ, + \n"
        "\nNota: Los movimientos con teclas solo funcionan en modo MANUAL."
    )
    label_ayuda = ttk.Label(frame, text=texto_ayuda, justify="left", wraplength=450, font=("Arial", 10))
    label_ayuda.pack(anchor="w", pady=5)

    root.mainloop()

# ==================================================
# FUNCIONES SERIE (igual que antes)
# ==================================================
def conectar_serial():
    global ser
    try:
        ser = serial.Serial(PUERTO, BAUDRATE, timeout=TIMEOUT)
        ser.flushInput()
        print(f"Conectado a {PUERTO}")
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False

def enviar_comando(cmd):
    if ser and ser.is_open:
        ser.write((cmd + '\n').encode())

def enviar_angulos(a0, a1, a2, a3):
    enviar_comando(f"S:{a0:.1f},{a1:.1f},{a2:.1f},{a3:.1f}")

def enviar_tecla(tecla):
    enviar_comando(tecla)

def enviar_modo_servo(idx, modo):
    enviar_comando(f"C:{idx},{modo}")

def leer_datos():
    global ang_actual, modos_servo, necesita_actualizar_interfaz
    if ser and ser.is_open:
        try:
            line = ser.readline().decode().strip()
            if not line:
                return
            if DEBUG:
                print(f"Recibido: {line}")
            if line.startswith('A:'):
                partes = line[2:].split(',')
                if len(partes) == 4:
                    try:
                        vals = [float(p) for p in partes]
                        with lock:
                            ang_actual = vals
                    except ValueError:
                        pass
            elif line.startswith('M:'):
                partes = line[2:].split(',')
                if len(partes) == 4:
                    try:
                        modos_recibidos = [int(p) for p in partes]
                        with lock:
                            for i in range(4):
                                modos_servo[i] = (modos_recibidos[i] == 1)
                            necesita_actualizar_interfaz = True
                    except ValueError:
                        pass
        except Exception as e:
            if DEBUG:
                print(f"Error lectura: {e}")

def hilo_lectura():
    while corriendo:
        leer_datos()
        time.sleep(0.001)

# ==================================================
# PROGRAMA PRINCIPAL (matplotlib)
# ==================================================
def ejecutar_interfaz():
    # La variable PUERTO ya debe estar definida
    if not conectar_serial():
        print("No se pudo conectar. Saliendo.")
        return

    # Iniciar hilo de lectura
    hilo = threading.Thread(target=hilo_lectura, daemon=True)
    hilo.start()

    # ===== CONFIGURACIÓN DE LA FIGURA =====
    fig = plt.figure(figsize=(16, 10))
    fig.subplots_adjust(left=0.05, bottom=0.25, right=0.95, top=0.93)

    gs = gridspec.GridSpec(2, 3, height_ratios=[1, 1], width_ratios=[1, 1, 1])

    # ---- 4 gráficos polares (2x2) ----
    colores = ['red', 'blue', 'green', 'orange']
    nombres = ['Art1', 'Art2', 'Art3', 'Garra']
    axes_polar = []
    polar_lines = []
    polar_points = []
    polar_texts = []

    for row in range(2):
        for col in range(2):
            idx = row*2 + col
            ax = fig.add_subplot(gs[row, col], projection='polar')
            ax.set_theta_zero_location('E')
            ax.set_theta_direction(1)
            ax.set_ylim(0, 1)
            ax.set_yticks([])
            ax.set_title(nombres[idx], fontsize=12)
            ax.grid(True, linestyle='--', alpha=0.5)
            line, = ax.plot([], [], color=colores[idx], linewidth=3)
            point, = ax.plot([], [], 'o', color=colores[idx], markersize=10)
            axes_polar.append(ax)
            polar_lines.append(line)
            polar_points.append(point)
            txt = ax.text(0.5, -0.15, "90.0°", transform=ax.transAxes,
                          ha='center', va='center', fontsize=12, fontweight='bold',
                          bbox=dict(boxstyle="round", facecolor='white', alpha=0.8))
            polar_texts.append(txt)

    # ---- Gráfico 3D ----
    ax4 = fig.add_subplot(gs[:, 2], projection='3d')
    ax4.set_xlabel('X')
    ax4.set_ylabel('Y')
    ax4.set_zlabel('Z')
    ax4.set_xlim(-1.5, 1.5)
    ax4.set_ylim(-1.5, 1.5)
    ax4.set_zlim(-0.5, 2.0)
    ax4.view_init(elev=25, azim=-45)
    ax4.quiver(0, 0, 0, 1.5, 0, 0, color='gray', alpha=0.4, arrow_length_ratio=0.1)
    ax4.quiver(0, 0, 0, 0, 1.5, 0, color='gray', alpha=0.4, arrow_length_ratio=0.1)
    ax4.quiver(0, 0, 0, 0, 0, 1.5, color='gray', alpha=0.4, arrow_length_ratio=0.1)

    lineas_3d = []
    for i in range(3):
        l, = ax4.plot([], [], [], color=colores[i], linewidth=4)
        lineas_3d.append(l)
    punto_final, = ax4.plot([], [], [], 'ko', markersize=10, markeredgecolor='darkred')
    proj_xy, = ax4.plot([], [], [], 'gray', linestyle='--', linewidth=1, alpha=0.5)
    proj_xz, = ax4.plot([], [], [], 'gray', linestyle='--', linewidth=1, alpha=0.5)
    proj_yz, = ax4.plot([], [], [], 'gray', linestyle='--', linewidth=1, alpha=0.5)
    arrow_vec = ax4.quiver([0], [0], [0], [0], [0], [0],
                           color='green', arrow_length_ratio=0.2, linewidth=2, alpha=0.7)

    text_ang = ax4.text2D(0.02, 0.98, "", transform=ax4.transAxes,
                          ha='left', va='top', fontsize=11,
                          bbox=dict(boxstyle="round", facecolor='white', alpha=0.85, edgecolor='gray'))

    # ===== CONTROLES =====
    sliders = []
    botones_modo = []
    botones_step = []
    textos_modo = []
    textos_angulo_slider = []

    def actualizar_interfaz_modos():
        for i, (b, s, txt) in enumerate(zip(botones_modo, sliders, textos_modo)):
            if modos_servo[i]:  # manual
                b.label.set_text('M')
                b.color = 'lightgreen'
                s.set_active(True)
                s.ax.set_facecolor('#e6ffe6')
                txt.set_text('MANUAL')
                txt.set_color('darkorange')
            else:               # auto
                b.label.set_text('A')
                b.color = 'lightgray'
                s.set_active(False)
                s.ax.set_facecolor('#f0f0f0')
                txt.set_text('AUTO')
                txt.set_color('forestgreen')
        # Botones globales
        if all(modos_servo):
            boton_manual.color = 'lightgreen'
            boton_auto.color = 'lightgray'
        elif not any(modos_servo):
            boton_manual.color = 'lightgray'
            boton_auto.color = 'lightgreen'
        else:
            boton_manual.color = 'lightgray'
            boton_auto.color = 'lightgray'
        fig.canvas.draw_idle()

    def toggle_modo_servo(idx):
        nuevo_modo = 0 if modos_servo[idx] else 1
        modos_servo[idx] = (nuevo_modo == 1)
        enviar_modo_servo(idx, nuevo_modo)
        actualizar_interfaz_modos()

    # Posiciones de los controles
    y_row1 = 0.16
    y_row2 = 0.09
    y_btns = 0.03

    # Art1
    ax_s1 = plt.axes([0.08, y_row1, 0.12, 0.025])
    s1 = Slider(ax_s1, 'Art1', 0, 180, valinit=90, valstep=1)
    sliders.append(s1)
    ax_ang1 = plt.axes([0.205, y_row1, 0.04, 0.025])
    ang1_txt = ax_ang1.text(0.5, 0.5, '90.0°', ha='center', va='center', fontsize=10, fontweight='bold')
    ax_ang1.axis('off')
    textos_angulo_slider.append(ang1_txt)

    ax_b1 = plt.axes([0.25, y_row1, 0.03, 0.025])
    b1 = Button(ax_b1, 'A', color='lightgray')
    b1.on_clicked(lambda event, idx=0: toggle_modo_servo(idx))
    botones_modo.append(b1)
    ax_txt1 = plt.axes([0.29, y_row1, 0.05, 0.025])
    txt1 = ax_txt1.text(0.5, 0.5, 'AUTO', ha='center', va='center', fontsize=8, color='forestgreen')
    ax_txt1.axis('off')
    textos_modo.append(txt1)
    ax_s1_dec = plt.axes([0.35, y_row1, 0.025, 0.025])
    b_s1_dec = Button(ax_s1_dec, '-', color='lightcoral')
    ax_s1_inc = plt.axes([0.38, y_row1, 0.025, 0.025])
    b_s1_inc = Button(ax_s1_inc, '+', color='lightblue')
    botones_step.append((b_s1_dec, b_s1_inc))

    # Art2
    ax_s2 = plt.axes([0.48, y_row1, 0.12, 0.025])
    s2 = Slider(ax_s2, 'Art2', 0, 180, valinit=90, valstep=1)
    sliders.append(s2)
    ax_ang2 = plt.axes([0.605, y_row1, 0.04, 0.025])
    ang2_txt = ax_ang2.text(0.5, 0.5, '90.0°', ha='center', va='center', fontsize=10, fontweight='bold')
    ax_ang2.axis('off')
    textos_angulo_slider.append(ang2_txt)

    ax_b2 = plt.axes([0.65, y_row1, 0.03, 0.025])
    b2 = Button(ax_b2, 'A', color='lightgray')
    b2.on_clicked(lambda event, idx=1: toggle_modo_servo(idx))
    botones_modo.append(b2)
    ax_txt2 = plt.axes([0.69, y_row1, 0.05, 0.025])
    txt2 = ax_txt2.text(0.5, 0.5, 'AUTO', ha='center', va='center', fontsize=8, color='forestgreen')
    ax_txt2.axis('off')
    textos_modo.append(txt2)
    ax_s2_dec = plt.axes([0.75, y_row1, 0.025, 0.025])
    b_s2_dec = Button(ax_s2_dec, '-', color='lightcoral')
    ax_s2_inc = plt.axes([0.78, y_row1, 0.025, 0.025])
    b_s2_inc = Button(ax_s2_inc, '+', color='lightblue')
    botones_step.append((b_s2_dec, b_s2_inc))

    # Art3
    ax_s3 = plt.axes([0.08, y_row2, 0.12, 0.025])
    s3 = Slider(ax_s3, 'Art3', 0, 180, valinit=90, valstep=1)
    sliders.append(s3)
    ax_ang3 = plt.axes([0.205, y_row2, 0.04, 0.025])
    ang3_txt = ax_ang3.text(0.5, 0.5, '90.0°', ha='center', va='center', fontsize=10, fontweight='bold')
    ax_ang3.axis('off')
    textos_angulo_slider.append(ang3_txt)

    ax_b3 = plt.axes([0.25, y_row2, 0.025, 0.025])
    b3 = Button(ax_b3, 'A', color='lightgray')
    b3.on_clicked(lambda event, idx=2: toggle_modo_servo(idx))
    botones_modo.append(b3)
    ax_txt3 = plt.axes([0.29, y_row2, 0.05, 0.025])
    txt3 = ax_txt3.text(0.5, 0.5, 'AUTO', ha='center', va='center', fontsize=8, color='forestgreen')
    ax_txt3.axis('off')
    textos_modo.append(txt3)
    ax_s3_dec = plt.axes([0.35, y_row2, 0.025, 0.025])
    b_s3_dec = Button(ax_s3_dec, '-', color='lightcoral')
    ax_s3_inc = plt.axes([0.38, y_row2, 0.025, 0.025])
    b_s3_inc = Button(ax_s3_inc, '+', color='lightblue')
    botones_step.append((b_s3_dec, b_s3_inc))

    # Garra
    ax_s4 = plt.axes([0.48, y_row2, 0.12, 0.025])
    s4 = Slider(ax_s4, 'Garra', 0, 180, valinit=90, valstep=1)
    sliders.append(s4)
    ax_ang4 = plt.axes([0.605, y_row2, 0.04, 0.025])
    ang4_txt = ax_ang4.text(0.5, 0.5, '90.0°', ha='center', va='center', fontsize=10, fontweight='bold')
    ax_ang4.axis('off')
    textos_angulo_slider.append(ang4_txt)

    ax_b4 = plt.axes([0.65, y_row2, 0.025, 0.025])
    b4 = Button(ax_b4, 'A', color='lightgray')
    b4.on_clicked(lambda event, idx=3: toggle_modo_servo(idx))
    botones_modo.append(b4)
    ax_txt4 = plt.axes([0.69, y_row2, 0.05, 0.025])
    txt4 = ax_txt4.text(0.5, 0.5, 'AUTO', ha='center', va='center', fontsize=8, color='forestgreen')
    ax_txt4.axis('off')
    textos_modo.append(txt4)
    ax_s4_dec = plt.axes([0.75, y_row2, 0.025, 0.025])
    b_s4_dec = Button(ax_s4_dec, '-', color='lightcoral')
    ax_s4_inc = plt.axes([0.78, y_row2, 0.025, 0.025])
    b_s4_inc = Button(ax_s4_inc, '+', color='lightblue')
    botones_step.append((b_s4_dec, b_s4_inc))

    # ---- Botones principales ----
    ax_btn_manual = plt.axes([0.08, y_btns, 0.06, 0.035])
    boton_manual = Button(ax_btn_manual, 'Manual', color='lightgreen')
    ax_btn_auto = plt.axes([0.15, y_btns, 0.06, 0.035])
    boton_auto = Button(ax_btn_auto, 'Auto', color='lightgray')

    def set_modo_manual():
        for i in range(4):
            modos_servo[i] = True
            enviar_modo_servo(i, 1)
        actualizar_interfaz_modos()

    def set_modo_auto():
        for i in range(4):
            modos_servo[i] = False
            enviar_modo_servo(i, 0)
        actualizar_interfaz_modos()

    boton_manual.on_clicked(lambda event: set_modo_manual())
    boton_auto.on_clicked(lambda event: set_modo_auto())

    ax_boton_enviar = plt.axes([0.70, y_btns, 0.06, 0.035])
    boton_enviar = Button(ax_boton_enviar, 'Enviar')
    ax_boton_barrido = plt.axes([0.78, y_btns, 0.06, 0.035])
    boton_barrido = Button(ax_boton_barrido, 'Barrido')
    ax_boton_reset = plt.axes([0.86, y_btns, 0.06, 0.035])
    boton_reset = Button(ax_boton_reset, 'Reset 90°')

    def enviar_desde_sliders():
        vals = [s.val for s in sliders]
        enviar_angulos(*vals)
    boton_enviar.on_clicked(lambda event: enviar_desde_sliders())

    def reset_angulos():
        for s in sliders:
            s.set_val(90)
        enviar_desde_sliders()
    boton_reset.on_clicked(lambda event: reset_angulos())

    def step_angle(idx, delta):
        if not modos_servo[idx]:
            return
        nuevo = sliders[idx].val + delta
        nuevo = max(0, min(180, nuevo))
        sliders[idx].set_val(nuevo)
        enviar_desde_sliders()

    for i, (b_dec, b_inc) in enumerate(botones_step):
        b_dec.on_clicked(lambda event, idx=i: step_angle(idx, -STEP))
        b_inc.on_clicked(lambda event, idx=i: step_angle(idx, STEP))

    def barrido():
        def ejecutar():
            for ang in range(0, 181, STEP):
                enviar_angulos(ang, 90, 90, 90)
                time.sleep(0.05)
            for ang in range(0, 181, STEP):
                enviar_angulos(90, ang, 90, 90)
                time.sleep(0.05)
            for ang in range(0, 181, STEP):
                enviar_angulos(90, 90, ang, 90)
                time.sleep(0.05)
            for ang in range(0, 181, STEP):
                enviar_angulos(90, 90, 90, ang)
                time.sleep(0.05)
            print("Barrido completado")
        threading.Thread(target=ejecutar, daemon=True).start()
    boton_barrido.on_clicked(lambda event: barrido())

    # ===== TECLADO =====
    def on_key(event):
        if event.key in ['1','2','3','4','5','6','7','8','9']:
            enviar_tecla(event.key)
            return
        if event.key == 'left' and modos_servo[0]:
            step_angle(0, -STEP)
        elif event.key == 'right' and modos_servo[0]:
            step_angle(0, STEP)
        elif event.key == 'down' and modos_servo[1]:
            step_angle(1, -STEP)
        elif event.key == 'up' and modos_servo[1]:
            step_angle(1, STEP)
        elif event.key == 'r':
            reset_angulos()
    fig.canvas.mpl_connect('key_press_event', on_key)

    # ===== ANIMACIÓN =====
    def actualizar_grafica(frame):
        global necesita_actualizar_interfaz, ultimo_ang_actual

        if necesita_actualizar_interfaz:
            necesita_actualizar_interfaz = False
            actualizar_interfaz_modos()

        with lock:
            # Polares
            for i in range(4):
                rad = np.radians(ang_actual[i])
                polar_lines[i].set_data([rad, rad], [0, 1])
                polar_points[i].set_data([rad], [1])
                polar_texts[i].set_text(f"{ang_actual[i]:.1f}°")

            # 3D
            a0 = np.radians(ang_actual[0])
            a1 = np.radians(ang_actual[1])
            a2 = np.radians(ang_actual[2] - 90)
            L1, L2, L3 = 1.0, 0.8, 0.6
            x1 = L1 * np.cos(a0)
            y1 = L1 * np.sin(a0)
            z1 = 0.0
            x2 = x1 + L2 * np.cos(a1) * np.cos(a0)
            y2 = y1 + L2 * np.cos(a1) * np.sin(a0)
            z2 = L2 * np.sin(a1)
            x3 = x2 + L3 * np.cos(a1 - a2) * np.cos(a0)
            y3 = y2 + L3 * np.cos(a1 - a2) * np.sin(a0)
            z3 = z2 + L3 * np.sin(a1 - a2)

            lineas_3d[0].set_data([0, x1], [0, y1])
            lineas_3d[0].set_3d_properties([0, z1])
            lineas_3d[1].set_data([x1, x2], [y1, y2])
            lineas_3d[1].set_3d_properties([z1, z2])
            lineas_3d[2].set_data([x2, x3], [y2, y3])
            lineas_3d[2].set_3d_properties([z2, z3])
            punto_final.set_data([x3], [y3])
            punto_final.set_3d_properties([z3])
            proj_xy.set_data([0, x3], [0, y3])
            proj_xy.set_3d_properties([0, 0])
            proj_xz.set_data([0, x3], [0, 0])
            proj_xz.set_3d_properties([0, z3])
            proj_yz.set_data([0, 0], [0, y3])
            proj_yz.set_3d_properties([0, z3])
            arrow_vec.set_offsets(np.array([[0, 0, 0]]))
            arrow_vec.set_segments(np.array([[[0, 0, 0], [x3, y3, z3]]]))

            text_ang.set_text(
                f"Art1: {ang_actual[0]:.1f}°\n"
                f"Art2: {ang_actual[1]:.1f}°\n"
                f"Art3: {ang_actual[2]:.1f}°\n"
                f"Garra: {ang_actual[3]:.1f}°"
            )

            # Textos de sliders
            for i, txt in enumerate(textos_angulo_slider):
                txt.set_text(f"{ang_actual[i]:.1f}°")

            # Sincronizar sliders en AUTO
            for i, s in enumerate(sliders):
                if not modos_servo[i]:
                    if ultimo_ang_actual[i] is None or abs(ang_actual[i] - ultimo_ang_actual[i]) > 0.5:
                        s.set_val(ang_actual[i])
                        ultimo_ang_actual[i] = ang_actual[i]

        return (polar_lines + polar_points + polar_texts + lineas_3d +
                [punto_final, proj_xy, proj_xz, proj_yz, arrow_vec, text_ang] +
                textos_angulo_slider)

    def init():
        for line in polar_lines:
            line.set_data([], [])
        for point in polar_points:
            point.set_data([], [])
        for txt in polar_texts:
            txt.set_text("0.0°")
        for line in lineas_3d:
            line.set_data([], [])
            line.set_3d_properties([])
        punto_final.set_data([], [])
        punto_final.set_3d_properties([])
        proj_xy.set_data([], [])
        proj_xy.set_3d_properties([])
        proj_xz.set_data([], [])
        proj_xz.set_3d_properties([])
        proj_yz.set_data([], [])
        proj_yz.set_3d_properties([])
        arrow_vec.set_offsets(np.array([[0, 0, 0]]))
        arrow_vec.set_segments(np.array([[[0, 0, 0], [0, 0, 0]]]))
        text_ang.set_text("")
        for txt in textos_angulo_slider:
            txt.set_text("0.0°")
        return (polar_lines + polar_points + polar_texts + lineas_3d +
                [punto_final, proj_xy, proj_xz, proj_yz, arrow_vec, text_ang] +
                textos_angulo_slider)

    actualizar_interfaz_modos()

    ani = animation.FuncAnimation(fig, actualizar_grafica, init_func=init,
                                  interval=30, blit=True, cache_frame_data=False)

    plt.show()

    # Al cerrar la figura
    global corriendo
    corriendo = False
    if ser and ser.is_open:
        ser.close()
    print("Programa terminado.")

# ==================================================
# PUNTO DE ENTRADA
# ==================================================
if __name__ == "__main__":
    # Mostrar ventana de configuración
    ventana_configuracion()
    # Si se seleccionó un puerto, ejecutar la interfaz
    if PUERTO:
        ejecutar_interfaz()
    else:
        print("No se seleccionó puerto. Saliendo.")
