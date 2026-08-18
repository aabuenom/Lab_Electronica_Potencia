import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import serial
import serial.tools.list_ports
import threading
import queue
import time

class SerialController:
    """Maneja la conexión serie y la comunicación en un hilo separado."""
    def __init__(self, update_text_callback):
        self.serial_port = None
        self.connected = False
        self.read_thread = None
        self.stop_event = threading.Event()
        self.update_text = update_text_callback  # función para agregar texto a la GUI
        self.write_queue = queue.Queue()  # cola para comandos a enviar

    def connect(self, port, baudrate=9600):
        """Intenta conectar al puerto especificado."""
        if self.connected:
            self.disconnect()
        try:
            self.serial_port = serial.Serial(port, baudrate, timeout=0.1)
            self.connected = True
            self.stop_event.clear()
            # Iniciar hilo de lectura
            self.read_thread = threading.Thread(target=self._read_loop, daemon=True)
            self.read_thread.start()
            # Iniciar hilo de escritura
            self.write_thread = threading.Thread(target=self._write_loop, daemon=True)
            self.write_thread.start()
            return True
        except Exception as e:
            self.update_text(f"Error al conectar: {e}")
            return False

    def disconnect(self):
        """Cierra la conexión serie."""
        if self.connected:
            self.stop_event.set()
            if self.read_thread and self.read_thread.is_alive():
                self.read_thread.join(timeout=1)
            if self.write_thread and self.write_thread.is_alive():
                self.write_thread.join(timeout=1)
            if self.serial_port and self.serial_port.is_open:
                self.serial_port.close()
            self.connected = False
            self.serial_port = None
            self.update_text("Desconectado")

    def send_command(self, command):
        """Envía un comando a través de la cola de escritura."""
        if self.connected:
            self.write_queue.put(command + '\n')
        else:
            self.update_text("No conectado. No se puede enviar el comando.")

    def _read_loop(self):
        """Bucle de lectura en hilo separado."""
        while not self.stop_event.is_set():
            if self.serial_port and self.serial_port.is_open:
                try:
                    if self.serial_port.in_waiting > 0:
                        line = self.serial_port.readline().decode('utf-8', errors='ignore').strip()
                        if line:
                            self.update_text(f"Arduino: {line}")
                except Exception as e:
                    self.update_text(f"Error de lectura: {e}")
                    break
            time.sleep(0.01)

    def _write_loop(self):
        """Bucle de escritura desde la cola."""
        while not self.stop_event.is_set():
            try:
                command = self.write_queue.get(timeout=0.1)
                if self.serial_port and self.serial_port.is_open:
                    self.serial_port.write(command.encode())
            except queue.Empty:
                continue
            except Exception as e:
                self.update_text(f"Error al escribir: {e}")
                break


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Controlador de Generador de Onda - Arduino")
        self.root.geometry("600x500")

        # Variables de control
        self.freq_var = tk.StringVar(value="50")
        self.method_var = tk.StringVar(value="1")
        self.port_var = tk.StringVar()

        # Inicializar controlador serie con callback de actualización
        self.serial_ctrl = SerialController(self.update_text)

        # Crear interfaz
        self.create_widgets()

        # Actualizar lista de puertos al iniciar
        self.refresh_ports()

        # Manejar cierre de ventana
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def create_widgets(self):
        # Frame superior: puerto y conexión
        top_frame = ttk.LabelFrame(self.root, text="Conexión Serie", padding=5)
        top_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(top_frame, text="Puerto:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.port_combo = ttk.Combobox(top_frame, textvariable=self.port_var, state="readonly", width=20)
        self.port_combo.grid(row=0, column=1, padx=5, pady=5)
        self.port_combo.bind('<<ComboboxSelected>>', self.on_port_selected)

        self.btn_refresh = ttk.Button(top_frame, text="Actualizar puertos", command=self.refresh_ports)
        self.btn_refresh.grid(row=0, column=2, padx=5, pady=5)

        self.btn_connect = ttk.Button(top_frame, text="Conectar", command=self.toggle_connection)
        self.btn_connect.grid(row=0, column=3, padx=5, pady=5)

        # Separador
        ttk.Separator(self.root, orient='horizontal').pack(fill=tk.X, padx=10, pady=5)

        # Frame medio: configuración (frecuencia y método)
        config_frame = ttk.LabelFrame(self.root, text="Configuración", padding=10)
        config_frame.pack(fill=tk.X, padx=10, pady=5)

        # Frecuencia
        freq_frame = ttk.Frame(config_frame)
        freq_frame.pack(side=tk.LEFT, padx=10, fill=tk.X, expand=True)
        ttk.Label(freq_frame, text="Frecuencia:").pack(anchor=tk.W)
        ttk.Radiobutton(freq_frame, text="50 Hz", variable=self.freq_var, value="50").pack(anchor=tk.W)
        ttk.Radiobutton(freq_frame, text="60 Hz", variable=self.freq_var, value="60").pack(anchor=tk.W)

        # Método
        method_frame = ttk.Frame(config_frame)
        method_frame.pack(side=tk.LEFT, padx=10, fill=tk.X, expand=True)
        ttk.Label(method_frame, text="Método de disparo:").pack(anchor=tk.W)
        ttk.Radiobutton(method_frame, text="Método 1 (digitalWrite)", variable=self.method_var, value="1").pack(anchor=tk.W)
        ttk.Radiobutton(method_frame, text="Método 2 (registros)", variable=self.method_var, value="2").pack(anchor=tk.W)
        ttk.Radiobutton(method_frame, text="Método 3 (máscara)", variable=self.method_var, value="3").pack(anchor=tk.W)

        # Botón aplicar
        btn_apply = ttk.Button(config_frame, text="Aplicar configuración", command=self.apply_config)
        btn_apply.pack(side=tk.RIGHT, padx=10, pady=10)

        # Frame inferior: área de texto (logs)
        log_frame = ttk.LabelFrame(self.root, text="Mensajes del Arduino", padding=5)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.text_area = scrolledtext.ScrolledText(log_frame, height=15, state='normal')
        self.text_area.pack(fill=tk.BOTH, expand=True)
        self.text_area.config(state='disabled')

        # Botón limpiar logs
        btn_clear = ttk.Button(self.root, text="Limpiar mensajes", command=self.clear_logs)
        btn_clear.pack(pady=5)

    def refresh_ports(self):
        """Actualiza la lista de puertos disponibles."""
        ports = [port.device for port in serial.tools.list_ports.comports()]
        self.port_combo['values'] = ports
        if ports:
            self.port_combo.set(ports[0])
        else:
            self.port_combo.set('')
            self.port_var.set('')

    def on_port_selected(self, event):
        """Se activa al seleccionar un puerto."""
        pass

    def toggle_connection(self):
        """Conecta o desconecta según el estado actual."""
        if self.serial_ctrl.connected:
            self.serial_ctrl.disconnect()
            self.btn_connect.config(text="Conectar")
            self.port_combo.config(state="readonly")
            self.btn_refresh.config(state="normal")
        else:
            port = self.port_var.get()
            if not port:
                messagebox.showwarning("Puerto no seleccionado", "Por favor, seleccione un puerto.")
                return
            if self.serial_ctrl.connect(port):
                self.btn_connect.config(text="Desconectar")
                self.port_combo.config(state="disabled")
                self.btn_refresh.config(state="disabled")
                # Enviar estado actual al conectar (opcional)
                # No hay comando de consulta, pero podemos aplicar configuración actual
                self.apply_config()
            else:
                self.btn_connect.config(text="Conectar")

    def apply_config(self):
        """Envía los comandos correspondientes a la frecuencia y método seleccionados."""
        if not self.serial_ctrl.connected:
            messagebox.showwarning("No conectado", "Conéctese al Arduino primero.")
            return

        freq = self.freq_var.get()
        method = self.method_var.get()

        # Enviar comando de frecuencia
        if freq == "50":
            self.serial_ctrl.send_command("F50")
        elif freq == "60":
            self.serial_ctrl.send_command("F60")

        # Enviar comando de método
        if method == "1":
            self.serial_ctrl.send_command("M1")
        elif method == "2":
            self.serial_ctrl.send_command("M2")
        elif method == "3":
            self.serial_ctrl.send_command("M3")

        self.update_text("Configuración enviada.")

    def update_text(self, message):
        """Agrega un mensaje al área de texto (llamado desde cualquier hilo)."""
        # Se debe ejecutar en el hilo principal
        self.root.after(0, self._append_text, message)

    def _append_text(self, message):
        """Inserta texto en el área de logs."""
        self.text_area.config(state='normal')
        self.text_area.insert(tk.END, message + "\n")
        self.text_area.see(tk.END)
        self.text_area.config(state='disabled')

    def clear_logs(self):
        """Limpia el área de texto."""
        self.text_area.config(state='normal')
        self.text_area.delete(1.0, tk.END)
        self.text_area.config(state='disabled')

    def on_close(self):
        """Cierra la conexión y la ventana."""
        self.serial_ctrl.disconnect()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()