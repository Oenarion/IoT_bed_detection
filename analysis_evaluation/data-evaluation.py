from datetime import datetime, timedelta
from influxdb_client import InfluxDBClient, Point, WritePrecision
import pandas as pd
import sys
from utility_functions import *
import matplotlib.pyplot as plt

influx_token = "xxx"
influx_org = "galf"
influx_bucket = "evaluation"
influx_url = "http://127.0.0.1:8086"

START_SLEEP = "23:00:00"
END_SLEEP = "07:00:00"

days = [["2024-10-12", "2024-10-13"], ["2024-10-13", "2024-10-14"], ["2024-10-14", "2024-10-15"]]

def compute_mean_latency(df):
    df_latency = df['http_time']
    
    print(df_latency)
    
    mean_latency = df_latency.mean()
    
    print(f"MEAN LATENCY: {mean_latency}")
    
    
def is_asleep(timestamp):
    
    start_sleep_dt = pd.to_datetime(START_SLEEP).time()  # 11:00 PM
    end_sleep_dt = pd.to_datetime(END_SLEEP).time()  # 7:00 AM
    # Get the time from the timestamp
    current_time = timestamp.time()
    # Check if the current time is within the sleep period
    if start_sleep_dt < end_sleep_dt:  # Normal case: 11 PM to 7 AM
        return start_sleep_dt <= current_time or current_time < end_sleep_dt
    else:  # Edge case: sleep overlaps midnight
        return current_time >= start_sleep_dt or current_time < end_sleep_dt



def compute_accuracy(df):
    total_entries = len(df)
    
    TP = len(df[(df['user_in_bed'] > 0) & (df['asleep'] == True)])
    TN = len(df[(df['user_in_bed'] == 0) & (df['asleep'] == False)])

    print(f"Total Entries: {total_entries}, True Positives: {TP}, True Negatives: {TN}")
    
    if TP+TN == 0:
        return 0
    
    acc = ((TP + TN) / total_entries) * 100
    
    return acc

def compute_single_day_accuracy(df, start_date, end_date):
    # Filter the DataFrame for the specified date range
    df_filtered = df[(df['timestamp'].dt.date >= pd.to_datetime(start_date).date()) &
                     (df['timestamp'].dt.date <= pd.to_datetime(end_date).date())]

    # Check if the timestamps fall within the sleeping hours
    df_filtered['asleep'] = df_filtered['timestamp'].apply(is_asleep)

    total_entries = len(df_filtered)
    
    TP = len(df_filtered[(df_filtered['user_in_bed'] > 0) & (df_filtered['asleep'] == True)])
    TN = len(df_filtered[(df_filtered['user_in_bed'] == 0) & (df_filtered['asleep'] == False)])

    print(f"Total Entries: {total_entries}, True Positives: {TP}, True Negatives: {TN}")
    
    if TP + TN == 0:
        return 0
    
    acc = ((TP + TN) / total_entries) * 100
    
    return acc

def compute_single_day_precision(df, start_date, end_date):
    # Filter the DataFrame for the specified date range
    df_filtered = df[(df['timestamp'].dt.date >= pd.to_datetime(start_date).date()) &
                     (df['timestamp'].dt.date <= pd.to_datetime(end_date).date())]

    # Check if the timestamps fall within the sleeping hours
    df_filtered['asleep'] = df_filtered['timestamp'].apply(is_asleep)

    total_entries = len(df_filtered)
    
    # Use df_filtered for TP and FP calculations
    TP = len(df_filtered[(df_filtered['user_in_bed'] > 0) & (df_filtered['asleep'] == True)])
    FP = len(df_filtered[(df_filtered['user_in_bed'] > 0) & (df_filtered['asleep'] == False)])
    
    print(f"Total Entries: {total_entries}, True Positives: {TP}, False Positives: {FP}")
    
    if TP + FP == 0:
        return 0
    
    precision = (TP / (TP + FP)) * 100
    
    return precision

def compute_single_day_recall(df, start_date, end_date):
    # Filter the DataFrame for the specified date range
    df_filtered = df[(df['timestamp'].dt.date >= pd.to_datetime(start_date).date()) &
                     (df['timestamp'].dt.date <= pd.to_datetime(end_date).date())]

    # Check if the timestamps fall within the sleeping hours
    df_filtered['asleep'] = df_filtered['timestamp'].apply(is_asleep)

    total_entries = len(df_filtered)
    
    # Use df_filtered for TP and FN calculations
    TP = len(df_filtered[(df_filtered['user_in_bed'] > 0) & (df_filtered['asleep'] == True)])
    FN = len(df_filtered[(df_filtered['user_in_bed'] == 0) & (df_filtered['asleep'] == True)])
    
    print(f"Total Entries: {total_entries}, True Positives: {TP}, False Negatives: {FN}")
    
    if TP + FN == 0:
        return 0
    
    recall = (TP / (TP + FN)) * 100  # Fix the variable name from precision to recall
    
    return recall


def compute_precision(df):
    
    TP = len(df[(df['user_in_bed'] > 0) & (df['asleep'] == True)])
    FP = len(df[(df['user_in_bed'] > 0) & (df['asleep'] == False)])
    
    if TP+FP == 0:
        return 0
    
    precision = (TP/(TP+FP)) * 100
    
    return precision

def compute_recall(df):
    
    TP = len(df[(df['user_in_bed'] > 0) & (df['asleep'] == True)])
    FN = len(df[(df['user_in_bed'] == 0) & (df['asleep'] == True)])
    
    if TP+FN == 0:
        return 0
    
    precision = (TP/(TP+FN)) * 100
    
    return precision

def compute_fpr(df):
    TP = len(df[(df['user_in_bed'] > 0) & (df['asleep'] == True)])
    FN = len(df[(df['user_in_bed'] == 0) & (df['asleep'] == True)])
    
    if TP+FN == 0:
        return 0
    
    precision = (FN/(TP+FN)) * 100
    
    return precision


def compute_pr_curve(df):
    thresholds = [20 * i for i in range(40)]
    
    precs = []
    recs = []
    
    for thresh in thresholds:
        df_filtered = df.copy()
        
        # Use .loc for setting values
        df_filtered.loc[df_filtered['sensor_value'] >= thresh, 'user_in_bed'] = 1
        
        # Assuming you have functions defined to compute recall and false positive rate
        recs.append(compute_recall(df_filtered))
        precs.append(compute_precision(df_filtered))
        

    # Plot the ROC curve
    plt.plot(recs, precs, marker='o')
    plt.xlabel('Recall')
    plt.ylabel('Precision')
    plt.title(f'Precision Recall Curve')
    plt.grid()
    plt.show()  # Show the plot
    


def main():
    
    query = f'''from(bucket: "evaluation")
    |> range(start: -365d)
    |> filter(fn: (r) => r["_measurement"] == "pressure_sensor")
    |> filter(fn: (r) => r["_field"] == "threshold" or r["_field"] == "supposed_to_be_in_bed" or r["_field"] == "sensor_value" or r["_field"] == "sampling_rate" or r["_field"] == "http_time" or r["_field"] == "user_in_bed")
    |> filter(fn: (r) => r["user_id"] == "esp32-galf")
    |> yield(name: "last")
    '''
    
    df = send_query_influx(query,influx_url,influx_token, influx_org)
    
    compute_mean_latency(df)

    df['asleep'] = df['timestamp'].apply(is_asleep)

    
    #df_sleep_time = df[df['asleep'] == True]
    acc = compute_accuracy(df)
    print(f"ACCURACY FOR THE WHOLE PROCESS: {acc:.1f} %")
    precision = compute_precision(df)
    print(f"PRECISION FOR THE WHOLE PROCESS: {precision:.1f} %")
    recall = compute_recall(df)
    print(f"RECALL FOR THE WHOLE PROCESS: {recall:.1f} %")
    
    for day in days:
        start_date, end_date = day
        acc = compute_single_day_accuracy(df, start_date, end_date)
        prec = compute_single_day_precision(df, start_date, end_date)
        rec = compute_single_day_recall(df, start_date, end_date)
        print(f"ACCURACY FOR {start_date} TO {end_date}: {acc:.1f} %")
        print(f"PRECISION FOR {start_date} TO {end_date}: {prec:.1f} %")
        print(f"RECALL FOR {start_date} TO {end_date}: {rec:.1f} %")
        
    compute_pr_curve(df)
    
if __name__ == '__main__':
    main()