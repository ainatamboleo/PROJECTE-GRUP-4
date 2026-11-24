# VERSIÓ 2 GRUP 4
En aquesta versió del projecte hem hagut de fer certes addicions als codis que ja teniem de la versió 1. A més a més, hem aprofitat per millorar errors que teniem pendents a la versió 1. En primer lloc, ja existeix una connexió estable entre Arduinos, ja que el que passava és que teniem errors als codis (per exemple, havíem establert a través del port serial una connexió directe entre el satèl·lit i pyhton) i per aquesta raó ni ens funcionava correctament l'alarma blava. En segon lloc, també hem aconseguit que la gràfica deixi un espai en blanc si l'usuari decideix aturar el programa i després reanudar-lo. Gràcies a les millores que vam efectuar de la versió 1, la versió 2 ens ha resultat més fàcil i hem pogut abansar sense gaire problemàtica. En aquest document us explicarem com ha evolucionat el nostre projecte pas a pas, a més dels codis finals i els unitaris de cada unitat que conforme el nostre projecte.

## Protocol d'aplicació
En aquest pas havíem d'establir una mena de llegenda per tal de tenir constància de quin tipus de dades estavem enviant/rebent, ja que cada cop el projecte consistia en afegir més valors i per tal de facilitar la comunicació entre Arduinos, vam decidir fraccionar-ho de la següent manera:
**Les dades que siguin enviades amb un 1 davant són dades de temperatura i humitat.**
**Les dades que siguin enviades amb un 2 davant són dades de distància.**
**Les dades que siguin enviades amb un 3 davant són dades relacionades amb els botons de la interfaz.**

## Càlcul de mitjanes de les temparatures
Em aquest pas el que havíem de fer és afegir dins de la gràfica de la interfaz una variable que recol·lecti 10 dades des del sensor de temperatura i donunel valor d'una mitjana per tal de mantindre un control sobre les temperatures rebudes pel satèl·lit. Això també pot ajudar, més endevant a afegir una funció que activi un ventilador per alleugir el satè·lit si s'hi detecta que la mitjana és més alta a la que hauria de ser.

## Sensor de distància
Aquest pas implicava afegir un sensor de distància al nostre satèl·lit que tingués un rang de visibilitat de **180º** i pogués determinar com de lluny o d'aprop tenia els objectes que l'envolten. Aquestes dades també les vam afegir a l'interfaz on es troba la gràfica on hi apareix les dades de temperatura i humitat ja que d'aquesta manera a l'usuari li resultaria més fàcil si ho trobava tot en un mateix lloc.

## Utilització de la IA dins de la versió 2
Malgrat que la majoria de codis estan fets i basats en codis explicats a classe o en el pròpia guia detallada del projecte, sí que hem usat la IA sobretot per detectar errors o ajudar-nos quan ens estancaven en algún pas. La IA que hem utilitzat és GEMINI ja que és de les més recomenades i fiables. La vam utlitzar principalment en el codi de Python de la interfaz, ja que ens estava costant molt que quan l'usuari cliqués el botó de reanudar, la interfaz deixes un espai en blanc des del moment de l'aturada. A part de l'ús de la IA també ens vam informar per eines com YouTube ja que no sabiem exactament com enganxar el radar amb el motor per tal d'efectuar el sensor de distància.

## CODIS UNITARIS
Aquí hem recopilat els codis unitaris usats fins ara:

**CODI UNITARI SENSOR DE TEMPERATURA I HUMITAT**
```C
// Definiciones necesarias
#include <DHT.h>
#define DHTPIN 2
#define DHTTYPE DHT11
DHT dht(DHTPIN, DHTTYPE);
void setup() {
   Serial.begin(9600);
   // Inicialización del sensor
   dht.begin();
}
void loop() {
   delay(2000);
   float h = dht.readHumidity();
   float t = dht.readTemperature();
   if (isnan(h) || isnan(t))
      Serial.println("Error al leer el sensor DHT11");
   else {
      Serial.print("Humedad: ");
      Serial.print(h);
      Serial.print("%\t");
      Serial.print("Temperatura: ");
      Serial.print(t);
      Serial.println("°C");
   }
}
```

**CODI UNITARI SENSOR DE DISTÀNCIA**
```C
#include <Servo.h>

Servo radarServo;
const int trigPin = 3;
const int echoPin = 4;
const int servoPin = 6;

void setup() {
  Serial.begin(9600);
  pinMode(trigPin, OUTPUT);
  pinMode(echoPin, INPUT);
  radarServo.attach(servoPin);
  Serial.println("=== TEST UNITARIO RADAR INICIADO ===");
}

long medirDistancia() {
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);

  // Timeout de 25000 us (~4 metros máximo) para no bloquear el programa
  long duracion = pulseIn(echoPin, HIGH, 25000);
  if (duracion == 0) return -1; // Indica error o fuera de rango
  return duracion * 0.034 / 2;
}

void loop() {
  for (int ang = 0; ang <= 180; ang += 15) {
    radarServo.write(ang);
    delay(250);
    long dist = medirDistancia();
    Serial.print("Angulo: "); Serial.print(ang);
    Serial.print(" deg | Distancia: ");
    if (dist == -1) Serial.println("ERROR / SIN ECO");
    else { Serial.print(dist); Serial.println(" cm"); }
  }
}
```

**CODI UNITARI ARDUINO SATÈL·LIT I ARDUINO TERRA**

***ARDUINO SATÈL·LIT***
```C
#include <SoftwareSerial.h>

SoftwareSerial mySerial(10, 11); // RX = 10, TX = 11 (igual que en tu código)[cite: 2]

unsigned long ultimoEnvioTest = 0;
const unsigned long intervaloTest = 1000;
unsigned long contadorTest = 0;
bool okRecibido = false;

void setup() {
  Serial.begin(9600);
  mySerial.begin(9600);
  Serial.println("=== TEST CONEXION: ARDUINO SATELITE ===");
}

void loop() {
  // 1. Escuchar mensajes desde Arduino Tierra
  if (mySerial.available() > 0) {
    String msg = mySerial.readStringUntil('\n');
    msg.trim();

    if (msg.length() > 0) {
      Serial.print("[SATELITE] Recibido de Tierra: ");
      Serial.println(msg);

      if (msg == "PING") {
        mySerial.println("PONG");
        Serial.println("[SATELITE] Enviado: PONG");
      } else if (msg == "Ok") {
        okRecibido = true;
      }
    }
  }

  // 2. Enviar mensaje de prueba cada 1 segundo
  if (millis() - ultimoEnvioTest >= intervaloTest) {
    ultimoEnvioTest = millis();
    contadorTest++;

    mySerial.print("TEST:");
    mySerial.println(contadorTest);

    Serial.print("[SATELITE] Enviado: TEST:");
    Serial.print(contadorTest);
    Serial.print(" | Ultimo 'Ok' de Tierra: ");
    Serial.println(okRecibido ? "SI" : "NO");
    okRecibido = false;
  }
  ```
  
***ARDUINO TERRA***
```C
#include <SoftwareSerial.h>

SoftwareSerial mySerial(10, 11); // RX = 10, TX = 11 (igual que en tu código)[cite: 3]

unsigned long ultimoPing = 0;
unsigned long tiempoEnvioPing = 0;
const unsigned long intervaloPing = 2000;
bool esperandoPong = false;

unsigned long paquetesRecibidos = 0;
unsigned long pingsRespondidos = 0;

void setup() {
  Serial.begin(9600);
  mySerial.begin(9600);
  Serial.println("=== TEST CONEXION: ARDUINO TIERRA ===");
}

void loop() {
  // 1. Enviar PING periódico para comprobar ida y vuelta
  if (millis() - ultimoPing >= intervaloPing) {
    ultimoPing = millis();
    tiempoEnvioPing = millis();
    esperandoPong = true;

    mySerial.println("PING");
    Serial.println("[TIERRA] Enviado: PING");
  }

  // 2. Escuchar respuestas y paquetes del Satélite
  if (mySerial.available() > 0) {
    String datos = mySerial.readStringUntil('\n');
    datos.trim();

    if (datos.length() > 0) {
      if (datos == "PONG") {
        pingsRespondidos++;
        unsigned long rtt = millis() - tiempoEnvioPing;
        esperandoPong = false;

        Serial.print("[TIERRA] Recibido PONG (RTT: ");
        Serial.print(rtt);
        Serial.print(" ms) | Total PONGs: ");
        Serial.println(pingsRespondidos);
      } else {
        paquetesRecibidos++;
        Serial.print("[TIERRA] Recibido del Satelite: ");
        Serial.print(datos);
        Serial.print(" | Total paquetes: ");
        Serial.println(paquetesRecibidos);

        // Confirmación igual que en tu código de Tierra[cite: 3]
        mySerial.println("Ok");
      }
    }
  }

  // 3. Avisar si no llega PONG tras 1.5 segundos
  if (esperandoPong && (millis() - tiempoEnvioPing > 1500)) {
    esperandoPong = false;
    Serial.println("[TIERRA] AVISO: Timeout esperando PONG (revisar cableado TX/RX y GND)");
  }
}
```

## VÍDEO
Aquí us adjuntem el nostre vídeo de la VERSIÓ 2: https://drive.google.com/file/d/1EldoWImuvnvYieY3RKaKXQMirU95njrL/view?usp=drivesdk
No ho hem pogut pujar d'una altra manera ja que el vídeo ocupava molt d'espai, disculpin si això fos un inconvenient.
