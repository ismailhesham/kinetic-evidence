"""Charts from script numbers only (no invented data)."""
from __future__ import annotations
import re
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

NUM_RE = re.compile(r"(-?\d[\d,]*(?:\.\d+)?)")
YEAR_RE = re.compile(r"\b(19\d{2}|20\d{2})\b")

def _numbers(text):
    vals = []
    for m in NUM_RE.finditer(text):
        try:
            vals.append(float(m.group(1).replace(",", "")))
        except ValueError:
            continue
    return vals

def render_chart(narration: str, out_path: str, w=1280, h=720) -> dict:
    vals = _numbers(narration)
    if len(vals) < 1:
        return {"ok": False, "reason": "insufficient_data"}

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    
    # 1. Detect Chart Type
    chart_type = "bar"
    low = narration.lower()
    years = YEAR_RE.findall(narration)
    
    if "%" in narration or "percent" in low:
        chart_type = "pie"
    elif len(years) >= 2:
        chart_type = "line"  # Timeline / trend
    elif "vs" in low or "versus" in low or "compared" in low:
        chart_type = "comparison"
        
    # 2. Setup Matplotlib
    fig, ax = plt.subplots(figsize=(w / 100, h / 100), dpi=100)
    fig.patch.set_facecolor("#0f1216")
    ax.set_facecolor("#0f1216")
    ax.tick_params(colors="#cfd6df")
    for spine in ax.spines.values():
        spine.set_color("#2b333e")

    # 3. Render based on type
    if chart_type == "pie" and len(vals) >= 2:
        ax.pie(vals[:5], labels=[f"{v}%" for v in vals[:5]], 
               colors=["#4f9dff", "#ff6b6b", "#50d890", "#f9ca24", "#a29bfe"],
               textprops={'color': "w"})
        ax.set_facecolor("#0f1216")
        
    elif chart_type == "line" and len(vals) >= 2:
        labels = years[:len(vals)] if len(years) == len(vals) else [f"T{i}" for i in range(len(vals))]
        ax.plot(labels, vals, color="#4f9dff", marker="o", linewidth=4, markersize=8)
        ax.fill_between(labels, vals, color="#4f9dff", alpha=0.2)
        ax.set_ylim(0, max(vals) * 1.2)
        
    elif chart_type == "comparison" and len(vals) >= 2:
        labels = ["Item A", "Item B"] if len(vals) == 2 else [f"Item {i+1}" for i in range(len(vals))]
        colors = ["#4f9dff" if v == max(vals) else "#555" for v in vals]
        ax.barh(labels, vals, color=colors)
        ax.set_xlim(0, max(vals) * 1.2)
        
    elif len(vals) >= 2:
        labels = [f"#{i+1}" for i in range(len(vals))]
        ax.bar(labels, vals, color="#4f9dff")
        ax.set_ylim(0, max(vals) * 1.1)
        
    else:
        # Single number fallback (Data Card style)
        ax.text(0.5, 0.5, f"{vals[0]:g}", color="#ffffff",
                fontsize=100, ha="center", va="center", transform=ax.transAxes)
        ax.set_axis_off()

    fig.tight_layout()
    fig.savefig(out_path, facecolor=fig.get_facecolor())
    plt.close(fig)
    
    return {
        "ok": True, 
        "path": out_path, 
        "n_values": len(vals),
        "chart_type_detected": chart_type
    }