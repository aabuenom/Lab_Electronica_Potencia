"""
Interfaz gráfica para controlar el inversor trifásico Arduino.
Permite seleccionar puerto COM, metodología (SVPWM o seis pasos)
y frecuencia fundamental (Hz). Los comandos se envían por serial
a 9600 baudios.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import serial
import serial.tools.list_ports
import threading
import time

# ------------------- Clase principal de la GUI -------------------
class InversorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Controlador de Inversor Trifásico")
        self.root.geometry("500x350")
        self.root.resizable(False, False)

        # Variables de estado
        self.serial_port = None
        self.connected = False
        self.reading_thread = None
        self.running = False

        # Crear los widgets
        self.crear_widgets()

        # Actualizar la lista de puertos al inicio
        self.actualizar_puertos()

    def crear_widgets(self):
        # ----- Frame de conexión -----
        frame_conexion = ttk.LabelFrame(self.root, text="Conexión", padding=10)
        frame_conexion.pack(fill="x", padx=10, pady=5)

        ttk.Label(frame_conexion, text="Puerto:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.combo_puertos = ttk.Combobox(frame_conexion, state="readonly", width=15)
        self.combo_puertos.grid(row=0, column=1, padx=5, pady=5)

        self.btn_refrescar = ttk.Button(frame_conexion, text="Refrescar", command=self.actualizar_puertos)
        self.btn_refrescar.grid(row=0, column=2, padx=5, pady=5)

        self.btn_conectar = ttk.Button(frame_conexion, text="Conectar", command=self.toggle_conexion)
        self.btn_conectar.grid(row=0, column=3, padx=5, pady=5)

        self.estado_label = ttk.Label(frame_conexion, text="Estado: Desconectado", foreground="red")
        self.estado_label.grid(row=0, column=4, padx=10, pady=5)

        # ----- Frame de configuración (metodología y frecuencia) -----
        frame_config = ttk.LabelFrame(self.root, text="Configuración", padding=10)
        frame_config.pack(fill="x", padx=10, pady=5)

        # Metodología
        ttk.Label(frame_config, text="Metodología:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.metodo_var = tk.StringVar(value="1")
        ttk.Radiobutton(frame_config, text="SVPWM (M1)", variable=self.metodo_var, value="1").grid(row=0, column=1, padx=5, pady=5, sticky="w")
        ttk.Radiobutton(frame_config, text="Seis pasos (M2)", variable=self.metodo_var, value="2").grid(row=0, column=2, padx=5, pady=5, sticky="w")

        # Frecuencia
        ttk.Label(frame_config, text="Frecuencia (Hz):").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.frec_var = tk.StringVar(value="60")
        self.spin_frec = ttk.Spinbox(frame_config, from_=1, to=200, increment=1, textvariable=self.frec_var, width=10)
        self.spin_frec.grid(row=1, column=1, padx=5, pady=5, sticky="w")

        # Botón aplicar
        self.btn_aplicar = ttk.Button(frame_config, text="Aplicar configuración", command=self.enviar_configuracion, state="disabled")
        self.btn_aplicar.grid(row=1, column=2, padx=10, pady=5)

        # ----- Área de log / mensajes -----
        frame_log = ttk.LabelFrame(self.root, text="Mensajes del Arduino", padding=10)
        frame_log.pack(fill="both", expand=True, padx=10, pady=5)

        self.text_log = tk.Text(frame_log, height=8, state="disabled", wrap="word")
        self.text_log.pack(fill="both", expand=True)

        # Scrollbar para el log
        scroll = ttk.Scrollbar(self.text_log, orient="vertical", command=self.text_log.yview)
        scroll.pack(side="right", fill="y")
        self.text_log.configure(yscrollcommand=scroll.set)

        # ----- Configurar el cierre de la ventana -----
        self.root.protocol("WM_DELETE_WINDOW", self.cerrar_aplicacion)

    # ---------- Funciones de conexión ----------
    def actualizar_puertos(self):
        """Lista los puertos COM disponibles y los muestra en el combobox."""
        puertos = [port.device for port in serial.tools.list_ports.comports()]
        if puertos:
            self.combo_puertos['values'] = puertos
            if self.combo_puertos.get() == "":
                self.combo_puertos.current(0)
        else:
            self.combo_puertos['values'] = []
            self.combo_puertos.set("")
            if not self.connected:
                messagebox.showwarning("Sin puertos", "No se detectaron puertos COM disponibles.")

    def toggle_conexion(self):
        """Conecta o desconecta del puerto serie."""
        if not self.connected:
            self.conectar()
        else:
            self.desconectar()

    def conectar(self):
        """Intenta abrir el puerto serie."""
        puerto = self.combo_puertos.get()
        if not puerto:
            messagebox.showerror("Error", "Selecciona un puerto primero.")
            return

        try:
            self.serial_port = serial.Serial(puerto, 9600, timeout=0.1)
            # Esperar un poco para que el Arduino se reinicie si es necesario
            time.sleep(2)
            self.connected = True
            self.estado_label.config(text="Estado: Conectado", foreground="green")
            self.btn_conectar.config(text="Desconectar")
            self.btn_aplicar.config(state="normal")
            self.combo_puertos.config(state="disabled")
            self.btn_refrescar.config(state="disabled")
            self.log_message(f"Conectado a {puerto}")

            # Iniciar hilo de lectura
            self.running = True
            self.reading_thread = threading.Thread(target=self.leer_serial, daemon=True)
            self.reading_thread.start()

        except serial.SerialException as e:
            messagebox.showerror("Error de conexión", f"No se pudo conectar a {puerto}.\n{e}")
            self.connected = False
            self.estado_label.config(text="Estado: Desconectado", foreground="red")
            self.btn_conectar.config(text="Conectar")
            self.btn_aplicar.config(state="disabled")

    def desconectar(self):
        """Cierra la conexión serie."""
        self.running = False
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()
        self.connected = False
        self.estado_label.config(text="Estado: Desconectado", foreground="red")
        self.btn_conectar.config(text="Conectar")
        self.btn_aplicar.config(state="disabled")
        self.combo_puertos.config(state="readonly")
        self.btn_refrescar.config(state="normal")
        self.log_message("Desconectado")

    def leer_serial(self):
        """Hilo que lee continuamente el puerto y muestra los mensajes."""
        while self.running:
            try:
                if self.serial_port and self.serial_port.is_open:
                    if self.serial_port.in_waiting > 0:
                        linea = self.serial_port.readline().decode('utf-8', errors='ignore').strip()
                        if linea:
                            self.log_message(f"Arduino: {linea}")
                time.sleep(0.05)
            except Exception as e:
                # Si ocurre un error, lo mostramos y salimos del hilo
                self.log_message(f"Error en lectura: {e}")
                break

    # ---------- Envío de comandos ----------
    def enviar_configuracion(self):
        """Envía la metodología y la frecuencia al Arduino."""
        if not self.connected or not self.serial_port or not self.serial_port.is_open:
            messagebox.showerror("Error", "No estás conectado al Arduino.")
            return

        # Obtener valores
        metodo = self.metodo_var.get()
        frec_str = self.frec_var.get()

        # Validar frecuencia
        try:
            frec = float(frec_str)
            if frec <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Error", "La frecuencia debe ser un número positivo.")
            return

        # Construir comandos
        comando_metodo = f"M{metodo}\n"   # M1 o M2
        comando_frec = f"F{frec:.1f}\n"   # Fxx.x

        # Enviar
        try:
            self.serial_port.write(comando_metodo.encode())
            time.sleep(0.1)  # Pequeña pausa entre comandos
            self.serial_port.write(comando_frec.encode())
            self.log_message(f"Enviado: {comando_metodo.strip()} y {comando_frec.strip()}")
        except Exception as e:
            messagebox.showerror("Error al enviar", f"No se pudo enviar el comando.\n{e}")
            self.log_message(f"Error al enviar: {e}")

    # ---------- Utilidades ----------
    def log_message(self, msg):
        """Añade un mensaje al área de log (desde cualquier hilo)."""
        self.root.after(0, self._log_message, msg)

    def _log_message(self, msg):
        """Inserta el mensaje en el widget Text (seguro para hilos)."""
        self.text_log.config(state="normal")
        self.text_log.insert(tk.END, f"{msg}\n")
        self.text_log.see(tk.END)
        self.text_log.config(state="disabled")

    def cerrar_aplicacion(self):
        """Cierra la aplicación de forma ordenada."""
        self.running = False
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()
        self.root.destroy()

# ------------------- Punto de entrada -------------------
if __name__ == "__main__":
    root = tk.Tk()
    app = InversorGUI(root)
    root.mainloop()
