from datetime import datetime, timedelta
from influxdb_client import InfluxDBClient, Point, WritePrecision
import pandas as pd
import sys
from utility_functions import *

influx_token = "xxx"
influx_org = "galf"
influx_bucket = "evaluation"
influx_url = "http://127.0.0.1:8086"

if len(sys.argv) != 5:
    print("GIVE START DATE AND END DATE FOR SLEEPING EVALUATION!")
    
# DATE IS YYYY-MM-DD
# TIME IS HH:MM:SS
start_date = sys.argv[1]
start_time = sys.argv[2]
end_date = sys.argv[3]
end_time = sys.argv[4]


def compute_time(df):
    # Set the timestamp as the index
    df.set_index("timestamp", inplace=True)

    print(df)
    # Print the DataFrame
    print(len(df))

    print(df.columns)
    # Filter rows where user is in bed and should be in bed
    df_filtered = df[(df['user_in_bed'] == 1) & (df['supposed_to_be_in_bed'] == 1)]
    print(len(df_filtered))

    total_seconds = (df_filtered["sampling_rate"].sum())/1000

    m, s = divmod(total_seconds, 60)
    h, m = divmod(m, 60)
    print(f"Total sleep time: {h} hours, {m} minutes and {s} seconds")

def main():
    start_datetime_str, end_datetime_str = get_datetime_start_end()
    
    query = f'''from(bucket: "evaluation")
    |> range(start: {start_datetime_str}, stop: {end_datetime_str})
    |> filter(fn: (r) => r["_measurement"] == "pressure_sensor")
    |> filter(fn: (r) => r["_field"] == "threshold" or r["_field"] == "supposed_to_be_in_bed" or r["_field"] == "sensor_value" or r["_field"] == "sampling_rate" or r["_field"] == "http_time" or r["_field"] == "user_in_bed")
    |> filter(fn: (r) => r["user_id"] == "esp32-galf")
    |> yield(name: "last")
    '''
    
    df = send_query_influx(query,influx_url,influx_token, influx_org)
    
    compute_time(df)
    
if __name__ == '__main__':
    main()