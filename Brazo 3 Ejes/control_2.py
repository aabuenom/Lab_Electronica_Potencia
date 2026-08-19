# =====================================================================
# control_brazo.py - Interfaz gráfica para brazo robótico de 4 servos
#                   con control individual por servo (auto/manual).
# =====================================================================

import serial
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.widgets import Slider, Button
import matplotlib.gridspec as gridspec
import numpy as np
import threading
import time
from mpl_toolkits.mplot3d import Axes3D

# ===== CONFIGURACIÓN =====
PUERTO = '/dev/ttyUSB0'        # Ajusta según tu sistema (Windows: 'COMx')
BAUDRATE = 115200
TIMEOUT = 0.1
MAX_PUNTOS = 100
STEP = 5

# ---- OFFSET para el modelo 3D (grados) ----
OFFSET = 90.0

# ===== VARIABLES GLOBALES =====
ser = None
tiempos = []
angulos = [[], [], [], []]
ang_actual = [90.0, 90.0, 90.0, 90.0]
corriendo = True
modos_servo = [False, False, False, False]  # False=auto, True=manual
lock = threading.Lock()

# ===== FUNCIONES SERIE =====
def conectar_serial():
    global ser
    try:
        ser = serial.Serial(PUERTO, BAUDRATE, timeout=TIMEOUT)
        print(f"Conectado a {PUERTO}")
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False

def enviar_comando(cmd):
    if ser and ser.is_open:
        ser.write((cmd + '\n').encode())

def enviar_angulos(a0, a1, a2, a3):
    cmd = f"S:{a0:.1f},{a1:.1f},{a2:.1f},{a3:.1f}"
    enviar_comando(cmd)

def enviar_tecla(tecla):
    enviar_comando(tecla)

def enviar_modo_servo(idx, modo):
    """modo: 0=auto, 1=manual"""
    enviar_comando(f"C:{idx},{modo}")

def toggle_modo_global():
    enviar_comando('m')

def leer_datos():
    global ang_actual
    if ser and ser.is_open:
        try:
            line = ser.readline().decode().strip()
            if line.startswith('A:'):
                partes = line[2:].split(',')
                if len(partes) == 4:
                    try:
                        vals = [float(p) for p in partes]
                        with lock:
                            ang_actual = vals
                            tiempos.append(time.time())
                            for i in range(4):
                                angulos[i].append(vals[i])
                                if len(angulos[i]) > MAX_PUNTOS:
                                    angulos[i].pop(0)
                            if len(tiempos) > MAX_PUNTOS:
                                tiempos.pop(0)
                    except ValueError:
                        pass
        except:
            pass

def hilo_lectura():
    while corriendo:
        leer_datos()
        time.sleep(0.005)

# ==================================================
# 1. CONFIGURACIÓN DE LA FIGURA
# ==================================================
fig = plt.figure(figsize=(16, 10))
fig.subplots_adjust(left=0.05, bottom=0.22, right=0.95, top=0.93)

gs = gridspec.GridSpec(3, 3, height_ratios=[1.2, 1, 1], width_ratios=[1, 1, 1])

# ---- Evolución temporal (arriba) ----
ax1 = fig.add_subplot(gs[0, :])
ax1.set_title("Evolución de los 4 ángulos")
ax1.set_xlabel("Tiempo (s)")
ax1.set_ylabel("Ángulo (°)")
ax1.set_ylim(-10, 190)
ax1.grid(True)
colores = ['red', 'blue', 'green', 'orange']
nombres = ['Art1', 'Art2', 'Art3', 'Garra']
lineas = []
for i in range(4):
    l, = ax1.plot([], [], color=colores[i], label=nombres[i])
    lineas.append(l)
ax1.legend(loc='upper right')

# ---- 4 gráficos polares (2x2) ----
axes_polar = []
polar_lines = []
polar_points = []
for row in range(2):
    for col in range(2):
        idx = row*2 + col
        ax = fig.add_subplot(gs[1+row, col], projection='polar')
        ax.set_theta_zero_location('E')
        ax.set_theta_direction(1)
        ax.set_ylim(0, 1)
        ax.set_yticks([])
        ax.set_title(nombres[idx], fontsize=10)
        ax.grid(True, linestyle='--', alpha=0.5)
        line, = ax.plot([], [], color=colores[idx], linewidth=3)
        point, = ax.plot([], [], 'o', color=colores[idx], markersize=8)
        axes_polar.append(ax)
        polar_lines.append(line)
        polar_points.append(point)

# ---- Gráfico 3D ----
ax4 = fig.add_subplot(gs[1:, 2], projection='3d')
ax4.set_xlabel('X')
ax4.set_ylabel('Y')
ax4.set_zlabel('Z')
ax4.set_xlim(-1.5, 1.5)
ax4.set_ylim(-1.5, 1.5)
ax4.set_zlim(-0.5, 2.0)
ax4.view_init(elev=25, azim=-45)
# Ejes de referencia
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
text_ang = ax4.text2D(0.95, 0.95, "", transform=ax4.transAxes, ha='right', va='top',
                      fontsize=10, bbox=dict(boxstyle="round", facecolor='white', alpha=0.7))

# ==================================================
# 2. CONTROLES (sliders + botones de modo individual)
# ==================================================
sliders = []
botones_modo = []
botones_step = []

def actualizar_interfaz_modos():
    for i, (b, s) in enumerate(zip(botones_modo, sliders)):
        if modos_servo[i]:  # manual
            b.label.set_text('M')
            b.color = 'lightgreen'
            s.set_active(True)
        else:               # auto
            b.label.set_text('A')
            b.color = 'lightgray'
            s.set_active(False)
    fig.canvas.draw_idle()

def toggle_modo_servo(idx):
    nuevo_modo = 0 if modos_servo[idx] else 1
    modos_servo[idx] = (nuevo_modo == 1)
    enviar_modo_servo(idx, nuevo_modo)
    actualizar_interfaz_modos()

# ---- Fila 1: Art1 y Art2 (y = 0.16) ----
y_row1 = 0.16
# Art1
ax_s1 = plt.axes([0.08, y_row1, 0.14, 0.025])
s1 = Slider(ax_s1, 'Art1', 22, 180, valinit=90, valstep=1)
sliders.append(s1)
ax_b1 = plt.axes([0.23, y_row1, 0.04, 0.025])
b1 = Button(ax_b1, 'A', color='lightgray')
b1.on_clicked(lambda event, idx=0: toggle_modo_servo(idx))
botones_modo.append(b1)
ax_s1_dec = plt.axes([0.28, y_row1, 0.03, 0.025])
b_s1_dec = Button(ax_s1_dec, '-', color='lightcoral')
ax_s1_inc = plt.axes([0.32, y_row1, 0.03, 0.025])
b_s1_inc = Button(ax_s1_inc, '+', color='lightblue')
botones_step.append((b_s1_dec, b_s1_inc))

# Art2
ax_s2 = plt.axes([0.40, y_row1, 0.14, 0.025])
s2 = Slider(ax_s2, 'Art2', 22, 180, valinit=90, valstep=1)
sliders.append(s2)
ax_b2 = plt.axes([0.55, y_row1, 0.04, 0.025])
b2 = Button(ax_b2, 'A', color='lightgray')
b2.on_clicked(lambda event, idx=1: toggle_modo_servo(idx))
botones_modo.append(b2)
ax_s2_dec = plt.axes([0.60, y_row1, 0.03, 0.025])
b_s2_dec = Button(ax_s2_dec, '-', color='lightcoral')
ax_s2_inc = plt.axes([0.64, y_row1, 0.03, 0.025])
b_s2_inc = Button(ax_s2_inc, '+', color='lightblue')
botones_step.append((b_s2_dec, b_s2_inc))

# ---- Fila 2: Art3 y Garra (y = 0.09) ----
y_row2 = 0.09
# Art3
ax_s3 = plt.axes([0.08, y_row2, 0.14, 0.025])
s3 = Slider(ax_s3, 'Art3', 22, 180, valinit=90, valstep=1)
sliders.append(s3)
ax_b3 = plt.axes([0.23, y_row2, 0.04, 0.025])
b3 = Button(ax_b3, 'A', color='lightgray')
b3.on_clicked(lambda event, idx=2: toggle_modo_servo(idx))
botones_modo.append(b3)
ax_s3_dec = plt.axes([0.28, y_row2, 0.03, 0.025])
b_s3_dec = Button(ax_s3_dec, '-', color='lightcoral')
ax_s3_inc = plt.axes([0.32, y_row2, 0.03, 0.025])
b_s3_inc = Button(ax_s3_inc, '+', color='lightblue')
botones_step.append((b_s3_dec, b_s3_inc))

# Garra
ax_s4 = plt.axes([0.40, y_row2, 0.14, 0.025])
s4 = Slider(ax_s4, 'Garra', 22, 180, valinit=90, valstep=1)
sliders.append(s4)
ax_b4 = plt.axes([0.55, y_row2, 0.04, 0.025])
b4 = Button(ax_b4, 'A', color='lightgray')
b4.on_clicked(lambda event, idx=3: toggle_modo_servo(idx))
botones_modo.append(b4)
ax_s4_dec = plt.axes([0.60, y_row2, 0.03, 0.025])
b_s4_dec = Button(ax_s4_dec, '-', color='lightcoral')
ax_s4_inc = plt.axes([0.64, y_row2, 0.03, 0.025])
b_s4_inc = Button(ax_s4_inc, '+', color='lightblue')
botones_step.append((b_s4_dec, b_s4_inc))

# ---- Botones principales (fila inferior) ----
y_btns = 0.03
ax_boton_modo = plt.axes([0.08, y_btns, 0.12, 0.035])
boton_modo = Button(ax_boton_modo, 'Modo: Global Auto', color='lightcoral')

def actualizar_modo_global():
    # Invertir todos los modos locales
    for i in range(4):
        modos_servo[i] = not modos_servo[i]
    toggle_modo_global()
    # Actualizar etiqueta del botón global
    if all(modos_servo):
        boton_modo.label.set_text('Modo: Global Manual')
        boton_modo.color = 'lightgreen'
    else:
        boton_modo.label.set_text('Modo: Global Auto')
        boton_modo.color = 'lightcoral'
    actualizar_interfaz_modos()

boton_modo.on_clicked(lambda event: actualizar_modo_global())

# Enviar, Barrido, Reset
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
    nuevo = max(22, min(180, nuevo))
    sliders[idx].set_val(nuevo)
    enviar_desde_sliders()

for i, (b_dec, b_inc) in enumerate(botones_step):
    b_dec.on_clicked(lambda event, idx=i: step_angle(idx, -STEP))
    b_inc.on_clicked(lambda event, idx=i: step_angle(idx, STEP))

def barrido():
    def ejecutar():
        for ang in range(22, 181, STEP):
            enviar_angulos(ang, 90, 90, 90)
            time.sleep(0.05)
        for ang in range(22, 181, STEP):
            enviar_angulos(90, ang, 90, 90)
            time.sleep(0.05)
        for ang in range(22, 181, STEP):
            enviar_angulos(90, 90, ang, 90)
            time.sleep(0.05)
        for ang in range(22, 181, STEP):
            enviar_angulos(90, 90, 90, ang)
            time.sleep(0.05)
        print("Barrido completado")
    threading.Thread(target=ejecutar, daemon=True).start()

boton_barrido.on_clicked(lambda event: barrido())

# ==================================================
# 3. TECLADO
# ==================================================
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

# ==================================================
# 4. ANIMACIÓN
# ==================================================
def actualizar_grafica(frame):
    with lock:
        if tiempos:
            t0 = tiempos[0]
            t_vals = [t - t0 for t in tiempos]
            for i, line in enumerate(lineas):
                line.set_data(t_vals, angulos[i])
            ax1.relim()
            ax1.autoscale_view()
        else:
            for line in lineas:
                line.set_data([], [])

        for i in range(4):
            rad = np.radians(ang_actual[i])
            polar_lines[i].set_data([rad, rad], [0, 1])
            polar_points[i].set_data([rad], [1])

        # 3D
        a0 = np.radians(ang_actual[0])
        a1 = np.radians(ang_actual[1])
        a2 = np.radians(ang_actual[2]-90)
        a3 = np.radians(ang_actual[3] - OFFSET)
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
        text_ang.set_text(f"Art1: {ang_actual[0]:.1f}°\nArt2: {ang_actual[1]:.1f}°\nArt3: {ang_actual[2]:.1f}°\nGarra: {ang_actual[3]:.1f}°")

        # Sincronizar sliders en automático
        for i, s in enumerate(sliders):
            if not modos_servo[i]:  # auto
                s.set_val(ang_actual[i])

    return lineas + polar_lines + polar_points + lineas_3d + [punto_final, proj_xy, proj_xz, proj_yz, arrow_vec, text_ang]

def init():
    for line in lineas:
        line.set_data([], [])
    for line in polar_lines:
        line.set_data([], [])
    for point in polar_points:
        point.set_data([], [])
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
    return lineas + polar_lines + polar_points + lineas_3d + [punto_final, proj_xy, proj_xz, proj_yz, arrow_vec, text_ang]

# ==================================================
# 5. PROGRAMA PRINCIPAL
# ==================================================
if __name__ == "__main__":
    if not conectar_serial():
        print("No se pudo conectar. Saliendo.")
        exit()

    hilo = threading.Thread(target=hilo_lectura, daemon=True)
    hilo.start()

    actualizar_interfaz_modos()
    boton_modo.label.set_text('Modo: Global Auto')
    boton_modo.color = 'lightcoral'

    ani = animation.FuncAnimation(fig, actualizar_grafica, init_func=init,
                                  interval=20, blit=False, cache_frame_data=False)

    plt.show()

    corriendo = False
    if ser and ser.is_open:
        ser.close()
    print("Programa terminado.")
