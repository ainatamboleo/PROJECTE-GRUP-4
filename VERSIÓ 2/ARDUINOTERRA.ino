´´´C
#include <SoftwareSerial.h>
SoftwareSerial mySerial(10, 11);

unsigned long nextMillis = 500;
const int ledVerdeTierra = 13;

const int ledErrorBlanco = 8;   // Alarma 1: Fallo sensor DHT11
const int ledErrorAzul = 7;     // Alarma Comunicación perdida
const int ledErrorAmarillo = 9; // Alarma 2: Fallo sensor distancia

unsigned long intervaloEnvio = 3000;
unsigned long TiempoMaxSinDatos = 1000 + intervaloEnvio;
unsigned long prevMillisLed = 0; 
unsigned long intervaloApagadoLed = 300;

unsigned long ultimoTiempoDatos = 0;
bool sistemaIniciado = false;

void setup() {
   Serial.begin(9600);
   mySerial.begin(9600);
   pinMode(ledVerdeTierra, OUTPUT);
   pinMode(ledErrorBlanco, OUTPUT);
   pinMode(ledErrorAzul, OUTPUT);
   pinMode(ledErrorAmarillo, OUTPUT);
}

void loop() {
   // 1. Recepción de datos desde el Satélite
   if (mySerial.available() > 0) {
      String datos = mySerial.readStringUntil('\n'); // Lehemos todos los datos enviados por el Satélite
      datos.trim();

      ultimoTiempoDatos = millis();
      digitalWrite(ledErrorAzul, LOW);

      if (datos == "Alarma1") { // Si recibimos la alarma1 la transmitimos a Python y encendemos el LED blanco
         digitalWrite(ledErrorBlanco, HIGH);
         Serial.print("3\n"); // Código 3 a Python (Fallo del sensor de temperatura/humedad)
      }
      else if (datos == "Alarma1OFF") { // Apagamos el LED blanco si recibimos la orden de apagar la alarma1
         digitalWrite(ledErrorBlanco, LOW);
      }
      else if (datos == "Alarma2") { //Si recibimos la alarma2 la transmitimos a Python y encendemos el LED amarillo
         digitalWrite(ledErrorAmarillo, HIGH);
         Serial.print("5\n"); // Código 5 a Python (Fallo sensor distancia)
      }
      else if (datos == "Alarma2OFF") { // Apagamos el LED amarillo si recibimos la orden de apagar la alarma2
         digitalWrite(ledErrorAmarillo, LOW);
      }
      else if (datos == "Alarma3") { // Si recibimos la alarma3 la transmitimos a Python
         Serial.print("6\n"); // Código 6 a Python (3 medias consecutivas altas)
      }
      // Si el mensaje recibido son las lecturas del sensor (no es una alarma ni Ok)
      else if (datos != "Ok" && datos.length() > 0) {
         digitalWrite(ledErrorAzul, LOW);

         digitalWrite(ledVerdeTierra, HIGH); //encendemos el led verde para indicar que hemos recibido datos del satélite
         prevMillisLed = millis();

         Serial.println(datos); // Imprime los datos a Python (1:T:H, 2:Dist:Ang, 4:Med)
      }
      mySerial.println("Ok");
   }

   // Comprobación de fallo de comunicación
   if ((sistemaIniciado == true) && (millis() - ultimoTiempoDatos > TiempoMaxSinDatos)) {
      digitalWrite(ledErrorAzul, HIGH);
      Serial.println("99"); // Avisa a Python del fallo de comunicación
   }

   // Apagado del LED verde tras la recepción de datos del satélite y pasado el tiempo de apagado
   if (digitalRead(ledVerdeTierra) == HIGH && (millis() - prevMillisLed >= intervaloApagadoLed)) {
      digitalWrite(ledVerdeTierra, LOW);
   }

   // 2. Recepción de órdenes desde Python y envío al Satélite
   if (Serial.available() > 0) { 
      String data = Serial.readStringUntil('\n');     //Leemos las órdenes enviadas desde Python
      data.trim();
      
      if (data.startsWith("1:")) {
         // Código 1: Cambiar periodo de envío en ms (Formato 1:ms)
         String valorStr = data.substring(2);
         unsigned long ms = valorStr.toInt();
         if (ms > 0) {
            intervaloEnvio = ms;
            TiempoMaxSinDatos = intervaloEnvio + 1500;
         }
         mySerial.println(data);
      }
      else if (data == "Inicio" || data == "3:3") { //Si recibimos la orden de inicio, enviamos la orden al satélite e iniciamos el sistema 
         sistemaIniciado = true;
         ultimoTiempoDatos = millis(); // Arrancamos el cronómetro de seguridad
         mySerial.println(data);
      }
      else if (data == "Parar" || data == "3:2") { //Si recibimos la orden de parar, enviamos la orden al satélite y paramos el sistema
         sistemaIniciado = false;
         digitalWrite(ledErrorAzul, LOW); // Apagamos el LED azul de fallo de comunicación para evitar confusión con un problema de conexión
         mySerial.println(data);
      }
      else { // Si es otro tipo de orden, cambios en los grados del sensor o activación del modo de barrido, etc., se reenvía directamente al satélite
         // Reenvía directamente en estos formatos: 2:grados / 2:Barrido / 5:ms / MediaSatelite / MediaTierra / MaxTemp:X
         mySerial.println(data);
      }
   }
}
´´´
