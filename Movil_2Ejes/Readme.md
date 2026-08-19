# Control de un Brazo con Dos (2) Grados de Libertad

En la infografía se puede ver la cinematica del sistema a controlar

![Cinemática](/home/alex/Arduino/Movil2Ejes/infografia.png  "Cinemática del Brazo")
## Maqueta

La maqueta esta compuesta por dos servo motores SG90 Controlados de tres formas diferentes:

1. Teclado
2. Joytick
3. Control Remoto Infrarojo

El Servo 1 maneja la rotación de la base, mientras que el servo 2 maneja el grado de inclinación

## Componentes de la Maqueta
1. Dos (2) Servos MG90 de 0 a 180°
2. Modulo  PCA9685
3. IR (KY-022)
4. Dos (2) JOYSTICK
5. Control Remoto

## Software Desarrolado

Los programas estan desarrolados considerando que el servo de la base esta al canal 0 y el servo de la articulación esta en el canal 1.

**Nota: El Servo del brazo se restrige el movimiento a 21° como mínimo para que no choque con el otro servo.**

### **Arduino**

#### calibracion.ino

Permite calibrar el recorrido de ambos servo motores utilizando el modulo PCA9685, controlado por teclado ambos servos.

#### Movil_SG90.ino
Permite el movimiento del brazo desde el teclado o el joystick, asume que los servo motores estan directos a las salidas 9 y 10 y alimentados desde el arduino

#### Movil_SG90_v2.ino
Permite el movimiento del brazo desde el teclado o el joystick usando el modulo PCA9685 con el servo de la base en el canal 0 y el servo del brazo en el canal 1

#### Remoto.ino
Permite la calibración del HEX de cada boton del control Remoto a utilizar, para este caso el mapeo del control es el siguiente:

- Boton_1, 	0xF30CFF00
- Boton_2, 	0xE718FF00
- Boton_3,	0xA15EFF00
- Boton_4,	0xF708FF00
- Boton_5,	0xE31CFF00
- Boton_6,	0xA55AFF00
- Boton_7,	0xBD42FF00
- Boton_8,	0xAD52FF00
- Boton_9,	0xB54AFF00
- Boton_0,	0xE916FF00
- Boton_100+,	0xE619FF00
- Boton_200+,	0xF20DFF00
- Boton_-,	0xF807FF00
- Boton_+,	0xEA15FF00
- Boton_EQ,	0xF609FF00
- Boton_<,	0xBB44FF00
- Boton_>,	0xBF40FF00
- Boton_>|,	0xBC43FF00
- Boton_CH-,	0xBA45FF00
- Boton_CH,	0xB946FF00
- Boton_CH+,	0xB847FF00


#### Control_inT.ino
Integra el control  del brazo usando el modulo PCA9685 con el servo de la base en el canal 0 y el servo del brazo en el canal 1. Tiene tres esquemas de control desde el teclado, joystick o Control Remoto. 

### Python

Se desarrollaron interfaz gráficas para monitorear el movimiento del brazo con Python 

#### Control_3d4.py
se usa en conjunto con **Control_inT.ino** permite monitorear el movimiento desde una interfaz grafica que se puede manejar para los tres modos de control. En el modo teclado utiliza las flechas de cursores para controlar el movimiento. Este programa supone que el arduino esta conectado al puerto /dev/ttyUSB0.

### Control_3d5.py
Es igual que el anterior pero tiene una interfaz para escoger el puerto de comunicación con el arduino.
 
En la figura se presenta la interfaz de conexion al puerto de comunicación con el arduino

![Puerto de Conexón](/home/alex/Arduino/Movil2Ejes/Puerto.png  "Puerto de Conexión")

En la figura se presenta la interfaz de control en python

![Interfaz de Control](/home/alex/Arduino/Movil2Ejes/Interfaz.png  "Interfaz de Control")