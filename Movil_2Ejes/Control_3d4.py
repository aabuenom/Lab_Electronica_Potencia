# =====================================================================
# Control_3d1.py - Interfaz gráfica para control y visualización del pán-tilt
#                  con gráfico 3D mejorado (dos eslabones articulados)
#                  + Vector verde desde origen hasta extremo
#                  + Refresco más rápido (intervalo 20 ms)
#                  + AÑADIDO: Botón "Remoto" para activar modo IR (KY-022)
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

# ===== CONFIGURACIÓN DEL PUERTO SERIE =====
PUERTO = '/dev/ttyUSB0'        # En Windows usar 'COMx', en Linux /dev/ttyUSB0
BAUDRATE = 9600
TIMEOUT = 0.1
MAX_PUNTOS = 100

# ===== VARIABLES GLOBALES =====
ser = None
tiempos = []
ang_rot = []
ang_inc = []
ang_rot_actual = 90.0
ang_inc_actual = 90.0
corriendo = True
modo_actual = 'T'
lock = threading.Lock()

# ===== FUNCIONES DE COMUNICACIÓN SERIE =====
def conectar_serial():
    global ser
    try:
        ser = serial.Serial(PUERTO, BAUDRATE, timeout=TIMEOUT)
        print(f"Conectado a {PUERTO}")
        return True
    except Exception as e:
        print(f"Error al conectar: {e}")
        return False

def enviar_comando(cmd):
    if ser and ser.is_open:
        ser.write((cmd + '\n').encode())

def enviar_angulos(rot, inc):
    if modo_actual == 'T':
        cmd = f"{rot:.1f},{inc:.1f}"
        enviar_comando(cmd)

def leer_datos():
    global ang_rot_actual, ang_inc_actual
    if ser and ser.is_open:
        try:
            line = ser.readline().decode().strip()
            if line:
                partes = line.split(',')
                if len(partes) == 2:
                    try:
                        r = float(partes[0])
                        i = float(partes[1])
                        with lock:
                            ang_rot_actual = r
                            ang_inc_actual = i
                            tiempos.append(time.time())
                            ang_rot.append(r)
                            ang_inc.append(i)
                            if len(tiempos) > MAX_PUNTOS:
                                tiempos.pop(0)
                                ang_rot.pop(0)
                                ang_inc.pop(0)
                    except ValueError:
                        pass
        except:
            pass

def hilo_lectura():
    while corriendo:
        leer_datos()
        time.sleep(0.005)  # <-- REDUCIDO para lectura más rápida (200 Hz)

# ==================================================
# 1. CONFIGURACIÓN DE LA FIGURA Y GRÁFICOS
# ==================================================
fig = plt.figure(figsize=(14, 10))
fig.subplots_adjust(left=0.08, bottom=0.22, right=0.92, top=0.92)

gs = gridspec.GridSpec(3, 2, height_ratios=[1, 1, 1], width_ratios=[1, 1])

# --- Cuadrante superior: evolución temporal ---
ax1 = fig.add_subplot(gs[0, :])
ax1.set_title("Evolución de ángulos", fontsize=12)
ax1.set_xlabel("Tiempo (s)")
ax1.set_ylabel("Ángulo (°)")
ax1.set_ylim(-10, 190)
ax1.grid(True)
linea_rot, = ax1.plot([], [], 'r-', label='Rotación')
linea_inc, = ax1.plot([], [], 'b-', label='Inclinación')
ax1.legend(loc='upper right')

# --- Cuadrante inferior izquierdo: polares ---
ax2 = fig.add_subplot(gs[1, 0], projection='polar')
ax2.set_theta_zero_location('E')
ax2.set_theta_direction(1)
ax2.set_ylim(0, 1)
ax2.set_yticks([])
ax2.grid(True, linestyle='--', alpha=0.5)
linea_polar_rot, = ax2.plot([], [], 'r-', linewidth=3, label='Rotación')
punto_polar_rot, = ax2.plot([], [], 'ro', markersize=8)
ax2.legend(loc='lower center', bbox_to_anchor=(0.5, -0.15))

ax3 = fig.add_subplot(gs[2, 0], projection='polar')
ax3.set_theta_zero_location('E')
ax3.set_theta_direction(1)
ax3.set_ylim(0, 1)
ax3.set_yticks([])
ax3.grid(True, linestyle='--', alpha=0.5)
linea_polar_inc, = ax3.plot([], [], 'b-', linewidth=3, label='Inclinación')
punto_polar_inc, = ax3.plot([], [], 'bo', markersize=8)
ax3.legend(loc='lower center', bbox_to_anchor=(0.5, -0.15))

# --- Cuadrante inferior derecho: GRÁFICO 3D MEJORADO (DOS ESLABONES) ---
ax4 = fig.add_subplot(gs[1:, 1], projection='3d')
ax4.set_xlabel('X', fontsize=10)
ax4.set_ylabel('Y', fontsize=10)
ax4.set_zlabel('Z', fontsize=10)

# Límites y marcas
ax4.set_xlim(-1.2, 2.2)
ax4.set_ylim(-1.2, 2.2)
ax4.set_zlim(-1.2, 1.2)
ax4.set_xticks([-1, 0, 1, 2])
ax4.set_yticks([-1, 0, 1, 2])
ax4.set_zticks([-1, 0, 1])

# Vista inicial
ax4.view_init(elev=20, azim=-30)

# Ejes de referencia
ax4.quiver(0, 0, 0, 1.2, 0, 0, color='gray', alpha=0.6, arrow_length_ratio=0.1, linewidth=2)
ax4.quiver(0, 0, 0, 0, 1.2, 0, color='gray', alpha=0.6, arrow_length_ratio=0.1, linewidth=2)
ax4.quiver(0, 0, 0, 0, 0, 1.2, color='gray', alpha=0.6, arrow_length_ratio=0.1, linewidth=2)

# Círculos de referencia
theta = np.linspace(0, 2*np.pi, 100)
x_circ = np.cos(theta)
y_circ = np.sin(theta)
z_circ = np.zeros_like(theta)
ax4.plot(x_circ, y_circ, z_circ, color='lightgray', linestyle='--', linewidth=1, alpha=0.5)
x_circ2 = np.cos(theta)
z_circ2 = np.sin(theta)
y_circ2 = np.zeros_like(theta)
ax4.plot(x_circ2, y_circ2, z_circ2, color='lightgray', linestyle='--', linewidth=1, alpha=0.5)

# Esfera semitransparente (opcional)
u = np.linspace(0, 2 * np.pi, 30)
v = np.linspace(0, np.pi, 30)
x_esp = np.outer(np.cos(u), np.sin(v))
y_esp = np.outer(np.sin(u), np.sin(v))
z_esp = np.outer(np.ones(np.size(u)), np.cos(v))
ax4.plot_surface(x_esp, y_esp, z_esp, color='lightblue', alpha=0.15, rstride=1, cstride=1, edgecolor='none')

# === OBJETOS GRÁFICOS 3D ===
linea_azul, = ax4.plot([], [], [], 'b-', linewidth=4, label='Eslabón 1')
linea_roja, = ax4.plot([], [], [], 'r-', linewidth=4, label='Eslabón 2')
punto_final, = ax4.plot([], [], [], 'ko', markersize=10, markeredgecolor='darkred', markeredgewidth=1, label='Extremo')
origen_point, = ax4.plot([0], [0], [0], 'ko', markersize=8)

proj_xy_line, = ax4.plot([], [], [], 'gray', linestyle='--', linewidth=1.5, alpha=0.7)
proj_xz_line, = ax4.plot([], [], [], 'gray', linestyle='--', linewidth=1.5, alpha=0.5)
proj_yz_line, = ax4.plot([], [], [], 'gray', linestyle='--', linewidth=1.5, alpha=0.5)

text_ang = ax4.text2D(0.95, 0.95, "", transform=ax4.transAxes, ha='right', va='top', fontsize=10,
                      bbox=dict(boxstyle="round,pad=0.3", facecolor='white', alpha=0.7))

# Vector verde con flecha (más visible)
arrow_vec = ax4.quiver([0], [0], [0], [0], [0], [0],
                       color='green', arrow_length_ratio=0.2, linewidth=2,
                       label='Vector posición', zorder=10, pivot='tail')

ax4.legend(loc='upper left')

# ==================================================
# 2. SLIDERS Y BOTONES
# ==================================================
ax_rot_slider = plt.axes([0.15, 0.08, 0.30, 0.03])
ax_inc_slider = plt.axes([0.15, 0.03, 0.30, 0.03])
slider_rot = Slider(ax_rot_slider, 'Rotación', 0, 180, valinit=90, valstep=1)
slider_inc = Slider(ax_inc_slider, 'Inclinación', 21, 180, valinit=90, valstep=1)

ax_boton_enviar = plt.axes([0.50, 0.05, 0.08, 0.04])
boton_enviar = Button(ax_boton_enviar, 'Enviar')

ax_boton_barrido = plt.axes([0.60, 0.05, 0.08, 0.04])
boton_barrido = Button(ax_boton_barrido, 'Barrido')

# Botones de modo: Teclado, Joystick y Remoto
ax_boton_teclado = plt.axes([0.75, 0.08, 0.10, 0.05])
boton_teclado = Button(ax_boton_teclado, 'Teclado', color='lightgreen', hovercolor='green')

ax_boton_joystick = plt.axes([0.87, 0.08, 0.10, 0.05])
boton_joystick = Button(ax_boton_joystick, 'Joystick', color='lightcoral', hovercolor='red')

# NUEVO: Botón para modo Remoto (IR)
ax_boton_remoto = plt.axes([0.75, 0.02, 0.10, 0.05])   # debajo de Teclado
boton_remoto = Button(ax_boton_remoto, 'Remoto', color='gold', hovercolor='orange')

# ==================================================
# 3. FUNCIONES DE CONTROL
# ==================================================
def actualizar_controles(modo):
    global modo_actual
    modo_actual = modo
    if modo == 'T':
        slider_rot.set_active(True)
        slider_inc.set_active(True)
        boton_enviar.ax.set_visible(True)
        boton_barrido.ax.set_visible(True)
        boton_teclado.color = 'lightgreen'
        boton_joystick.color = 'lightcoral'
        boton_remoto.color = 'gold'
        enviar_comando('T')
        print("Modo: Teclado (Terminal)")
    elif modo == 'J':
        slider_rot.set_active(False)
        slider_inc.set_active(False)
        boton_enviar.ax.set_visible(False)
        boton_barrido.ax.set_visible(False)
        boton_teclado.color = 'lightgray'
        boton_joystick.color = 'lightgreen'
        boton_remoto.color = 'gold'
        enviar_comando('J')
        print("Modo: Joystick")
    else:  # modo 'R'
        slider_rot.set_active(False)
        slider_inc.set_active(False)
        boton_enviar.ax.set_visible(False)
        boton_barrido.ax.set_visible(False)
        boton_teclado.color = 'lightgray'
        boton_joystick.color = 'lightcoral'
        boton_remoto.color = 'lightgreen'
        enviar_comando('R')
        print("Modo: Remoto IR (usando mando)")

# Asignar eventos a los botones
boton_teclado.on_clicked(lambda event: actualizar_controles('T'))
boton_joystick.on_clicked(lambda event: actualizar_controles('J'))
boton_remoto.on_clicked(lambda event: actualizar_controles('R'))

def al_presionar_enviar(event):
    rot = slider_rot.val
    inc = slider_inc.val
    if inc < 21: inc = 21
    enviar_angulos(rot, inc)
    print(f"Enviado: Rot={rot:.1f}, Inc={inc:.1f}")

def al_presionar_barrido(event):
    def barrido():
        for ang in range(0, 181, 5):
            enviar_angulos(ang, 90.0)
            time.sleep(0.08)
        for ang in range(21, 181, 5):
            enviar_angulos(90.0, ang)
            time.sleep(0.08)
        print("Barrido completado")
    threading.Thread(target=barrido, daemon=True).start()

boton_enviar.on_clicked(al_presionar_enviar)
boton_barrido.on_clicked(al_presionar_barrido)

# ==================================================
# 4. TECLADO
# ==================================================
def on_key(event):
    if modo_actual != 'T':
        return
    inc = 5
    if event.key == 'left':
        nueva = slider_rot.val - inc
        if nueva < 0: nueva = 0
        slider_rot.set_val(nueva)
        enviar_angulos(nueva, slider_inc.val)
    elif event.key == 'right':
        nueva = slider_rot.val + inc
        if nueva > 180: nueva = 180
        slider_rot.set_val(nueva)
        enviar_angulos(nueva, slider_inc.val)
    elif event.key == 'down':
        nueva = slider_inc.val - inc
        if nueva < 21: nueva = 21
        slider_inc.set_val(nueva)
        enviar_angulos(slider_rot.val, nueva)
    elif event.key == 'up':
        nueva = slider_inc.val + inc
        if nueva > 180: nueva = 180
        slider_inc.set_val(nueva)
        enviar_angulos(slider_rot.val, nueva)
    elif event.key == 'r' or event.key == 'R':
        slider_rot.set_val(90)
        slider_inc.set_val(90)
        enviar_angulos(90, 90)
        print("Reset a 90°")

fig.canvas.mpl_connect('key_press_event', on_key)

# ==================================================
# 5. ANIMACIÓN
# ==================================================
def actualizar_grafica(frame):
    with lock:
        # Evolución temporal
        if tiempos:
            t_vals = [t - tiempos[0] for t in tiempos]
            linea_rot.set_data(t_vals, ang_rot)
            linea_inc.set_data(t_vals, ang_inc)
            ax1.relim()
            ax1.autoscale_view()
        else:
            linea_rot.set_data([], [])
            linea_inc.set_data([], [])

        # Polares
        rot_rad = np.radians(ang_rot_actual)
        inc_rad = np.radians(ang_inc_actual)
        linea_polar_rot.set_data([rot_rad, rot_rad], [0, 1])
        punto_polar_rot.set_data([rot_rad], [1])

        inc_rad_polar = np.radians(ang_inc_actual)
        linea_polar_inc.set_data([inc_rad_polar, inc_rad_polar], [0, 1])
        punto_polar_inc.set_data([inc_rad_polar], [1])

        # ---- GRÁFICO 3D: DOS ESLABONES ----
        x1 = np.cos(rot_rad)
        y1 = np.sin(rot_rad)
        z1 = 0.0

        x2 = x1 + np.cos(inc_rad) * np.cos(rot_rad)
        y2 = y1 + np.cos(inc_rad) * np.sin(rot_rad)
        z2 = np.sin(inc_rad)

        linea_azul.set_data([0, x1], [0, y1])
        linea_azul.set_3d_properties([0, z1])

        linea_roja.set_data([x1, x2], [y1, y2])
        linea_roja.set_3d_properties([z1, z2])

        punto_final.set_data([x2], [y2])
        punto_final.set_3d_properties([z2])

        proj_xy_line.set_data([0, x2], [0, y2])
        proj_xy_line.set_3d_properties([0, 0])

        proj_xz_line.set_data([0, x2], [0, 0])
        proj_xz_line.set_3d_properties([0, z2])

        proj_yz_line.set_data([0, 0], [0, y2])
        proj_yz_line.set_3d_properties([0, z2])

        # Actualizar vector verde
        arrow_vec.set_offsets(np.array([[0, 0, 0]]))
        arrow_vec.set_segments(np.array([[[0, 0, 0], [x2, y2, z2]]]))

        text_ang.set_text(f"Rot: {ang_rot_actual:.1f}°\nInc: {ang_inc_actual:.1f}°")

        if modo_actual == 'T':
            slider_rot.set_val(ang_rot_actual)
            slider_inc.set_val(ang_inc_actual)

    return (linea_rot, linea_inc,
            linea_polar_rot, punto_polar_rot,
            linea_polar_inc, punto_polar_inc,
            linea_azul, linea_roja, punto_final,
            proj_xy_line, proj_xz_line, proj_yz_line,
            arrow_vec,
            text_ang)

def init():
    linea_rot.set_data([], [])
    linea_inc.set_data([], [])
    linea_polar_rot.set_data([], [])
    punto_polar_rot.set_data([], [])
    linea_polar_inc.set_data([], [])
    punto_polar_inc.set_data([], [])
    linea_azul.set_data([], [])
    linea_azul.set_3d_properties([])
    linea_roja.set_data([], [])
    linea_roja.set_3d_properties([])
    punto_final.set_data([], [])
    punto_final.set_3d_properties([])
    proj_xy_line.set_data([], [])
    proj_xy_line.set_3d_properties([])
    proj_xz_line.set_data([], [])
    proj_xz_line.set_3d_properties([])
    proj_yz_line.set_data([], [])
    proj_yz_line.set_3d_properties([])
    arrow_vec.set_offsets(np.array([[0, 0, 0]]))
    arrow_vec.set_segments(np.array([[[0, 0, 0], [0, 0, 0]]]))
    text_ang.set_text("")
    return (linea_rot, linea_inc,
            linea_polar_rot, punto_polar_rot,
            linea_polar_inc, punto_polar_inc,
            linea_azul, linea_roja, punto_final,
            proj_xy_line, proj_xz_line, proj_yz_line,
            arrow_vec,
            text_ang)

# ==================================================
# 6. PROGRAMA PRINCIPAL
# ==================================================
if __name__ == "__main__":
    if not conectar_serial():
        print("No se pudo conectar. Saliendo.")
        exit()

    hilo = threading.Thread(target=hilo_lectura, daemon=True)
    hilo.start()

    # Iniciamos en modo Teclado (T) por defecto, pero el Arduino ya está en 'R'
    # Para sincronizar, enviamos 'T' al inicio para que coincida con la interfaz
    # O bien, podemos poner modo_actual = 'R' y actualizar controles.
    # Voy a poner modo inicial 'R' para que coincida con el Arduino.
    actualizar_controles('R')   # <--- Cambiado para que arranque en Remoto

    # Refresco más rápido: intervalo de 20 ms (50 Hz)
    ani = animation.FuncAnimation(fig, actualizar_grafica, init_func=init,
                                  interval=20, blit=False, cache_frame_data=False)

    plt.show()

    corriendo = False
    if ser and ser.is_open:
        ser.close()
    print("Programa terminado.")
