def heat_ledger(result, t=lambda value: value):
    """Animate the net number while preserving the actual saved before/after values."""
    before = float(result["before"]["mean_dt_c"])
    after = float(result["after"]["mean_dt_c"])
    removed = before - after
    scale = max(abs(before), abs(removed), abs(after), 0.01)
    rows = [
        (t("Project adds"), f"+{before:.2f} °C", before, "#ff7a3d"),
        (t("Offsets remove"), f"−{removed:.2f} °C", removed, "#46c4be"),
        (t("Net change"), f"{after:+.2f} °C", abs(after),
         "#ff7a3d" if after > 0.005 else "#46c4be"),
    ]
    markup = """<style>
    body {margin:0;background:transparent;color:#e4ebe9;font-family:Arial,'Noto Sans Malayalam',sans-serif;}
    .heat-ledger {padding:12px 16px;border:1px solid #36504d;border-radius:12px;}
    .heat-ledger-row {display:flex;justify-content:space-between;gap:12px;
                      font-size:15px;line-height:1.5;margin:5px 0;}
    .heat-ledger-track {height:9px;background:#29403d;border-radius:10px;overflow:hidden;}
    .heat-ledger-fill {height:100%;width:var(--ledger-width);background:var(--ledger-color);
                       animation:ledger-fill .9s ease-out both;}
    @keyframes ledger-fill {from {width:0;} to {width:var(--ledger-width);}}
    </style><div class='heat-ledger'>"""
    for i, (label, value, amount, color) in enumerate(rows):
        width = min(100, max(0, amount / scale * 100))
        number_id = " id='net-number'" if i == 2 else ""
        markup += (f"<div class='heat-ledger-row'><span>{label}</span>"
                   f"<strong{number_id} style='color:{color}'>{value}</strong></div>"
                   f"<div class='heat-ledger-track'><div class='heat-ledger-fill' "
                   f"style='--ledger-width:{width:.1f}%;--ledger-color:{color}'></div></div>")
    markup += f"""</div><script>
    const start = {before:.4f}, end = {after:.4f}, duration = 900;
    const output = document.getElementById('net-number');
    const format = value => `${{value >= 0 ? '+' : ''}}${{value.toFixed(2)}} °C`;
    let began;
    function tick(now) {{
      if (began === undefined) began = now;
      const p = Math.min(1, (now - began) / duration);
      const eased = 1 - Math.pow(1 - p, 3);
      output.textContent = format(start + (end - start) * eased);
      if (p < 1) requestAnimationFrame(tick);
    }}
    requestAnimationFrame(tick);
    </script>"""
    return markup
