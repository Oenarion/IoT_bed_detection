# Why?
Traditional alarm clocks can be disruptive. This IoT alarm system can provide a more ubiquitous and non-intrusive waking experience by incorporating bed presence detection.

# ESP 32
The first part of the project involves the ESP32, which is connected to a pressure sensor and a mp3 tf-id module and speaker. This configuration provides an alarm that goes off after a certain pressure is read by the pressure sensor, 
through the use of the speaker. <br>
The **`project.ino`** file handles all the logic which about the device stuff, such as connecting to the WiFi, subscribing to the mqtt broker and sending data to an http server.

# MQTT
The MQTT broker handles the communication between the **data proxy server** and the **esp32** and was deployed using Docker, it can be found in the **`MQTT-broker`** directory, 
this service was used to pass to the ESP32 three possible messages which are:
- sampling_rate, to modify the sampling rate of the pressure sensor (i.e. how often the pressure is read).
- trigger_alarm, to trigger the alarm if the user is still in the bed.
- stop_alarm, to stop the alarm if the user wants it to stop.


# Data proxy server
This server was implemented using Flask and handles most of the task of the project, which are:
- Allows the user to set up specific variables for his alarm through the use of a terminal, here's the detailed list:
  - **set time**: Sets the wake-up time and automatically adjusts the user’s in-bed time based on the current sleeping hours.
  - **set sleeping hours**: Sets the number of sleeping hours and recalibrates the user’s in-bed time according to the wake-up time.
  - **set threshold**: Configures the pressure sensor threshold, with values above the threshold indicating the user is in bed.
  - **set days**: Selects the days on which the alarm should activate.
  - **sampling rate**: Determines the interval (in seconds) between each sample of the pressure sensor taken by the ESP32.
  - **stop alarm**: Stops the alarm if it is currently playing.
  - **show variables**: Displays all the key variables set by the user.
- Receives commmunications from the ESP32 not only using the mqtt protocol, but also using an http connection, the commands supported are:
  - **alarm stopped**: Informs the server that the alarm has sounded for 60 seconds and has stopped.
  - **data**: Sends the current pressure sensor value to the server.
  - **time**: Transmits the duration of the HTTP request for sending pressure data.
- Finally it also sends all the data transmitted from the ESP32 to an InfluxDB instance, after receiving the **time** command.

# InfluxDB
InfluxDB was used as a database to store values such as the pressure sensor value, the http transmission time, the sampling rate, if the user was in bed and other variables.

# Grafana
Grafana was used to display a clear visual interface for metrics such as average sleeping time and all the variables saved in the influxDB instance over time.

# Data analysis module
The data analysis module, namely **`data-analysis.py`**, was used to compute the user's sleep duration based on the pressure sensor data, it takes as input 4 parameters which are:
- start_date
- start_time
- end_date
- end_time
<br> Such that the examination can be done in specific days, the computation is done by taking the values stored in the influxDB instance.

# Data evaluation module
Finally a data evaluation module, namely **`data-evaluation.py`**, was used to compute metrics such as accuracy of the pressure sensor, mean latency of the http request, precision and recall.

# More information
If you want the specific details of the implementations and other details, they can all be found in the **`IoT_project_Galfano.pdf`** file. <br>
Also if you want a presentation with a more comprehensible visualization of the entities which are used take a look at the **`IoT Alarm system with bed presence detection.pdf`** file.
