#!/usr/bin/env python3
import os, psycopg2
from datetime import datetime
from matplotlib import pyplot as plt
from dotenv import load_dotenv

def main():
    load_dotenv()

    PG_USER = os.getenv("PG_USER")
    PG_PASSWORD = os.getenv("PG_PASSWORD")
    PG_DATABASE = os.getenv("PG_DATABASE")
    PG_HOST = os.getenv("PG_HOST")
    PG_PORT = os.getenv("PG_PORT")

    pg_conn = psycopg2.connect(user=PG_USER, password=PG_PASSWORD, database=PG_DATABASE, host=PG_HOST, port=PG_PORT)
    cur = pg_conn.cursor()

    cur.execute("""SELECT ROUND((MAX(processed) - MIN(created))/1000.0,2) AS total_time_sec,
                   ROUND(MAX(processed - created)/1000.0,2) AS max_latency_sec,
                   ROUND(SUM(size/1024.0/1024.0)*8/((MAX(processed) - MIN(created))/1000.0),2) AS throughput_mbps
                   FROM kafka_throughput_metrics""")

    row = cur.fetchone()

    print(f"Total time: {row[0]} sec")
    print(f"Max latency: {row[1]} sec")
    print(f"Throughput: {row[2]} Mbps")

    cur_date = datetime.now().strftime('%Y.%m.%d %H:%M:%S')

    with open(f"report_output/{cur_date}_report.txt", 'a', newline='') as file:
        file.write(f"Total time: {row[0]} sec, Max latency: {row[0]} sec, Throughput: {row[1]} Mbps\n")

    cur.execute("""WITH t AS (
                   SELECT id, 
                   (MAX(processed - created) OVER(ORDER BY id ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW))/1000.0 AS max_latency_sec,
                   (MAX(processed) OVER(ORDER BY id ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)- MIN(created) OVER(ORDER BY id ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW))/1000.0 AS total_time_sec,
                   (SUM(size) OVER(ORDER BY id ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW))/1024.0/1024.0*8
                   /((MAX(processed - created) OVER(ORDER BY id ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW))/1000.0) AS throughput_mbps
                   FROM kafka_throughput_metrics)
                   ,stats AS (
                   SELECT MIN(total_time_sec) AS time_min, MAX(total_time_sec) AS time_max
                   FROM t)
                   SELECT
                   width_bucket(total_time_sec, time_min, time_max + 1, 10) AS bucket,
                   ROUND(MAX(total_time_sec),-1) time_sec,
                   ROUND(MAX(max_latency_sec),-1) AS max_latency_sec,
                   ROUND(MAX(throughput_mbps),1) AS throughput_mbps
                   FROM t, stats
                   GROUP BY bucket
                   ORDER BY bucket""")

    rows = cur.fetchall()
    
    time_sec = [r[1] for r in rows]
    max_latency_sec = [r[2] for r in rows]
    throughput_mbps = [r[3] for r in rows]

    cur.close()
    pg_conn.close()

    plt.subplot(2, 1, 1)
    plt.plot(time_sec, max_latency_sec)
    plt.ylabel('Latency, sec')
    plt.title('Latency and Throughput')

    plt.subplot(2, 1, 2)
    plt.plot(time_sec, throughput_mbps)
    plt.ylabel('Throughput, Mbps')
    plt.xlabel('Time, sec')
    
    plt.savefig(f"report_output/{cur_date}.png")

if __name__ == '__main__':
    main()
