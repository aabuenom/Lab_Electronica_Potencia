# =====================================================================
# Control_3d7.py - Ventana de conexión con Tkinter (Combobox)
#                  Ventana de control con Matplotlib.
#                  Modos: Teclado (T), Joystick (J), Remoto (R)
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
corriendo = False
modo_actual = 'T'
lock = threading.Lock()
puerto_actual = None
conectado = False

# ===== FUNCIONES DE PUERTO =====
def listar_puertos():
    puertos = serial.tools.list_ports.comports()
    return [p.device for p in puertos]

# ===== FUNCIONES DE COMUNICACIÓN SERIE =====
def conectar_serial(puerto):
    global ser, puerto_actual, conectado, corriendo
    if ser and ser.is_open:
        ser.close()
        corriendo = False
        time.sleep(0.1)
    try:
        ser = serial.Serial(puerto, BAUDRATE, timeout=TIMEOUT)
        puerto_actual = puerto
        conectado = True
        if not corriendo:
            corriendo = True
            threading.Thread(target=hilo_lectura, daemon=True).start()
        print(f"Conectado a {puerto}")
        return True
    except Exception as e:
        print(f"Error al conectar a {puerto}: {e}")
        ser = None
        puerto_actual = None
        conectado = False
        corriendo = False
        return False

def desconectar():
    global ser, conectado, corriendo
    if ser and ser.is_open:
        ser.close()
    conectado = False
    corriendo = False
    print("Desconectado")

def enviar_comando(cmd):
    if ser and ser.is_open and conectado:
        ser.write((cmd + '\n').encode())

def enviar_angulos(rot, inc):
    if modo_actual == 'T' and conectado:
        cmd = f"{rot:.1f},{inc:.1f}"
        enviar_comando(cmd)

def leer_datos():
    global ang_rot_actual, ang_inc_actual
    if ser and ser.is_open and conectado:
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
        time.sleep(0.005)

# ==================================================
# 1. VENTANA DE CONEXIÓN (Tkinter)
# ==================================================
def ventana_conexion():
    root = tk.Tk()
    root.title("Control Pán-Tilt - Conexión")
    root.geometry("400x200")
    root.resizable(False, False)

    frame = ttk.Frame(root, padding="20")
    frame.pack(fill=tk.BOTH, expand=True)

    # Etiqueta
    ttk.Label(frame, text="Selecciona el puerto:").grid(row=0, column=0, sticky=tk.W, pady=5)

    # Combobox
    puertos = listar_puertos() or ["No hay puertos"]
    combo = ttk.Combobox(frame, values=puertos, state="readonly", width=30)
    combo.grid(row=0, column=1, padx=10, pady=5)
    if puertos:
        combo.current(0)

    # Botones
    btn_actualizar = ttk.Button(frame, text="Actualizar", command=lambda: actualizar_puertos(combo))
    btn_actualizar.grid(row=1, column=0, pady=10)

    btn_conectar = ttk.Button(frame, text="Conectar", command=lambda: conectar(combo, root))
    btn_conectar.grid(row=1, column=1, pady=10)

    # Estado
    estado_label = ttk.Label(frame, text="Desconectado", foreground="red")
    estado_label.grid(row=2, column=0, columnspan=2, pady=10)

    root.mainloop()

def actualizar_puertos(combo):
    puertos = listar_puertos() or ["No hay puertos"]
    combo['values'] = puertos
    if puertos:
        combo.current(0)

def conectar(combo, root):
    puerto = combo.get()
    if puerto == "No hay puertos" or not puerto:
        return
    if conectar_serial(puerto):
        root.destroy()  # Cerrar ventana de conexión
        crear_ventana_control()  # Abrir ventana de control
    else:
        # Mostrar error en la etiqueta de estado (necesitamos actualizarla)
        # Para simplificar, usamos una variable global o buscamos el widget.
        # Obtenemos el widget de estado (último hijo de frame)
        for child in root.winfo_children():
            if isinstance(child, ttk.Frame):
                for sub in child.winfo_children():
                    if isinstance(sub, ttk.Label) and sub.cget("text") == "Desconectado":
                        sub.config(text="Error de conexión", foreground="red")
                        break

# ==================================================
# 2. VENTANA DE CONTROL (Matplotlib)
# ==================================================
def crear_ventana_control():
    global fig_control

    fig_control = plt.figure(figsize=(14, 10))
    fig_control.suptitle(f"Control Pán-Tilt - Conectado a {puerto_actual}", fontsize=14)
    fig_control.subplots_adjust(left=0.08, bottom=0.22, right=0.92, top=0.92)

    gs = gridspec.GridSpec(3, 2, height_ratios=[1, 1, 1], width_ratios=[1, 1])

    # --- Gráficos (igual que antes) ---
    ax1 = fig_control.add_subplot(gs[0, :])
    ax1.set_title("Evolución de ángulos", fontsize=12)
    ax1.set_xlabel("Tiempo (s)")
    ax1.set_ylabel("Ángulo (°)")
    ax1.set_ylim(-10, 190)
    ax1.grid(True)
    linea_rot, = ax1.plot([], [], 'r-', label='Rotación')
    linea_inc, = ax1.plot([], [], 'b-', label='Inclinación')
    ax1.legend(loc='upper right')

    ax2 = fig_control.add_subplot(gs[1, 0], projection='polar')
    ax2.set_theta_zero_location('E')
    ax2.set_theta_direction(1)
    ax2.set_ylim(0, 1)
    ax2.set_yticks([])
    ax2.grid(True, linestyle='--', alpha=0.5)
    linea_polar_rot, = ax2.plot([], [], 'r-', linewidth=3, label='Rotación')
    punto_polar_rot, = ax2.plot([], [], 'ro', markersize=8)
    ax2.legend(loc='lower center', bbox_to_anchor=(0.5, -0.15))

    ax3 = fig_control.add_subplot(gs[2, 0], projection='polar')
    ax3.set_theta_zero_location('E')
    ax3.set_theta_direction(1)
    ax3.set_ylim(0, 1)
    ax3.set_yticks([])
    ax3.grid(True, linestyle='--', alpha=0.5)
    linea_polar_inc, = ax3.plot([], [], 'b-', linewidth=3, label='Inclinación')
    punto_polar_inc, = ax3.plot([], [], 'bo', markersize=8)
    ax3.legend(loc='lower center', bbox_to_anchor=(0.5, -0.15))

    ax4 = fig_control.add_subplot(gs[1:, 1], projection='3d')
    ax4.set_xlabel('X', fontsize=10)
    ax4.set_ylabel('Y', fontsize=10)
    ax4.set_zlabel('Z', fontsize=10)
    ax4.set_xlim(-1.2, 2.2)
    ax4.set_ylim(-1.2, 2.2)
    ax4.set_zlim(-1.2, 1.2)
    ax4.set_xticks([-1, 0, 1, 2])
    ax4.set_yticks([-1, 0, 1, 2])
    ax4.set_zticks([-1, 0, 1])
    ax4.view_init(elev=20, azim=-30)

    ax4.quiver(0, 0, 0, 1.2, 0, 0, color='gray', alpha=0.6, arrow_length_ratio=0.1, linewidth=2)
    ax4.quiver(0, 0, 0, 0, 1.2, 0, color='gray', alpha=0.6, arrow_length_ratio=0.1, linewidth=2)
    ax4.quiver(0, 0, 0, 0, 0, 1.2, color='gray', alpha=0.6, arrow_length_ratio=0.1, linewidth=2)

    theta = np.linspace(0, 2*np.pi, 100)
    x_circ = np.cos(theta)
    y_circ = np.sin(theta)
    z_circ = np.zeros_like(theta)
    ax4.plot(x_circ, y_circ, z_circ, color='lightgray', linestyle='--', linewidth=1, alpha=0.5)
    x_circ2 = np.cos(theta)
    z_circ2 = np.sin(theta)
    y_circ2 = np.zeros_like(theta)
    ax4.plot(x_circ2, y_circ2, z_circ2, color='lightgray', linestyle='--', linewidth=1, alpha=0.5)

    u = np.linspace(0, 2 * np.pi, 30)
    v = np.linspace(0, np.pi, 30)
    x_esp = np.outer(np.cos(u), np.sin(v))
    y_esp = np.outer(np.sin(u), np.sin(v))
    z_esp = np.outer(np.ones(np.size(u)), np.cos(v))
    ax4.plot_surface(x_esp, y_esp, z_esp, color='lightblue', alpha=0.15, rstride=1, cstride=1, edgecolor='none')

    linea_azul, = ax4.plot([], [], [], 'b-', linewidth=4, label='Eslabón 1')
    linea_roja, = ax4.plot([], [], [], 'r-', linewidth=4, label='Eslabón 2')
    punto_final, = ax4.plot([], [], [], 'ko', markersize=10, markeredgecolor='darkred', markeredgewidth=1, label='Extremo')
    origen_point, = ax4.plot([0], [0], [0], 'ko', markersize=8)
    proj_xy_line, = ax4.plot([], [], [], 'gray', linestyle='--', linewidth=1.5, alpha=0.7)
    proj_xz_line, = ax4.plot([], [], [], 'gray', linestyle='--', linewidth=1.5, alpha=0.5)
    proj_yz_line, = ax4.plot([], [], [], 'gray', linestyle='--', linewidth=1.5, alpha=0.5)
    text_ang = ax4.text2D(0.95, 0.95, "", transform=ax4.transAxes, ha='right', va='top', fontsize=10,
                          bbox=dict(boxstyle="round,pad=0.3", facecolor='white', alpha=0.7))
    arrow_vec = ax4.quiver([0], [0], [0], [0], [0], [0],
                           color='green', arrow_length_ratio=0.2, linewidth=2,
                           label='Vector posición', zorder=10, pivot='tail')
    ax4.legend(loc='upper left')

    # ==================================================
    # CONTROLES
    # ==================================================
    ax_rot_slider = plt.axes([0.15, 0.08, 0.30, 0.03])
    ax_inc_slider = plt.axes([0.15, 0.03, 0.30, 0.03])
    slider_rot = Slider(ax_rot_slider, 'Rotación', 0, 180, valinit=90, valstep=1)
    slider_inc = Slider(ax_inc_slider, 'Inclinación', 21, 180, valinit=90, valstep=1)

    ax_boton_enviar = plt.axes([0.50, 0.05, 0.08, 0.04])
    boton_enviar = Button(ax_boton_enviar, 'Enviar')

    ax_boton_barrido = plt.axes([0.60, 0.05, 0.08, 0.04])
    boton_barrido = Button(ax_boton_barrido, 'Barrido')

    ax_boton_teclado = plt.axes([0.75, 0.08, 0.10, 0.05])
    boton_teclado = Button(ax_boton_teclado, 'Teclado', color='lightgreen', hovercolor='green')

    ax_boton_joystick = plt.axes([0.87, 0.08, 0.10, 0.05])
    boton_joystick = Button(ax_boton_joystick, 'Joystick', color='lightcoral', hovercolor='red')

    ax_boton_remoto = plt.axes([0.75, 0.02, 0.10, 0.05])
    boton_remoto = Button(ax_boton_remoto, 'Remoto', color='gold', hovercolor='orange')

    ax_boton_desconectar = plt.axes([0.50, 0.12, 0.10, 0.04])
    boton_desconectar = Button(ax_boton_desconectar, 'Desconectar', color='lightcoral', hovercolor='red')

    ax_estado_control = plt.axes([0.15, 0.13, 0.30, 0.03])
    ax_estado_control.axis('off')
    estado_texto_control = ax_estado_control.text(0.5, 0.5, f"Conectado a {puerto_actual}", ha='center', va='center', fontsize=10, color='green')

    # ==================================================
    # FUNCIONES DE CONTROL
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
        else:
            slider_rot.set_active(False)
            slider_inc.set_active(False)
            boton_enviar.ax.set_visible(False)
            boton_barrido.ax.set_visible(False)
            boton_teclado.color = 'lightgray'
            boton_joystick.color = 'lightcoral'
            boton_remoto.color = 'lightgreen'
            enviar_comando('R')
            print("Modo: Remoto IR")

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

    def desconectar_y_volver():
        desconectar()
        plt.close(fig_control)
        ventana_conexion()

    boton_desconectar.on_clicked(lambda event: desconectar_y_volver())

    # ==================================================
    # TECLADO
    # ==================================================
    def on_key(event):
        if modo_actual != 'T' or not conectado:
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

    fig_control.canvas.mpl_connect('key_press_event', on_key)

    # ==================================================
    # ANIMACIÓN
    # ==================================================
    def actualizar_grafica(frame):
        with lock:
            if tiempos:
                t_vals = [t - tiempos[0] for t in tiempos]
                linea_rot.set_data(t_vals, ang_rot)
                linea_inc.set_data(t_vals, ang_inc)
                ax1.relim()
                ax1.autoscale_view()
            else:
                linea_rot.set_data([], [])
                linea_inc.set_data([], [])

            rot_rad = np.radians(ang_rot_actual)
            inc_rad = np.radians(ang_inc_actual)

            linea_polar_rot.set_data([rot_rad, rot_rad], [0, 1])
            punto_polar_rot.set_data([rot_rad], [1])

            inc_rad_polar = np.radians(ang_inc_actual)
            linea_polar_inc.set_data([inc_rad_polar, inc_rad_polar], [0, 1])
            punto_polar_inc.set_data([inc_rad_polar], [1])

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

    ani = animation.FuncAnimation(fig_control, actualizar_grafica, init_func=init,
                                  interval=20, blit=False, cache_frame_data=False)

    plt.show()

# ==================================================
# 3. PROGRAMA PRINCIPAL
# ==================================================
if __name__ == "__main__":
    ventana_conexion()
    print("Programa terminado.")
