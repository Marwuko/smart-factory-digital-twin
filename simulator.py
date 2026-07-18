"""Simulates a 3-machine production line, logging events to SQLite."""
import sqlite3, random
from datetime import datetime, timedelta

DB_PATH = "factory.db"
SHIFT_HOURS = 8

MACHINES = {
    "M1_cutting":   {"ideal_cycle_s": 10, "breakdown_p": 0.0005, "microstop_p": 0.010, "defect_p": 0.02},
    "M2_assembly":  {"ideal_cycle_s": 12, "breakdown_p": 0.0010, "microstop_p": 0.015, "defect_p": 0.04},
    "M3_packaging": {"ideal_cycle_s": 8,  "breakdown_p": 0.0003, "microstop_p": 0.008, "defect_p": 0.01},
}

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""CREATE TABLE IF NOT EXISTS production_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        machine TEXT NOT NULL,
        event_type TEXT NOT NULL,   -- UNIT_OK / UNIT_DEFECT / BREAKDOWN / REPAIR / MICROSTOP
        duration_s REAL             -- for stops: how long production was lost
    )""")
    conn.commit()
    return conn

def simulate_shift(start_time=None):
    conn = init_db()
    start = start_time or datetime.now().replace(hour=8, minute=0, second=0, microsecond=0)

    for name, cfg in MACHINES.items():
        t = start
        shift_end = start + timedelta(hours=SHIFT_HOURS)
        while t < shift_end:
            r = random.random()
            if r < cfg["breakdown_p"]:
                downtime = random.uniform(600, 2400)          # 10-40 min repair
                conn.execute("INSERT INTO production_events (timestamp, machine, event_type, duration_s) VALUES (?,?,?,?)",
                             (t.isoformat(), name, "BREAKDOWN", downtime))
                t += timedelta(seconds=downtime)
                conn.execute("INSERT INTO production_events (timestamp, machine, event_type, duration_s) VALUES (?,?,?,?)",
                             (t.isoformat(), name, "REPAIR", 0))
            elif r < cfg["breakdown_p"] + cfg["microstop_p"]:
                stop = random.uniform(20, 90)                  # brief jam / adjustment
                conn.execute("INSERT INTO production_events (timestamp, machine, event_type, duration_s) VALUES (?,?,?,?)",
                             (t.isoformat(), name, "MICROSTOP", stop))
                t += timedelta(seconds=stop)
            else:
                cycle = cfg["ideal_cycle_s"] * random.uniform(1.0, 1.25)  # real cycles run a bit slow
                t += timedelta(seconds=cycle)
                event = "UNIT_DEFECT" if random.random() < cfg["defect_p"] else "UNIT_OK"
                conn.execute("INSERT INTO production_events (timestamp, machine, event_type, duration_s) VALUES (?,?,?,?)",
                             (t.isoformat(), name, event, None))
    conn.commit()
    conn.close()
    print(f"Simulated {SHIFT_HOURS}h shift for {len(MACHINES)} machines -> {DB_PATH}")

if __name__ == "__main__":
    simulate_shift()
