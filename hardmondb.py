import sqlite3
import json
from datetime import datetime

def init(filename):
    conn = sqlite3.connect(filename)
    with conn:
        conn.execute("""
CREATE TABLE IF NOT EXISTS stats (
    [id] INTEGER PRIMARY KEY AUTOINCREMENT,
    [cpu_load] REAL,
    [cpu_temp] REAL,
    [gpu_load] REAL,
    [vram_load] REAL,
    [average_gpu] REAL,
    [mem_used] INTEGER,
    [mem_available] INTEGER,
    [data] TEXT NOT NULL,
    [ts] DATETIME DEFAULT CURRENT_TIMESTAMP
)       """)

    return conn

def add_stats(conn, stats):
    statsstr = json.dumps(stats)
    params = (
        stats.get("cpu_load"),
        stats.get("cpu_temp"),
        stats.get("gpu_load"),
        stats.get("vram_load"),
        stats.get("average_gpu"),
        stats.get("mem_used"),
        stats.get("mem_available"),
        statsstr
    )
    with conn:
        conn.execute("""
INSERT INTO stats
    (cpu_load, cpu_temp, gpu_load, vram_load,
    average_gpu, mem_used, mem_available, data)
VALUES
    (?, ?, ?, ?, ?, ?, ?, ?)
        """, params)

def load_avg(conn, windows):
    rowstrs = []
    for window in windows:
        winstr = f"-{window}"
        with conn:
            cur = conn.execute("""
SELECT
    avg(cpu_load), avg(gpu_load), avg(vram_load),
    avg(average_gpu), avg(mem_used), avg(mem_available)
FROM stats 
WHERE ts > DATETIME('now', ?) 
            """, (winstr,))
            row = cur.fetchone()
            rowstr = f"{fmtwindow(window)} - cpu_load: {fmtload(row[0])} | gpu_load: {fmtload(row[1])} | vram_load: {fmtload(row[2])}"
            rowstrs.append(rowstr)

    now = datetime.now()
    nowstr = now.strftime("%Y%m%d %H%M%S ")
    border = "=" * (len(rowstrs[0]) - len(nowstr))
    print(f"{nowstr}{border}")
    for row in rowstrs:
        print(row)

def fmtload(load):
    return f"{load:.2f}".rjust(5)

def fmtwindow(window):
    return f"{window}".rjust(11)