import gradio as gr
import pandas as pd
import sqlite3
import plotly.express as px
import plotly.graph_objects as go
import spaces

@spaces.GPU
def gpu_placeholder():
    # ZeroGPU requires one @spaces.GPU function; this dashboard is CPU-only.
    return "ok"

SHIFT_SECONDS = 8 * 3600
IDEAL_CYCLE = {"M1_cutting": 10, "M2_assembly": 12, "M3_packaging": 8}

def compute():
    conn = sqlite3.connect("factory.db")
    df = pd.read_sql("SELECT * FROM production_events", conn)
    conn.close()

    rows = []
    for machine, g in df.groupby("machine"):
        downtime = g[g.event_type.isin(["BREAKDOWN", "MICROSTOP"])].duration_s.sum()
        run_time = SHIFT_SECONDS - downtime
        ok = (g.event_type == "UNIT_OK").sum()
        defect = (g.event_type == "UNIT_DEFECT").sum()
        total = ok + defect
        a = run_time / SHIFT_SECONDS
        p = (IDEAL_CYCLE[machine] * total) / run_time if run_time else 0
        q = ok / total if total else 0
        rows.append({"machine": machine, "availability": a, "performance": p,
                     "quality": q, "OEE": a * p * q, "units": total, "defects": defect})
    oee = pd.DataFrame(rows).sort_values("OEE")

    downtime = df[df.event_type.isin(["BREAKDOWN", "MICROSTOP"])].groupby(
        ["machine", "event_type"]).duration_s.sum().div(60).reset_index(name="minutes_lost")
    return oee, downtime

def build_dashboard():
    oee, downtime = compute()

    worst = oee.iloc[0]
    summary = (
        f"## 🏭 Line OEE: {oee.OEE.mean():.1%} &nbsp;|&nbsp; "
        f"Bottleneck: **{worst.machine}** ({worst.OEE:.1%})\n"
        f"Units produced: {int(oee.units.sum())} &nbsp;|&nbsp; Defects: {int(oee.defects.sum())}"
    )

    gauges = go.Figure()
    for i, r in enumerate(oee.sort_values("machine").itertuples()):
        gauges.add_trace(go.Indicator(
            mode="gauge+number", value=r.OEE * 100,
            title={"text": r.machine},
            gauge={"axis": {"range": [0, 100]},
                   "bar": {"color": "green" if r.OEE > 0.75 else "orange" if r.OEE > 0.6 else "red"},
                   "threshold": {"line": {"color": "black"}, "value": 85}},
            domain={"row": 0, "column": i}))
    gauges.update_layout(grid={"rows": 1, "columns": 3}, height=300,
                         title="OEE by Machine (target: 85%)")

    melted = oee.melt(id_vars="machine", value_vars=["availability", "performance", "quality"])
    fig_factors = px.bar(melted, x="machine", y="value", color="variable", barmode="group",
                         title="OEE Factors Breakdown", range_y=[0, 1])

    fig_downtime = px.bar(downtime, x="machine", y="minutes_lost", color="event_type",
                          title="Downtime by Cause (minutes)")

    return summary, gauges, fig_factors, fig_downtime

with gr.Blocks(title="Smart Factory Digital Twin") as demo:
    gr.Markdown("# 🏭 Smart Factory Digital Twin — Live OEE Dashboard")
    summary_md = gr.Markdown()
    gauge_plot = gr.Plot()
    with gr.Row():
        factors_plot = gr.Plot()
        downtime_plot = gr.Plot()
    demo.load(build_dashboard, outputs=[summary_md, gauge_plot, factors_plot, downtime_plot])

demo.launch()
