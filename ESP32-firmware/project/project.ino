#include "SoftwareSerial.h"
#include "DFRobotDFPlayerMini.h"
#include <WiFi.h>
#include <PubSubClient.h>
#include <HTTPClient.h>

int inPIN = 33;
int threshold = 200;
bool started = false;
unsigned long startMillis = 0;
unsigned long currentMillis = 0;
unsigned long timeTaken = 0; 

int samplingRate = 20000; // Default sampling rate (in milliseconds)
bool alarmTriggered = false;
bool audioStarted = false;
unsigned long lastReadingTime = 0;

// Use pins 26 and 27 to communicate with DFPlayer Mini
static const uint8_t PIN_MP3_TX = 26; // Connects to module's RX 
static const uint8_t PIN_MP3_RX = 27; // Connects to module's TX 
SoftwareSerial softwareSerial(PIN_MP3_RX, PIN_MP3_TX);

// WiFi
const char *ssid = "FreakyWifi"; // Enter your WiFi name
const char *password = "xxx";  // Enter WiFi password

// MQTT Broker
const char *mqtt_broker = "192.168.178.25"; // Replace with your local broker IP, e.g., "192.168.1.100"
const char *topic = "esp32/commands";
const char *mqtt_username = "oenarion"; // Replace with your Mosquitto username
const char *mqtt_password = "xxx"; // Replace with your Mosquitto password
const int mqtt_port = 1883;

const char *mqtt_topic_sampling_rate = "esp32/commands/sampling_rate";
const char *mqtt_topic_alarm_trigger = "esp32/commands/trigger_alarm";
const char *mqtt_topic_alarm_stop = "esp32/commands/stop_alarm";

// Create the Player object
DFRobotDFPlayerMini player;
WiFiClient espClient;
PubSubClient client(espClient);

void setup() {
  // Init USB serial port for debugging
  Serial.begin(115200);
  // Init serial port for DFPlayer Mini
  softwareSerial.begin(9600);

  // Connect to WiFi
  connectWiFi();

  // Initialize DFPlayer Mini
  if (!player.begin(softwareSerial)) { 
    Serial.println("DFPlayer Mini not found!");
  } else {
    Serial.println("DFPlayer Mini ready.");
  }    

  // Connect to MQTT broker
  client.setServer(mqtt_broker, mqtt_port);
  client.setCallback(callback);

  reconnectMQTT();  // Ensure MQTT is connected on startup

  // Subscribe to MQTT topics with QoS 1
  client.subscribe(mqtt_topic_sampling_rate, 1);
  client.subscribe(mqtt_topic_alarm_trigger, 1);
  client.subscribe(mqtt_topic_alarm_stop, 1);
}

// WiFi connection function
void connectWiFi() {
  WiFi.begin(ssid, password);
  Serial.println("Connecting to WiFi...");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("Connected to WiFi.");
}

// MQTT reconnect function
void reconnectMQTT() {
  while (!client.connected()) {
    String client_id = "esp32-client-";
    client_id += String(WiFi.macAddress());
    Serial.printf("Connecting to MQTT broker as %s...\n", client_id.c_str());
    
    if (client.connect(client_id.c_str(), mqtt_username, mqtt_password)) {
      Serial.println("Connected to MQTT broker");
    } else {
      Serial.print("MQTT connection failed, state: ");
      Serial.println(client.state());
      delay(2000);
    }
  }
}

void callback(char* topic, byte* payload, unsigned int length) {
  String msg = "";
  for (int i = 0; i < length; i++) {
    msg += (char)payload[i];
  }

  Serial.print("Message arrived on topic: ");
  Serial.println(String(topic));
  Serial.print("Message: ");
  Serial.println(msg);

  if (String(topic) == mqtt_topic_sampling_rate) {
    samplingRate = msg.toInt(); // Update sampling rate
  } else if (String(topic) == mqtt_topic_alarm_trigger) {
    alarmTriggered = true;  // Start alarm
  } else if (String(topic) == mqtt_topic_alarm_stop) {
    alarmTriggered = false;  // Stop alarm
    audioStarted = false;
    if (player.available()) {
      player.stop();  // Stop the player safely
    }
  }
}

void loop() {
  // Ensure WiFi connection
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi disconnected, attempting to reconnect...");
    connectWiFi();
  }

  // Ensure MQTT is connected
  if (!client.connected()) {
    reconnectMQTT();
  }

  // Call client.loop frequently to process incoming MQTT messages
  client.loop();

  unsigned long currentMillis = millis();

  // Sensor data acquisition logic based on sampling rate
  if (currentMillis - lastReadingTime >= samplingRate) {
    lastReadingTime = currentMillis;

    int sensorValue = analogRead(inPIN); // Replace with your sensor pin
    Serial.print("SENSOR VALUE: ");
    Serial.println(sensorValue);

    sendDataToServer(sensorValue);  // Send sensor data to server
  }

  // Alarm control logic
  if (alarmTriggered && !audioStarted) {
    startMillis = millis();
    audioStarted = true;
    Serial.println("Alarm triggered, playing sound...");

    player.volume(20);  // Set volume
    player.play(1);     // Play the first MP3 file
  }

  if (alarmTriggered && (millis() - startMillis > 60000)) {  // Stop after 60 seconds
    player.stop();
    Serial.println("60 SECONDS PASSED! Stopping alarm.");
    alarmTriggered = false;
    audioStarted = false;
    sendAlarmEndToServer();
  }
}

void sendAlarmEndToServer(){
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    
    // Specify the destination URL
    http.begin("http://192.168.178.25:5000/alarm_stopped");  // Replace with your actual server URL
    
    // Send the GET request
    int httpResponseCode = http.GET();
    
    // Check the response code
    if (httpResponseCode > 0) {
      String response = http.getString();  // Get the response payload
      Serial.println(httpResponseCode);    // Print HTTP return code
      Serial.println(response);            // Print the server's response
    } else {
      Serial.print("Error on sending GET: ");
      Serial.println(httpResponseCode);
    }
    
    // End the connection
    http.end();
  }else {
    Serial.println("Error in WiFi connection");
  }
}

void sendDataToServer(int sensorValue) {
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    unsigned long startTime = millis();

    // Send sensor data
    http.begin("http://192.168.178.25:5000/data");  
    http.addHeader("Content-Type", "application/json");

    String postData = "{\"value\": " + String(sensorValue) + ", \"sampling_rate\": " + String(samplingRate) + "}";
    int httpResponseCode = http.POST(postData);

    if (httpResponseCode > 0) {
      String response = http.getString();
      Serial.println(httpResponseCode);
      Serial.println(response);
    } else {
      Serial.print("Error sending data: ");
      Serial.println(httpResponseCode);
    }

    unsigned long endTime = millis();
    timeTaken = endTime - startTime;

    http.end();  // End connection

    // Send time taken
    http.begin("http://192.168.178.25:5000/time");  
    http.addHeader("Content-Type", "application/json");
    postData = "{\"time_taken\": " + String(timeTaken) + "}";
    httpResponseCode = http.POST(postData);

    if (httpResponseCode > 0) {
      String response = http.getString();
      Serial.println(httpResponseCode);
      Serial.println(response);
    } else {
      Serial.print("Error sending time: ");
      Serial.println(httpResponseCode);
    }

    http.end();
  } else {
    Serial.println("WiFi not connected, cannot send data.");
  }
}
