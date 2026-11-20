#include <SoftwareSerial.h>
#include <DHT.h>
#include <Servo.h>
// Configuración del puerto serie para comunicación con Tierra
SoftwareSerial mySerial(10, 11);

#define DHTPIN 2
#define DHTTYPE DHT11
DHT dht(DHTPIN, DHTTYPE);

// Pines Sensor Ultrasonidos y Servomotor
const int trigPin = 3; // Pin Trigger del sensor (emite el pulso de sonido)
const int echoPin = 4; // Pin Echo del  (recibe el rebote del eco)
const int servoPin = 6; // Pin PWM donde está conectada la señal del servomotor
Servo radarServo; // Creamos el objeto 'radarServo' para mover el motor

//Pin del LED verde de confirmación de envío de datos al Arduino Tierra
const int ledVerdeSatelite = 5; //LED conectado al PIN 5

// Tiempos Temperatura y Humedad
unsigned long intervaloEnvio = 3000; //Tiempo entre los envios del sensor
unsigned long ultimoEnvio = 0; //Guarda el instante del último envio del sensor

// Tiempos Distancia y Radar
unsigned long intervaloDistancia = 1000; //Guarda el instante del último envio del sensor
unsigned long ultimoEnvioDistancia = 0; //Guarda el instante del último envío del radar
bool enviandoDistancia = true; //Controla si el radar esta enviando los datos
bool modoBarrido = true; //Permite iniciar el modo barrido
int anguloServo = 90; //Ángulo del servomotor
int pasoServo = 15; // Incremento en grados por cada paso de barrido

// Tiempo de parpadeo LED
unsigned long intervaloParpadeoLed = 100; //Duración del parpadeo
unsigned long tiempoEncendidoLed = 0; //Instante en el que se encendió el LED
bool ledEncendido = false; //Indica si el LED está encendido

// Control de conexión con Tierra
unsigned long ultimoOkRecibido = 0; //Heartbeat que permite controlar la conexión entre arduinos
const unsigned long tiempoMaximoSinOk = 5000; // 5 segundos sin recibir "Ok" = desconectado
bool conectadoConTierra = false;

//Variable para controlar si el satélite debe enviar datos o no
bool enviando = false;

// Vector para las últimas 10 temperaturas para calcular la media
float ultimasTemperaturas[10];
int indiceTemp = 0; //Posición donde se guarda la temperatura
int totalTemps = 0; //Total de temperaturas guardadas
bool MediaEnSatelite = false; //Indica si las medias se han de calcular desde el satélite o tierra

// Configuración de alarma por 3 medias consecutivas por encima del límite de temperatura establecido por el usuario (Inicialmente 30ºC)
float tempMaximaLimite = 30.0; //Umbral de temperatura
int contadorMediasAltas = 0;  //Contador indicará cuantas temperaturas sobrepasan el umbral establecido

// Añadimos las temperaturas al vector y calculamos su media
float actualizarYCalcularMedia(float nuevaTemp) {
   ultimasTemperaturas[indiceTemp] = nuevaTemp; //Creamos un vector que almacena la temperatura recibida
   indiceTemp = (indiceTemp + 1) % 10; // El índice avanza hasta el 9, al llegar a 10 vuelve a la posición 0
   if (totalTemps < 10) {
      totalTemps++; //Contador guarda cuántas temperaturas se han guardado hasta llegar a 10
   }
   float suma = 0; //Inicializamos 'suma', variable que almacenará la suma de todas las temperaturas
   for (int j = 0; j < totalTemps; j++) {
      suma += ultimasTemperaturas[j]; // Suma todas las temperaturas almacenadas en la cola
   }
   return suma / totalTemps; //Devuelve la media
}

// Configuramos los pines del radar asi como la configuración del mismo y leemos la distancia con en cm, en caso de error devuelve -1.0
float leerDistancia() {
   digitalWrite(trigPin, LOW);
   delayMicroseconds(2);
   digitalWrite(trigPin, HIGH);
   delayMicroseconds(10);
   digitalWrite(trigPin, LOW);
   
   long duracion = pulseIn(echoPin, HIGH, 30000); // Timeout del radar: 30ms, correponde a una distancia máxima de 5 metros aproximadamente
   if (duracion == 0) {
      return -1.0; // Fallo de lectura o sensor desconectado
   }
   return duracion * 0.0343 / 2.0; //Fórmula para calcular la distancia
}

void setup(){
   mySerial.begin(9600);
   Serial.begin(9600);
   pinMode(ledVerdeSatelite, OUTPUT);
   pinMode(trigPin, OUTPUT);
   pinMode(echoPin, INPUT); // Se configura pin Echo como entrada para escuchar el rebote
   
   radarServo.attach(servoPin); // Vincula el servomotor al pin 6
   radarServo.write(anguloServo); // Coloca el servo en su posición inicial (90°)
   
   dht.begin(); // Inicializa el sensor de temperatura y humedad DHT11
} 

void loop() {
   // 1. Escuchar órdenes de la Tierra
   if (mySerial.available() > 0) { // Comprueba si ha llegado algún mensaje desde Tierra
      String data = mySerial.readStringUntil('\n'); // Lee la línea completa hasta el salto de línea '\n'
      data.trim(); // Elimina espacios en blanco

      Serial.print("Recibido de Tierra -> ");
      Serial.println(data);

      // CALCULAR MEDIAS (Dónde se calculan)
      if (data == "MediaSatelite") {
         MediaEnSatelite = true; //Activamos el cálculo en el Satélite
         contadorMediasAltas = 0; //Reiniciamos el contador
         Serial.println("Modo activado: Calculando media en el Satélite.");
      }
      else if (data == "MediaTierra") {
         MediaEnSatelite = false; //Si la data es 'Tierra', desactivamos el cálculo en el Satélite
         contadorMediasAltas = 0; //Reiniciamos el contador
         Serial.println("Modo activado: Calculando media en Tierra.");
      }
      // BOTONES INICIO / PARAR / REANUDAR
      else if (data == "Inicio") {
         enviando = true; //Habilitamos el envío de datos
         enviandoDistancia = true; //Habilitamos el envío de datos del radar
         conectadoConTierra = true;
         ultimoOkRecibido = millis(); //Reiniciamos el temporizador de conexión
         // Reiniciamos vector al iniciar de cero
         indiceTemp = 0;
         totalTemps = 0;
         contadorMediasAltas = 0;
      }
       //Botón Reanudar
      else if (data == "3:3") { //3:3 Equivale a reanudar
         enviando = true; //Reactivamos el envío sin borrar las medias
         conectadoConTierra = true;
         ultimoOkRecibido = millis();
      }
      //Botón Parar
      else if (data == "3:2" || data == "Parar") {
         enviando = false; //Detenemos el envío de datos
         conectadoConTierra = false;
         digitalWrite(ledVerdeSatelite, LOW); //Apagamos el LED que indica la transmisión de datos
      }
      // CÓDIGO 1: Cambiar periodo de envío de T y H
      else if (data.startsWith("1:")) {
         String valorStr = data.substring(2); //Extraemos el texto que hay después de "1:"
         unsigned long ms = valorStr.toInt(); //Convertimos el texto a un número entero
         if (ms > 0) {
            intervaloEnvio = ms; //Actualizamos el intervalo de envío según lo que haya indicado el usuario
            Serial.print("Nuevo periodo T/H aplicado: ");
            Serial.print(ms);
            Serial.println(" ms.");
         }
      }
      // CÓDIGO 2: Orientación del servo (manual en grados o modo Barrido)
      else if (data.startsWith("2:")) {
         String valorStr = data.substring(2); //Extraemos los datos que van después del "2:"
         if (valorStr == "AUTO") {
            modoBarrido = true; //Si recibe "AUTO" se activa el modo barrido
            Serial.println("Radar en modo barrido.");
         } else {
            int orientacion = valorStr.toInt(); //Si no recibimos 'Rastreo', convertimos la data en un número entero
            if (orientacion >= 0 && orientacion <= 180) {
               modoBarrido = false; //Desactivamos el modo barrido
               anguloServo = orientacion; //Fijamos al ángulo soliditado
               radarServo.write(anguloServo); //Movemos el servo al ángulo solicitado
               Serial.print("Nueva orientación del sensor: ");
               Serial.print(orientacion);
               Serial.println(" grados.");
            }
         }
      }
      // CÓDIGO 4: Parar/Reanudar envío de distancia (4:0 parar, 4:1 reanudar)
      else if (data.startsWith("4:")) {
         int orden = data.substring(2).toInt(); //Cogemos los datos que hay después del "4:"
         enviandoDistancia = (orden == 1);
      }
      // CÓDIGO 5: Cambiar periodo de envío de distancia
      else if (data.startsWith("5:")) {
         unsigned long ms = data.substring(2).toInt(); //Cogemos los datos que hay después del "5:"
         if (ms > 0) {
            intervaloDistancia = ms; //Actualizamos el periodo de envío
         }
      }
      // Límite máximo de temperatura para alarma de medias
      else if (data.startsWith("MaxTemp:")) {
         tempMaximaLimite = data.substring(8).toFloat(); // Extrae el número decimal a partir del carácter 8
         contadorMediasAltas = 0; // Reinicia el contador de medias consecutivas
      }
      else if (data == "Ok") {
         ultimoOkRecibido = millis();
         conectadoConTierra = true;
      }
   }
   // Comprobamos si ha pasado demasiado tiempo sin recibir "Ok" de Tierra
   if ((enviando == true) && (millis() - ultimoOkRecibido > tiempoMaximoSinOk)) {
      conectadoConTierra = false; // Se perdió la comunicación
   }

   // 2. Envío periódico de datos de Temperatura y Humedad si está activo
   if ((enviando == true) && (millis() - ultimoEnvio >= intervaloEnvio)) {
      ultimoEnvio = millis();

      float h = dht.readHumidity(); // Lee la humedad
      float t = dht.readTemperature(); // Lee la temperatura

      // Comprobar si el sensor está desconectado o falla (devuelve NaN)
      if (isnan(h) || isnan(t)) {
         mySerial.println("Alarma1"); // Envía Alarma por fallo/desconexión del sensor DHT11
      } else {
         mySerial.println("AlarmaOFF"); // Apaga las alarmas de DHT11 si todo es normal

         // Enviar datos normales de T y H al Arduino Tierra con la siguiente estructura "1:temperatura:humedad"
         mySerial.print("1:");
         mySerial.print(t);
         mySerial.print(":");
         mySerial.print(h);
         mySerial.print("\n");

         // Si el usuario eligió calcular la media en el satélite
         if (MediaEnSatelite) {
            float mediaSatelite = actualizarYCalcularMedia(t);
            // Envía la media calculada a Tierra con el prefijo "4:"
            mySerial.print("4:");
            mySerial.print(mediaSatelite);
            mySerial.print("\n");

            // Comprobar 3 medias consecutivas por encima del límite
            if (mediaSatelite > tempMaximaLimite) {
               contadorMediasAltas++; // Incrementa el contador de temperaturas que superan el umbral
               if (contadorMediasAltas >= 3) {
                  mySerial.println("Alarma3"); //Si se superan tres temperaturas consecutivas, se activa la alarma
               }
            } else {
               contadorMediasAltas = 0; // Si baja del límite, se resetea el contador
            }
         }
      }
      // Hacemos parpadear el LED verde si existe conexión confirmada con Tierra
      if (conectadoConTierra == true) {
         digitalWrite(ledVerdeSatelite, HIGH);
         tiempoEncendidoLed = millis();
         ledEncendido = true;
      }
   }

   // 3. Envío periódico de datos de Distancia y movimiento del Radar (Versión 2)
   if ((enviando == true) && (enviandoDistancia == true) && (millis() - ultimoEnvioDistancia >= intervaloDistancia)) {
      ultimoEnvioDistancia = millis(); // Reinicia el cronómetro del radar

      // Si está en modo rastreo automático, mueve el servo un paso entre 0° y 180°
      if (modoBarrido) {
         anguloServo += pasoServo;
         if (anguloServo >= 180) { // Al llegar al extremo derecho (180°), invierte el sentido
            anguloServo = 180;
            pasoServo = -pasoServo;
         } else if (anguloServo <= 0) { // Al llegar al extremo izquierdo (0°), invierte el sentido
            anguloServo = 0;
            pasoServo = -pasoServo;
         }
         radarServo.write(anguloServo); // Mueve el servomotor a la nueva posición
      }

      float dist = leerDistancia();
      if (dist < 0) {
         mySerial.println("Alarma2"); // Fallo en el sensor de ultrasonidos
      } else {
         // Envía los datos  del radar con formato "2:distancia:angulo"
         mySerial.println("Alarma2OFF");
         mySerial.print("2:");
         mySerial.print(dist);
         mySerial.print(":");
         mySerial.println(anguloServo);
      }
   }

   // 4. Apagado no bloqueante del LED verde del satélite
   if ((ledEncendido == true) && (millis() - tiempoEncendidoLed >= intervaloParpadeoLed)) {
      digitalWrite(ledVerdeSatelite, LOW);
      ledEncendido = false;
   }
}
