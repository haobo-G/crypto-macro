# -*- coding: utf-8 -*-
"""
???? x ????????? ? Web ??
??: ??? index.html??? base64 ???????????
"""

import base64
import io
import sys
from datetime import datetime, timedelta

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.font_manager as fm
import seaborn as sns
import pandas as pd
import yfinance as yf

def _setup_font():
    candidates = ["Noto Sans CJK SC", "WenQuanYi Micro Hei",
                  "Microsoft YaHei", "SimHei", "PingFang SC"]
    available = {f.name for f in fm.fontManager.ttflist}
    for font in candidates:
        if font in available:
            plt.rcParams["font.family"] = font
            return

_setup_font()
plt.rcParams["axes.unicode_minus"] = False

TICKERS = {
    "BTC": "BTC-USD", "ETH": "ETH-USD",
    "SPX": "^GSPC",   "NDX": "^IXIC",
    "VIX": "^VIX",    "TNX": "^TNX",
}
LABELS = {
    "BTC": "Bitcoin", "ETH": "Ethereum",
    "SPX": "S&P 500", "NDX": "Nasdaq",
    "VIX": "VIX",     "TNX": "10Y UST",
}
LABELS_ZH = {
    "BTC": "Bitcoin",  "ETH": "Ethereum",
    "SPX": "S&P 500",  "NDX": "Nasdaq",
    "VIX": "VIX",      "TNX": "10Y Bond",
}
CORR_DESC = [
    (0.7,  1.01, "Strong +"),
    (0.4,  0.7,  "Moderate +"),
    (0.1,  0.4,  "Weak +"),
    (-0.1, 0.1,  "Neutral"),
    (-0.4, -0.1, "Weak -"),
    (-0.7, -0.4, "Moderate -"),
    (-1.01,-0.7, "Strong -"),
]

CORR_DESC_ZH = {
    "Strong +":   "????",
    "Moderate +": "?????",
    "Weak +":     "????",
    "Neutral":    "?????",
    "Weak -":     "????",
    "Moderate -": "?????",
    "Strong -":   "????",
}

def describe_corr(v):
    for lo, hi, label in CORR_DESC:
        if lo <= v < hi:
            return CORR_DESC_ZH.get(label, label)
    return ""

def fetch_data(days=100):
    end = datetime.today()
    start = end - timedelta(days=days + 14)
    frames = {}
    for name, ticker in TICKERS.items():
        for _ in range(3):
            try:
                df = yf.download(ticker,
                                 start=start.strftime("%Y-%m-%d"),
                                 end=end.strftime("%Y-%m-%d"),
                                 progress=False, auto_adjust=True)
                if not df.empty:
                    frames[name] = df["Close"].squeeze()
                    break
            except Exception:
                pass
    price = pd.DataFrame(frames)
    price.index = pd.to_datetime(price.index)
    return price

def compute_returns(price):
    rets = pd.DataFrame(index=price.index)
    for col in price.columns:
        if col in ("VIX", "TNX"):
            rets[col] = price[col].diff()
        else:
            rets[col] = price[col].pct_change() * 100
    return rets.dropna()

def fig_to_b64(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    buf.seek(0)
    b64 = base64.b64encode(buf.read()).decode()
    plt.close(fig)
    return f"data:image/png;base64,{b64}"

def make_heatmap(corr, title):
    col_labels = [LABELS.get(c, c) for c in corr.columns]
    fig, ax = plt.subplots(figsize=(6.5, 5.5))
    sns.heatmap(corr, annot=True, fmt=".2f", cmap="RdYlGn",
                vmin=-1, vmax=1, linewidths=0.5,
                xticklabels=col_labels, yticklabels=col_labels, ax=ax)
    ax.set_title(title, fontsize=12, pad=10)
    plt.tight_layout()
    return fig_to_b64(fig)

def make_bar_chart(returns, days=30):
    recent = returns.tail(days)
    fig, axes = plt.subplots(3, 2, figsize=(12, 9), sharex=True)
    axes = axes.flatten()
    for i, col in enumerate(["BTC", "ETH", "SPX", "NDX", "VIX", "TNX"]):
        if col not in recent.columns:
            axes[i].set_visible(False)
            continue
        ax = axes[i]
        colors = ["#e74c3c" if v < 0 else "#27ae60" for v in recent[col]]
        ax.bar(recent.index, recent[col], color=colors, width=0.7)
        ax.axhline(0, color="black", linewidth=0.7)
        unit = "chg(pt)" if col in ("VIX", "TNX") else "ret(%)"
        ax.set_title(f"{LABELS.get(col, col)}  {unit}", fontsize=10)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d"))
        ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=2))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha="right")
    fig.suptitle(f"Daily Returns ? Last {days} Trading Days", fontsize=13)
    plt.tight_layout()
    return fig_to_b64(fig)

def corr_rows(corr, top=6):
    pairs = []
    cols = list(corr.columns)
    for i in range(len(cols)):
        for j in range(i + 1, len(cols)):
            pairs.append((cols[i], cols[j], corr.iloc[i, j]))
    pairs.sort(key=lambda x: abs(x[2]), reverse=True)
    rows = ""
    for a, b, v in pairs[:top]:
        color = "#27ae60" if v > 0 else "#e74c3c"
        desc = describe_corr(v)
        rows += (
            f"<tr>"
            f"<td>{LABELS.get(a,a)} x {LABELS.get(b,b)}</td>"
            f'<td style="color:{color};font-weight:700">{v:+.2f}</td>'
            f"<td>{desc}</td>"
            f"</tr>"
        )
    return rows

def snapshot_rows_html(last, price):
    rows = ""
    for col in ["BTC", "ETH", "SPX", "NDX", "VIX", "TNX"]:
        if col not in last.index:
            continue
        val = last[col]
        unit = "pt" if col in ("VIX", "TNX") else "%"
        arrow = "&#9650;" if val > 0 else ("&#9660;" if val < 0 else "&mdash;")
        color = "#27ae60" if val > 0 else ("#e74c3c" if val < 0 else "#888")
        px = price[col].iloc[-1] if col in price.columns else None
        if px and col in ("BTC", "ETH"):
            px_str = f"${px:,.0f}"
        elif px:
            px_str = f"{px:.2f}"
        else:
            px_str = ""
        rows += (
            f"<tr>"
            f"<td>{LABELS.get(col,col)}</td>"
            f"<td>{px_str}</td>"
            f'<td style="color:{color};font-weight:700">{arrow} {val:+.2f}{unit}</td>'
            f"</tr>"
        )
    return rows

def build_html(returns, corr30, corr90, price):
    now = datetime.now().strftime("%Y-%m-%d %H:%M UTC")
    last_date = returns.index[-1].strftime("%Y-%m-%d")
    last = returns.iloc[-1]

    img30  = make_heatmap(corr30, "Correlation Heatmap ? 30 Trading Days")
    img90  = make_heatmap(corr90, "Correlation Heatmap ? 90 Trading Days")
    imgbar = make_bar_chart(returns, min(30, len(returns)))

    snap  = snapshot_rows_html(last, price)
    r30   = corr_rows(corr30)
    r90   = corr_rows(corr90)

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Crypto x Macro Correlation</title>
<style>
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;
        background:#0f1117;color:#e0e0e0;padding:16px}}
  h1{{font-size:1.3rem;color:#f0f0f0;margin-bottom:4px}}
  .sub{{color:#888;font-size:0.78rem;margin-bottom:18px}}
  .card{{background:#1a1d27;border-radius:12px;padding:16px;
         margin-bottom:14px;border:1px solid #2a2d3a}}
  h2{{font-size:0.95rem;color:#aaa;margin-bottom:10px;
      border-left:3px solid #6c63ff;padding-left:8px}}
  table{{width:100%;border-collapse:collapse;font-size:0.85rem}}
  th{{color:#888;font-weight:500;padding:5px 4px;
      border-bottom:1px solid #2a2d3a;text-align:left}}
  td{{padding:6px 4px;border-bottom:1px solid #1f2230}}
  img{{width:100%;border-radius:8px;margin-top:8px}}
  .btn{{display:block;width:100%;padding:12px;background:#6c63ff;
        color:#fff;border:none;border-radius:10px;font-size:0.95rem;
        cursor:pointer;margin-bottom:14px;text-align:center;
        text-decoration:none}}
  .note{{background:#2a1f1a;border:1px solid #8b4513;
         border-radius:8px;padding:12px;font-size:0.78rem;color:#cd853f}}
  .note li{{margin-left:16px;margin-top:4px}}
</style>
</head>
<body>
<h1>Crypto x Macro Correlation</h1>
<p class="sub">Updated: {now} &nbsp;|&nbsp; Latest data: {last_date}</p>

<a class="btn" href="https://github.com/haobo-G/crypto-macro/actions" target="_blank">
  Refresh manually (GitHub Actions) &rarr;
</a>

<div class="card">
  <h2>Latest Snapshot</h2>
  <table>
    <tr><th>Asset</th><th>Price</th><th>Change</th></tr>
    {snap}
  </table>
</div>

<div class="card">
  <h2>30-Day Correlation ? Top 6 Pairs</h2>
  <table>
    <tr><th>Pair</th><th>r</th><th>Strength</th></tr>
    {r30}
  </table>
  <img src="{img30}" alt="heatmap 30d">
</div>

<div class="card">
  <h2>90-Day Correlation ? Top 6 Pairs</h2>
  <table>
    <tr><th>Pair</th><th>r</th><th>Strength</th></tr>
    {r90}
  </table>
  <img src="{img90}" alt="heatmap 90d">
</div>

<div class="card">
  <h2>Daily Returns Comparison</h2>
  <img src="{imgbar}" alt="daily returns">
</div>

<div class="note">
  <strong>Risk Notice</strong>
  <ul>
    <li>Correlation describes historical statistics, not causation</li>
    <li>Crypto vs traditional markets may have 1-2 day lag effects</li>
    <li>Data source: Yahoo Finance ? delays and gaps possible</li>
  </ul>
</div>
</body>
</html>"""

def main():
    print("Fetching data...")
    price = fetch_data(100)
    returns = compute_returns(price)
    if returns.empty or len(returns) < 5:
        print("Insufficient data.", file=sys.stderr)
        sys.exit(1)
    print(f"Valid trading days: {len(returns)}, latest: {returns.index[-1].date()}")

    corr30 = returns.tail(30).corr()
    corr90 = returns.tail(90).corr()

    print("Building HTML report...")
    html = build_html(returns, corr30, corr90, price)
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("Done -> index.html")

if __name__ == "__main__":
    main()
