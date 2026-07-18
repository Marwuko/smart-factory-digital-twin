"""Computes OEE (Availability x Performance x Quality) per machine from the event log."""
import sqlite3
import pandas as pd

DB_PATH = "factory.db"
SHIFT_SECONDS = 8 * 3600

IDEAL_CYCLE = {"M1_cutting": 10, "M2_assembly": 12, "M3_packaging": 8}

def compute_oee():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("SELECT * FROM production_events", conn)
    conn.close()

    rows = []
    for machine, g in df.groupby("machine"):
        downtime = g[g.event_type.isin(["BREAKDOWN", "MICROSTOP"])].duration_s.sum()
        run_time = SHIFT_SECONDS - downtime

        ok = (g.event_type == "UNIT_OK").sum()
        defect = (g.event_type == "UNIT_DEFECT").sum()
        total_units = ok + defect

        availability = run_time / SHIFT_SECONDS
        performance = (IDEAL_CYCLE[machine] * total_units) / run_time if run_time > 0 else 0
        quality = ok / total_units if total_units > 0 else 0
        oee = availability * performance * quality

        rows.append({
            "machine": machine,
            "units_total": total_units,
            "units_ok": ok,
            "availability": round(availability, 3),
            "performance": round(performance, 3),
            "quality": round(quality, 3),
            "OEE": round(oee, 3),
        })
    return pd.DataFrame(rows).sort_values("OEE")

def downtime_pareto():
    """Which loss type costs each machine the most time?"""
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("""
        SELECT machine, event_type, COUNT(*) AS events, ROUND(SUM(duration_s)/60, 1) AS minutes_lost
        FROM production_events
        WHERE event_type IN ('BREAKDOWN', 'MICROSTOP')
        GROUP BY machine, event_type
        ORDER BY minutes_lost DESC
    """, conn)
    conn.close()
    return df

if __name__ == "__main__":
    print("=== OEE by Machine (worst first) ===")
    print(compute_oee().to_string(index=False))
    print("\n=== Downtime Pareto ===")
    print(downtime_pareto().to_string(index=False))
