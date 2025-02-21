from flask import Flask, request, jsonify
import paho.mqtt.client as mqtt
import threading
from datetime import datetime, timedelta
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
import time

# Setup Flask app
app = Flask(__name__)


# TARGET TIME
START_SLEEP_TIME = "23:00:00"
TARGET_TIME = "7:00:00" 
SLEEPING_HOURS = 8
TARGET_DAYS = [0,1,2,3,4,5,6]
THRESHOLD = 120
SENSOR_VALUE = -1
SAMPLING_RATE = 5000

days_map = {
    0:'Mon',
    1:'Tue',
    2:'Wed',
    3:'Thu',
    4:'Fri',
    5:'Sat',
    6:'Sun'
}

alarm_triggered = False


# MQTT broker settings
mqtt_broker = "localhost"
mqtt_topic = "esp32/commands"
mqtt_username = "oenarion"  # Replace with your MQTT username
mqtt_password = "xxx"  # Replace with your MQTT password
mqtt_client = mqtt.Client()

# InfluxDB settings
influx_token = "xxx"
influx_org = "galf"
influx_bucket = "evaluation"
influx_url = "http://127.0.0.1:8086"

influx_client = InfluxDBClient(url=influx_url, token=influx_token, org=influx_org)

# MQTT client setup
def on_connect(client, userdata, flags, rc):
    print(f"Connected to MQTT broker with code {rc}")

mqtt_client.on_connect = on_connect
# Set the username and password for the MQTT broker
mqtt_client.username_pw_set(mqtt_username, mqtt_password)
mqtt_client.connect(mqtt_broker, 1883, 60)

from datetime import datetime, timedelta

def check_time():
    """Background task that checks the time every second and triggers a POST request."""
    global alarm_triggered

    while True:
        try:
            # Get the current time as a datetime object
            current_time = datetime.now().strftime("%H:%M:%S")
            day_of_week = datetime.today().weekday()

            # Check if the alarm should trigger
            if current_time == TARGET_TIME and day_of_week in TARGET_DAYS and not alarm_triggered and SENSOR_VALUE >= THRESHOLD:
                print("Target time reached! Triggering alarm.")
                trigger_alarm()  # Call the function directly instead of making a POST request
                alarm_triggered = True
                
            time.sleep(1)  # Check every second
        except Exception as e:
            print(f"Error in time check: {e}")
        
def get_datetime():
    now = datetime.now()
    
    # Return the current time and the day of the week (0 = Monday, 6 = Sunday)
    return now.time(), now.weekday()  # Use weekday() for day of the week

@app.route('/alarm_stopped', methods=['GET'])
def alarm_update():
    global alarm_triggered
    
    alarm_triggered = False
    print("60 SECONDS PASSED, ALARM RESETTED!")
    return jsonify({"status": "success"}), 200

## THIS ALSO CHECKS FOR THRESHOLD, TIME TAKEN FOR THE REQUEST
## THRESHOLD WILL TELL US IF WE HAVE HAD A DETECTION OR NOT
@app.route('/data', methods=['POST'])
def receive_data():
    global SENSOR_VALUE, SAMPLING_RATE
    
    data = request.json
    SENSOR_VALUE = data.get('value')
    SAMPLING_RATE = data.get('sampling_rate')
    print(f"SENSOR DATA: {SENSOR_VALUE}, SAMPLING RATE: {SAMPLING_RATE}")

    return jsonify({"status": "success"}), 200

@app.route('/time', methods=['POST'])
def receive_time():
    global SENSOR_VALUE
    if SENSOR_VALUE != -1:
        user_in_bed = False
        sleeping = False
        
        data = request.json
        time_taken = data.get('time_taken')
        print(f"TIME TAKEN: {time_taken}")
        
        if SENSOR_VALUE >= THRESHOLD:
            user_in_bed = True
        
        format = '%H:%M:%S'
        start_sleep = datetime.strptime(START_SLEEP_TIME, format).time()
        end_sleep = datetime.strptime(TARGET_TIME, format).time()
        
        current_time, day_of_week = get_datetime()
        if day_of_week in TARGET_DAYS:
            if start_sleep < end_sleep:  # Normal case (same day)
                print("same day")
                print(f"START: {start_sleep}, END: {end_sleep}")
                sleeping = start_sleep <= current_time <= end_sleep
            else:  # Overnight case (spanning across midnight)
                print("diff day")
                print(f"START: {start_sleep}, END: {end_sleep}")
                sleeping = current_time >= start_sleep or current_time <= end_sleep

        
        print(f"USER IN BED: {user_in_bed}")
        print(f"USER IS IN SLEEPING HOURS: {sleeping}")
        print(f"ALARM TRIGGERED: {alarm_triggered}")
        
        # Send data to InfluxDB
        write_api = influx_client.write_api()
        
        user_in_bed_int = int(user_in_bed)
        sleeping_int = int(sleeping)
        
        # print(type(SENSOR_VALUE), type(THRESHOLD), type(time_taken), type(user_in_bed_int), type(sleeping_int))
        # print(SENSOR_VALUE, THRESHOLD, time_taken, user_in_bed_int, sleeping_int)
            
        try:
            write_api.write(bucket=influx_bucket, org=influx_org, record=[{ 'measurement': 'pressure_sensor',
                'tags': {'user_id': 'esp32-galf'},
                'fields': {'sensor_value': SENSOR_VALUE, 
                           'threshold': THRESHOLD,
                           'http_time': time_taken,
                           'user_in_bed': user_in_bed_int,
                           'supposed_to_be_in_bed':sleeping_int,
                           'sampling_rate': SAMPLING_RATE},
        }])
            print("Write operation successful.")
        except Exception as e:
            print(f"Write operation failed: {e}")
            
        
        return jsonify({"status": "success"}), 200
    else:
        print("Something went wrong!")
        
        return jsonify({"status": "rejected" }), 400


@app.route('/set_time', methods=['POST'])
def set_wake_up_hour():
    global TARGET_TIME, START_SLEEP_TIME, SLEEPING_HOURS
    if not request.json:
        return jsonify({"error": "Invalid JSON data"}), 400

    time = request.json.get('time')
    
    # Ensure the time is in the correct format
    try:
        format = '%H:%M:%S'
        # Parse the new time
        wake_up_hour = datetime.strptime(time, format)
    except ValueError:
        return jsonify({"error": "Badly formatted time!"}), 400

    # Update TARGET_TIME
    TARGET_TIME = time

    # Update START_SLEEP_TIME based on the new TARGET_TIME and SLEEPING_HOURS
    sleep_hour = wake_up_hour - timedelta(hours=SLEEPING_HOURS)
    START_SLEEP_TIME = sleep_hour.strftime('%H:%M:%S')

    print(f"UPDATE TIME WITH VALUE: {TARGET_TIME}")
    print(f"NEW USER SLEEP SCHEDULE: {START_SLEEP_TIME} to {wake_up_hour.strftime('%H:%M:%S')}")

    return jsonify({"status": "success", "time": TARGET_TIME}), 200

    
@app.route('/set_sleeping_hours', methods=['POST'])
def set_sleeping_hours():
    global SLEEPING_HOURS, START_SLEEP_TIME
    if not request.json:
        return jsonify({"error": "Invalid JSON data"}), 400

    SLEEPING_HOURS = request.json.get('sleep_time')

    print(f"UPDATED SLEEPING HOURS WITH VALUE: {SLEEPING_HOURS}")
    format = '%H:%M:%S'
    wake_up_hour = datetime.strptime(TARGET_TIME, format)
    sleep_hour = wake_up_hour - timedelta(hours=SLEEPING_HOURS)
    
    # Now print only the time (not date) using strftime
    sleep_time_str = sleep_hour.strftime('%H:%M:%S')
    wake_up_time_str = wake_up_hour.strftime('%H:%M:%S')
    
    START_SLEEP_TIME = sleep_time_str
    print(f"NEW USER SLEEP SCHEDULE: {sleep_time_str} to {wake_up_time_str}")
    
    return jsonify({"status": "success", "sleeping_hours": SLEEPING_HOURS}), 200

@app.route('/set_threshold', methods=['POST'])
def set_threshold():
    global THRESHOLD
    if not request.json:
        return jsonify({"error": "Invalid JSON data"}), 400

    THRESHOLD = request.json.get('threshold')
    
    print(f"UPDATE THRESHOLD WITH VALUE: {THRESHOLD}")
    
    return jsonify({"status": "success", "threshold": THRESHOLD}), 200

@app.route('/set_days', methods=['POST'])
def set_days():
    global TARGET_DAYS
    if not request.json:
        return jsonify({"error": "Invalid JSON data"}), 400
    
    if type(request.json.get('days')) == list:
        TARGET_DAYS = request.json.get('days')
    else:
        print("wrong type")
        
    print(f"UPDATED DAYS TO RING THE ALARM: {TARGET_DAYS}")
    
    return jsonify({"status": "success", "threshold": TARGET_DAYS}), 200

@app.route('/sampling_rate', methods=['POST'])
def set_sampling_rate():
    if not request.json:
        return jsonify({"error": "Invalid JSON data"}), 400

    time = request.json.get('sampling_rate')
    if not time:
        return jsonify({"error": "Missing 'sampling_rate' parameter"}), 400
    
    if time <= 2000:
        return jsonify({"error": "Sampling rate should be more than 2000s to make up for incosistencies..."}), 400
    # Send the command to ESP32 via MQTT
    mqtt_client.publish(mqtt_topic+"/sampling_rate", f"{time}")

    return jsonify({"status": "sampling_rate", "time": time}), 200

#@app.route('/trigger_alarm', methods=['POST'])
def trigger_alarm():
    # Send trigger alarm command to ESP32
    mqtt_client.publish(mqtt_topic+"/trigger_alarm", "STARTING ALARM")
    print("ALARM TRIGGERED")  
 #   return jsonify({"status": "alarm_triggered"}), 200

@app.route('/stop_alarm', methods=['GET'])
def stop_alarm():
    global alarm_triggered
    # Send stop alarm command to ESP32
    mqtt_client.publish(mqtt_topic+"/stop_alarm", "STOPPING ALARM")
    alarm_triggered = False
    
    return jsonify({"status": "alarm_stopped"}), 200

@app.route('/show_variables', methods=['GET'])
def show_variables():
    
    time_format = "%H:%M:%S"
    
    target_time = datetime.strptime(TARGET_TIME, time_format).time()
    start_sleep_time = datetime.strptime(START_SLEEP_TIME, time_format).time()
    current_time = datetime.now().time()
    day_of_week = days_map[datetime.today().weekday()]
    
    str_days = []
    for day in TARGET_DAYS:
        str_days.append(days_map[day])
        
    print(f"Current time: {current_time}, DAY OF THE WEEK: {day_of_week}")
    print(f"Alarm triggered: {alarm_triggered}")
    print(f"SENSOR VALUE: {SENSOR_VALUE}")
    print(f"SLEEP HOURS: {SLEEPING_HOURS}")
    print(f"TARGET DAYS: {str_days}")
    print(f"Current boundaries: {START_SLEEP_TIME} - {TARGET_TIME}")
    if start_sleep_time < target_time:  # Normal case (same day)
        is_in_sleeping_hours = start_sleep_time <= current_time <= target_time
    else:  # Overnight case (spanning across midnight)
        is_in_sleeping_hours = current_time >= start_sleep_time or current_time <= target_time
    
    print(f"IS THE USER IN SLEEPING HOURS: {is_in_sleeping_hours}")
    

    return jsonify({"status": "accepted"}), 200

if __name__ == '__main__':
    mqtt_client.loop_start()  # Start MQTT client loop in the background
    time_check_thread = threading.Thread(target=check_time)
    time_check_thread.daemon = True  # Allows the thread to exit when the main program exits
    time_check_thread.start()
    app.run(host='0.0.0.0', port=5000)  # Run Flask app
