import tkinter as tk                                                # Interfaz gráfica principal
from tkinter import *                                               # Widgets básicos de Tkinter (Label, Button, Entry, Frame...)
from tkinter import messagebox                                      # Ventanas emergentes de aviso/alarma
import serial                                                       # Comunicación por puerto serie con Arduino Tierra
import time                                                         #Control segundos transcurridos
import math                                                         # Funciones matemáticas
from matplotlib.figure import Figure                                # Contenedor de gráficas de Matplotlib
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg 

# Configuramos el puerto serie:
device = 'COM5'
try:
    mySerial = serial.Serial(device, 9600) # Abre el puerto a 9600 baudios
except:
    mySerial = None  # Si no está conectado o está ocupado, evita que el programa colapse al empezar

# Variables para almacenar datos y tiempo real (en segundos desde Inicio)
temperaturas = []   # Vector de temperaturas 
humedad = []        # Vector de humedad (%)
medias_temp = []    # Vector de medias móviles de temperatura
eje_x = []          # Eje X para T y H (en segundos reales)
eje_x_med = []      # Eje X para las medias

# Cola circular de 10 elementos en Tierra
cola_circular_tierra = [0.0] * 10   # Buffer circular de tamaño 10 para almacenar las últimas temperaturas
indice_cola = 0                     # Posición actual donde se escribirá la siguiente lectura (del 0 al 9)
total_en_cola = 0                   # Cantidad de datos acumulados hasta ese instante 
calcular_en_satelite = False        # Si es false se calculará en Tierra, si no, en el propio satélite

# Variables para control de tiempo, reseteo y huecos de pausa
tiempo_inicio = None               # Marca de tiempo al pulsar Iniciar o recibir el primer dato             
sistema_pausado = False            # True cuando se pulsa Parar o salta una alarma
alarma_activa = False              #Evita que se abran varias ventanas de alarma seguidas
contador_medias_altas_tierra = 0   # Cuenta cuántas medias consecutivas superan el umbral de temperatura

# Datos para el radar (ángulos en radianes y distancias en cm)
angulos_radar = []      # Ángulos convertidos a radianes
distancias_radar = []   # Distancias medidas por el sensor

#FUNCIONES
def calcular_media_tierra(nueva_temp):
    #Se inserta nueva_temp en el vector y devuelve la media
    global indice_cola, total_en_cola 
    cola_circular_tierra[indice_cola] = nueva_temp  #Guarda la temperatura en el vector
    indice_cola = (indice_cola + 1) % 10            # Avanza al siguiente hueco, al llegar a la posición 9 vuelve a 0
    if total_en_cola < 10:
        total_en_cola += 1                          # Aumenta el contador hasta llenar los 10 huecos
    return sum(cola_circular_tierra[:total_en_cola]) / total_en_cola    #Devuelve la media calculada

def comprobar_alarma_temperatura(valor_media):
    global contador_medias_altas_tierra, alarma_activa
    try:
        limite = float(entrada_max_temp.get())  # Lee el umbral escrito por el usuario en la interfaz
    except:
        limite = 30.0

    if valor_media > limite:
        contador_medias_altas_tierra += 1       # Suma una media consecutiva por encima del límite
        if contador_medias_altas_tierra >= 3:   #Si se han superado las tres medias consecutivas
            activar_parada_por_alarma(f"ALARMA 3 medias consecutivas > {limite}°C")
    else:
        contador_medias_altas_tierra = 0    # Si una media baja del límite, reinicia la racha consecutiva

def activar_parada_por_alarma(mensaje_alarma):
    # Detiene la recepción por alarma dejando registrada la pausa para el hueco temporal
    global sistema_pausado, alarma_activa                       # Declaramos que vamos a modificar las variables globales de pausa y estado de alarma
    if not alarma_activa:
        alarma_activa = True                                    # Marcamos que el sistema está actualmente en estado de alarma
        sistema_pausado = True                                  # Congelamos el pintado de nuevos datos en la gráfica, pero el reloj (tiempo_inicio) sigue avanzando para crear el hueco temporal
        # Comprobamos que el puerto serie exista y esté abierto antes de intentar escribir en él
        if mySerial and mySerial.is_open:
            mySerial.write("3:2\n".encode('utf-8'))             # Enviamos el comando "3:2" con salto de línea '\n'
        tituloLabel.config(text=mensaje_alarma, fg="red")
        window.bell()                                           # Alarma sonora
        messagebox.showwarning("Alarma del Sistema", mensaje_alarma)    #Aparece una ventana de advertencia

# Leemos los datos del puerto serie y actualizamos las gráficas
def leer_datos():
    #Lee las líneas disponibles del puerto serie y actualiza gráficas o dispara alarmas.
    global tiempo_inicio
    if mySerial and mySerial.is_open:
        while mySerial.in_waiting > 0:  # Procesa todos los mensajes acumulados en el buffer de entrada
            linea = mySerial.readline().decode('utf-8', errors='ignore').rstrip()   # Lee una línea y quita saltos de línea
            if linea:
                print(f"Dades rebudes: {linea}")
                try:
                    trozos = linea.split(':')   # Separa en trozos por cada ':'
                    codigo = trozos[0]          # El primer elemento indica el tipo de mensaje

                    # CÓDIGO 1: Temperatura y Humedad -> "1:temp:hum"
                    if codigo == '1' and len(trozos) >= 3 and not sistema_pausado:
                        if tiempo_inicio is None:
                            tiempo_inicio = time.time()     # Inicia el cronómetro si aún no había empezado
                        t_actual = round(time.time() - tiempo_inicio, 1)    # Segundos transcurridos

                        temp_valor = float(trozos[1]) #Extraemos los datos de temperatura
                        hum_valor = float(trozos[2])  #Extraemos los datos de humedad

                        eje_x.append(t_actual)              # Añade el instante de tiempo actual al final del eje X
                        temperaturas.append(temp_valor)     # Guardamos la nueva temperatura leída en el historial para poder dibujarla en la gráfica
                        humedad.append(hum_valor)           # Guardamos la nueva humedad leída en el historial para poder dibujarla en la gráfica

                        # Si la media se calcula en Tierra, la calculamos aquí con la cola circular
                        if not calcular_en_satelite:
                            media_val = calcular_media_tierra(temp_valor)   # Metemos la temperatura actual en la cola circular de 10 muestras y devuelve la media móvil
                            eje_x_med.append(t_actual)                      # Registramos el instante de tiempo actual en el eje X propio de la media
                            medias_temp.append(media_val)                   # Guardamos la media recién calculada en el historial para dibujarla en la gráfica
                            comprobar_alarma_temperatura(media_val)         #Comprobamos si la media supera el límite maximo 3 veces seguidas

                        #Actualizamos los datos de las líneas de temperatura, humedad, y media
                        linea_temp.set_data(eje_x, temperaturas)
                        linea_hum.set_data(eje_x, humedad)
                        linea_med.set_data(eje_x_med, medias_temp)
                        #Creamos un ejeX dinámico y un eje Y entre 0 y 100
                        ax.set_xlim(0, max(20, t_actual + 5))
                        ax.set_ylim(0, 100)
                        canvas.draw()

                    # CÓDIGO 4: Media enviada desde el Satélite -> "4:media"
                    elif codigo == '4' and len(trozos) >= 2 and not sistema_pausado:
                        # Solo incorporamos esta media si el modo activo es calcular en el Satélite
                        if calcular_en_satelite:
                            if tiempo_inicio is None:
                                tiempo_inicio = time.time()
                            # Calcula cuántos segundos han pasado desde tiempo_inicio hasta ahora y redondea a 1 decimal para colocar el punto en ele je X
                            t_actual = round(time.time() - tiempo_inicio, 1)
                            media_val = float(trozos[1])    # Toma el segundo trozo del mensaje y lo convierte de texto a número decimal

                            eje_x_med.append(t_actual)
                            medias_temp.append(media_val)   # Guarda el valor de la media recibida del Satélite al final de la lista de medias para pintarla
                            linea_med.set_data(eje_x_med, medias_temp)
                            canvas.draw()   #Redibujamos en la gráfica

                    # CÓDIGO 2: Distancia y Ángulo para el Radar -> "2:dist:angulo"
                    # siempre que tenga al menos 3 partes y el sistema no esté pausado
                    elif codigo == '2' and len(trozos) >= 3 and not sistema_pausado:
                        dist_val = float(trozos[1])     # Extrae la distancia medida por el sensor de ultrasonidos y la convierte a número decimal
                        ang_grados = float(trozos[2])   # Extrae el ángulo del servo en grados y lo convierte a número decimal
                        ang_rad = math.radians(ang_grados)  # Convierte el ángulo de grados a radianes

                        # Guardamos las últimas 15 lecturas para efecto barrido radar
                        angulos_radar.append(ang_rad)   # Añade el nuevo ángulo en radianes al historial de puntos del radar
                        distancias_radar.append(dist_val)   # Añade la nueva distancia medida al historial de puntos del radar
                        if len(angulos_radar) > 15:         # Si ya hay más de 15 lecturas guardadas, elimina la más antigua
                            angulos_radar.pop(0)
                            distancias_radar.pop(0)
                        
                        # Actualiza los marcadores rojos de objetos detectados en la gráfica
                        puntos_radar.set_data(angulos_radar, distancias_radar)
                        linea_barrido.set_data([0, ang_rad], [0, max(100, dist_val)])   # Dibuja la línea verde de barrido desde el centro
                        ax_radar.set_ylim(0, max(100, max(distancias_radar) + 10))      # Ajusta el límite radial máximo (eje Y polar) a al menos 100
                        canvas.draw()       #Redibujamos

                    # ALARMAS DESDE ARDUINO
                    elif codigo == '3':
                        activar_parada_por_alarma("ALARMA: Fallo en sensor Temperatura/Humedad")
                    elif codigo == '5':
                        activar_parada_por_alarma("ALARMA: Fallo en sensor de Distancia")
                    elif codigo == '6':
                        activar_parada_por_alarma("ALARMA SATÉLITE: 3 medias consecutivas excesivas")
                    elif codigo == '99':
                        activar_parada_por_alarma("ALARMA: Pérdida de comunicación con el Satélite")

                except Exception as e:
                    print(f"Error al procesar la línea: {e}")

    window.after(200, leer_datos)

# BOTÓN INICIAR: Resetea completamente las gráficas y empieza desde t=0
def AClick():
    # Declaramos como globales todas las variables que vamos a limpiar o reiniciar desde dentro de la función
    global temperaturas, humedad, medias_temp, eje_x, eje_x_med
    global angulos_radar, distancias_radar, tiempo_inicio, sistema_pausado, alarma_activa
    global indice_cola, total_en_cola, contador_medias_altas_tierra

    # 1. Borrar todos los datos anteriores y reiniciar reloj y colas
    temperaturas.clear()        # Vaciamos la lista del historial de temperaturas
    humedad.clear()             # Vaciamos la lista del historial de humedad
    medias_temp.clear()         # Vaciamos la lista del historial de medias 
    eje_x.clear()               # Vaciamos el eje de tiempos de temperatura y humedad
    eje_x_med.clear()           # Vaciamos el eje de tiempos de las medias
    angulos_radar.clear()       # Vaciamos los ángulos guardados del radar
    distancias_radar.clear()    # Vaciamos las distancias guardadas del radar

    indice_cola = 0                     # Volvemos a situar el puntero de la cola circular en la posición 0
    total_en_cola = 0                   # Reiniciamos a 0 el número de muestras acumuladas en la cola circular
    contador_medias_altas_tierra = 0    # Reiniciamos la cuenta de medias consecutivas por encima del límite de alarma
    tiempo_inicio = time.time()         # Guardamos el instante actual como nuevo origen de tiempo 
    sistema_pausado = False             # Nos aseguramos que el sistema no esté pausado y acepte datos nuevos
    alarma_activa = False               # Limpiamos cualquier estado de alarma previo para permitir nuevas comprobaciones

    # 2. Limpiar visualmente las gráficas inmediatamente (Borramos los puntos y reestablecemos los ejes)
    linea_temp.set_data([], [])
    linea_hum.set_data([], [])
    linea_med.set_data([], [])
    puntos_radar.set_data([], [])
    linea_barrido.set_data([], [])
    ax.set_xlim(0, 20)
    ax.set_ylim(0, 50)
    canvas.draw()

    # 3. Enviar orden de inicio al Arduino
    if mySerial and mySerial.is_open:
        mySerial.reset_input_buffer() # Descarta datos viejos pendientes en el buffer
        mySerial.write("Inicio\n".encode('utf-8'))
    tituloLabel.config(text="Gráfica Iniciada (Reseteada)", fg="black")

# BOTÓN PARAR: Pausa la gráfica manteniendo el reloj interno corriendo para crear el hueco
def BClick():
    # Indicamos que vamos a modificar la variable global sistema_pausado
    global sistema_pausado
    sistema_pausado = True      # Activamos la pausa para que leer_datos() deje de registrar/dibujar nuevos valores pero sin detener el reloj interno (tiempo_inicio) para que quede el hueco de tiempo
    if mySerial and mySerial.is_open:
        mySerial.write("3:2\n".encode('utf-8'))     # Enviamos el comando "3:2" con salto de línea '\n'
    tituloLabel.config(text="Gráfica Parada", fg="black")

# BOTÓN REANUDAR: Retoma la captura usando el tiempo real transcurrido (generando el hueco)
def CClick():
    # Declaramos como globales las variables de estado y contador que vamos a restablecer
    global sistema_pausado, alarma_activa, contador_medias_altas_tierra
    if tiempo_inicio is None: #Si nunca se ha efectuado la captura y recepción de datos, ejecutamos AClick y salimos de la función
        AClick()
        return

    sistema_pausado = False             # Desactivamos la pausa para volver a procesar y graficar datos entrantes
    alarma_activa = False               # Limpiamos el estado de alarma por si se reanuda tras una parada por alarma
    contador_medias_altas_tierra = 0    #Reiniciamos el contador

    # Insertamos None para que la línea no una en diagonal los puntos separados por la pausa,
    # dejando el hueco limpio en la gráfica.
    if len(eje_x) > 0:      # Solo si ya había al menos un punto registrado en temperatura y humedad
        t_hueco = round(time.time() - tiempo_inicio, 1)     # Calculamos el segundo exacto en el que se reanuda
        eje_x.append(t_hueco)                               # Añadimos ese instante de tiempo al eje X
        temperaturas.append(None)                           # Cortamos la línea roja de temperatura en ese punto
        humedad.append(None)                                # Cortamos la línea azul de humedad en ese punto
    
    if len(eje_x_med) > 0:  # Solo si ya había al menos un punto registrado en la media
        t_hueco = round(time.time() - tiempo_inicio, 1)     # Calculamos el segundo exacto en el que se reanuda
        eje_x_med.append(t_hueco)                           # Añadimos ese instante al eje X de la media
        medias_temp.append(None)                            # Cortamos la línea de la media en ese punto
 
    # Si existe conexión serie y el puerto está abierto, enviamos "3:3" para ordenar reanudar el envío
    if mySerial and mySerial.is_open:
        mySerial.write("3:3\n".encode('utf-8'))
    tituloLabel.config(text="Gráfica Reanudada", fg="black")

def MediaSateliteClick():
    global calcular_en_satelite
    calcular_en_satelite = True
    if mySerial and mySerial.is_open:
        mySerial.write('MediaSatelite\n'.encode('utf-8'))
    print('Comando enviado: MediaSatelite')
    tituloLabel.config(text="Modo Media: Calculando en Satélite", fg="black")

def MediaTierraClick():
    global calcular_en_satelite
    calcular_en_satelite = False
    if mySerial and mySerial.is_open:
        mySerial.write('MediaTierra\n'.encode('utf-8'))
    print('Comando enviado: MediaTierra')
    tituloLabel.config(text="Modo Media: Calculando en Tierra", fg="black")

# Leemos lo que el usuario ha escrito en la caja de comandos y lo enviamos por el puerto serie
def enviar_comando_personalizado():
    texto = entrada_comando.get().strip()   # Obtenemos el texto de entrada_comando y eliminamos espacios sobrantes
    # Solo enviamos algo si el campo de texto no está vacío
    if texto:
        if mySerial and mySerial.is_open:
            mensaje = texto + '\n'          # Añadimos '\n' como delimitador de fin de trama para la lectura serie
            mySerial.write(mensaje.encode('utf-8')) #Enviamos el texto por el puerto serie
            print(f'Comando personalizado enviado: {texto}')
            entrada_comando.delete(0, tk.END)   #>impiamos la caja de texto para el siguiente comando
        else:
            print('Error: El puerto serie no está abierto.')

# Envía el límite máximo de temperatura escrito para las alarmas
def enviar_max_temp():
    valor = entrada_max_temp.get().strip()  # Leemos el valor escrito en entrada_max_temp y quitamos espacios en blanco
    if valor and mySerial and mySerial.is_open:
        # Si hay un valor escrito y el puerto serie está abierto, enviamos la orden con prefijo "MaxTemp:"
        mySerial.write(f"MaxTemp:{valor}\n".encode('utf-8'))    
        print(f"Límite máximo de temperatura actualizado a {valor}°C")

# Configuramos la ventana de la interfaz (tamaño y título):
window = Tk()
window.title("Control y Monitorización Arduino - Versión 2")
window.geometry("1100x680")

# Configuramos la cuadrícula (manteniendo columnas 0 para controles y 1 para gráficas):
for r in range(11):
    window.rowconfigure(r, weight=1)
window.columnconfigure(0, weight=1)
window.columnconfigure(1, weight=3)

# Etiqueta del estado de la gráfica:
tituloLabel = Label(window, text="Pulsa Iniciar para empezar", font=("Courier", 11, "bold"))
tituloLabel.grid(row=0, column=0, columnspan=2, padx=5, pady=5, sticky=N + S + E + W)

# Botones principales (mismos colores, orden y nombres):
AButton = Button(window, text="Iniciar", bg="#0AAE28", fg="white", font=("Arial", 10, "bold"), command=AClick)
AButton.grid(row=1, column=0, padx=10, pady=3, sticky=N + S + E + W)

BButton = Button(window, text="Parar", bg="#BC0C0C", fg="white", font=("Arial", 10, "bold"), command=BClick)
BButton.grid(row=2, column=0, padx=10, pady=3, sticky=N + S + E + W)

CButton = Button(window, text="Reanudar", bg='#818CF8', fg="white", font=("Arial", 10, "bold"), command=CClick)
CButton.grid(row=3, column=0, padx=10, pady=3, sticky=N + S + E + W)

label_instrucciones = Label(
    window,
    text='Leyenda de Comandos:\n'
         '1:ms -> Periodo T/H (ej: 1:2000)\n'
         '2:grados -> Ángulo servo (0-180) | 2:AUTO -> Barrido\n'
         '3:2 -> Parar | 3:3 -> Reanudar\n'
         '5:ms -> Periodo Distancia (ej: 5:500)',
    font=('Arial', 8, 'bold'),
    fg='#374151',
    justify=LEFT
)
label_instrucciones.grid(row=4, column=0, padx=10, pady=(3, 0), sticky=N + S + E + W)

# Caja de texto para escribir el comando (Fila 5)
entrada_comando = Entry(window, font=('Arial', 11), justify='center')
entrada_comando.grid(row=5, column=0, padx=10, pady=(0, 3), sticky=N + S + E + W)

DButton = Button(window, text='Enviar Comando', bg="#F63BC1", fg='white', font=('Arial', 10, 'bold'), command=enviar_comando_personalizado)
DButton.grid(row=6, column=0, padx=10, pady=3, sticky=N + S + E + W)

# Botones para elegir dónde se calcula la media (descomentados y activos para V2)
MediaSat = Button(window, text='Media Satélite', bg="#FBAE14", fg='white', font=('Arial', 9, 'bold'), command=MediaSateliteClick)
MediaSat.grid(row=7, column=0, padx=10, pady=2, sticky=N + S + E + W)

MediaTie = Button(window, text='Media Tierra', bg="#19E4DE", fg='white', font=('Arial', 9, 'bold'), command=MediaTierraClick)
MediaTie.grid(row=8, column=0, padx=10, pady=2, sticky=N + S + E + W)

# Control de Temperatura Máxima para Alarma (Requisito 11 V2)
frame_max = Frame(window)
frame_max.grid(row=9, column=0, padx=10, pady=3, sticky=N + S + E + W)
Label(frame_max, text="T. Máx Alarma (°C):", font=('Arial', 9, 'bold')).pack(side=LEFT)
entrada_max_temp = Entry(frame_max, width=6, font=('Arial', 10), justify='center')
entrada_max_temp.insert(0, "30.0")
entrada_max_temp.pack(side=LEFT, padx=4)
Button(frame_max, text="Fijar", bg="#F59E0B", fg="white", font=('Arial', 8, 'bold'), command=enviar_max_temp).pack(side=LEFT)

# Creamos la figura con dos subgráficas: izquierda T/H/Media, derecha Radar de ultrasonidos
fig = Figure(figsize=(8, 5), dpi=100)
ax = fig.add_subplot(121)
ax_radar = fig.add_subplot(122, projection='polar')

# Subgráfica 1: Temperatura, Humedad y Media
linea_temp, = ax.plot([], [], color='red', marker='o', label='Temp')
linea_hum, = ax.plot([], [], color='blue', marker='o', label='Hum')
linea_med, = ax.plot([], [], color='green', marker='s', linestyle='--', label='Media (10)')
ax.set_title("Evolución Tª, Humedad y Media")
ax.set_xlabel("Tiempo (s)")
ax.set_ylabel("Valor")
ax.legend(loc='upper left')
ax.grid(True)

# Subgráfica 2: Radar Ultrasonidos (0° a 180°)
ax_radar.set_thetamin(0)
ax_radar.set_thetamax(180)
ax_radar.set_title("Radar")
puntos_radar, = ax_radar.plot([], [], 'ro', markersize=6, label='Objeto')
linea_barrido, = ax_radar.plot([], [], 'g-', linewidth=1.5)

# Juntamos las gráficas y la interfaz en la columna 1 ocupando toda la altura:
canvas = FigureCanvasTkAgg(fig, master=window)
canvas_widget = canvas.get_tk_widget()
canvas_widget.grid(row=1, column=1, rowspan=9, padx=10, pady=10, sticky=N + S + E + W)

window.after(500, leer_datos)
window.mainloop()
