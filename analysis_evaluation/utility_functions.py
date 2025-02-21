import sys
from datetime import datetime, timedelta
from influxdb_client import InfluxDBClient, Point, WritePrecision
import pandas as pd

def get_datetime_start_end():
    start_date = sys.argv[1]
    start_time = sys.argv[2]
    end_date = sys.argv[3]
    end_time = sys.argv[4]

    #influxDB has a different timezone
    start_datetime = datetime.fromisoformat(f"{start_date} {start_time}") - timedelta(hours=2)
    end_datetime = datetime.fromisoformat(f"{end_date} {end_time}") - timedelta(hours=2)

    # Format them for InfluxDB
    start_datetime_str = start_datetime.isoformat() + "Z"  # Add 'Z' for UTC
    end_datetime_str = end_datetime.isoformat() + "Z"  # Add 'Z' for UTC

    print(f"START TIME: {start_datetime}")
    print(f"END TIME: {end_datetime}")
    
    return start_datetime_str, end_datetime_str

def send_query_influx(query, influx_url, influx_token, influx_org):
    influx_client = InfluxDBClient(url=influx_url, token=influx_token, org=influx_org)

    query_api = influx_client.query_api()
    # Execute the query and get the results
    result = query_api.query(org=influx_org, query=query)


    if not result:
        print("No results returned from the query.")
    else:
        print(f"RESULT: {result}")

    data = []
    temp_data = {}

    # Parse the result
    for table in result:
        for record in table.records:
            # Extract the time, field name, and value
            timestamp = record.get_time()
            field_name = record.get_field()  # e.g., 'http_time', 'sampling_rate', etc.
            field_value = record.get_value()
            
            # Use timestamp as a key in temp_data
            if timestamp not in temp_data:
                temp_data[timestamp] = {}
            
            # Store the field value in the dictionary
            temp_data[timestamp][field_name] = field_value


    # Convert temp_data to a list of tuples
    for timestamp, fields in temp_data.items():
        # Ensure all desired fields are present, filling with NaN if not
        row = {
            "timestamp": timestamp,
            "http_time": fields.get("http_time", None),
            "sampling_rate": fields.get("sampling_rate", None),
            "sensor_value": fields.get("sensor_value", None),
            "supposed_to_be_in_bed": fields.get("supposed_to_be_in_bed", None),
            "threshold": fields.get("threshold", None),
            "user_in_bed": fields.get("user_in_bed", None),
        }
        data.append(row)

    # Create a DataFrame from the aggregated data
    df = pd.DataFrame(data)
    
    return df