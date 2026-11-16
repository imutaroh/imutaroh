#!/usr/bin/env python3
"""README 上部の「( 00 / log )」画像を作る。

GitHub の公開ページ（プロフィールの草と同じもの）から過去 1 年の
コントリビューションを読み、assets/log.json と assets/log-{light,dark}.png を更新する。
数字が前回と同じなら何もしない（FORCE=1 で作り直す）。

使い方:  CHROME=<Chrome の実行ファイル> python3 scripts/log.py
"""
import datetime
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import urllib.request

USER = "imutaroh"
ROOT = pathlib.Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
WEEKDAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def fetch():
    req = urllib.request.Request(
        f"https://github.com/users/{USER}/contributions",
        headers={"User-Agent": "profile-readme-log"},
    )
    html = urllib.request.urlopen(req, timeout=30).read().decode("utf-8")
    total = re.search(r"([\d,]+)\s+contributions?\s+in the last year", html)
    cells = {}
    for tag in re.findall(r"<td[^>]*ContributionCalendar-day[^>]*>", html):
        date = re.search(r'data-date="([\d-]+)"', tag)
        cid = re.search(r'\bid="([^"]+)"', tag)
        if date and cid:
            cells[cid.group(1)] = date.group(1)
    days = {}
    for cid, n in re.findall(r'<tool-tip[^>]*for="([^"]+)"[^>]*>\s*(No|\d+) contributions?', html):
        if cid in cells:
            days[cells[cid]] = 0 if n == "No" else int(n)
    if not total or len(days) < 300:
        sys.exit("コントリビューションのページを読み取れなかった（HTML の形が変わった可能性）")
    return int(total.group(1).replace(",", "")), dict(sorted(days.items()))


def summarize(total, days):
    dates = list(days)
    weeks = [sum(days[d] for d in dates[i:i + 7]) for i in range(0, len(dates), 7)]
    best = max(dates, key=lambda d: days[d])
    by_wd = [0] * 7
    for d, n in days.items():
        by_wd[datetime.date.fromisoformat(d).weekday()] += n
    return {
        "total": total,
        "per_day": round(total / len(dates), 1),
        "best_day": best,
        "best_count": days[best],
        "busiest": WEEKDAYS[by_wd.index(max(by_wd))],
        "quietest": WEEKDAYS[by_wd.index(min(by_wd))],
        "weeks": weeks,
    }


def html(s):
    w, h, pad = 440, 78, 6
    top = max(s["weeks"]) or 1
    pts = [
        (pad + i * (w - 2 * pad) / (len(s["weeks"]) - 1), h - pad - v / top * (h - 2 * pad))
        for i, v in enumerate(s["weeks"])
    ]
    line = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    ex, ey = pts[-1]
    return f"""<!doctype html><meta charset="utf-8">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=Playfair+Display:wght@700&display=swap">
<style>
html,body{{margin:0;background:transparent}}
body{{--ink:#1a2330;--sub:#5b6572;--line:#e3e8ed;--acc:#00add8;color:var(--ink);width:840px}}
body.dark{{--ink:#e8edf2;--sub:#9aa5b1;--line:#2f3945}}
.eb{{display:flex;align-items:center;gap:10px;font:400 13px "IBM Plex Mono",monospace;color:var(--sub);height:28px}}
.eb::after{{content:"";flex:1;height:1px;background:var(--line)}}
.dial{{width:11px;height:11px;border:1px solid var(--ink);border-radius:50%;position:relative;flex:none;box-sizing:border-box}}
.dial::after{{content:"";position:absolute;inset:2px;border-radius:50%;background:var(--ink)}}
.row{{display:flex;align-items:flex-end;justify-content:space-between;gap:24px;padding:10px 0 0}}
.num{{font:700 68px/1 "Playfair Display",serif;letter-spacing:-.01em}}
.cap{{font:400 13px "IBM Plex Mono",monospace;color:var(--sub);margin-top:10px}}
.pills{{display:flex;gap:8px;margin-top:16px}}
.pill{{font:400 12px "IBM Plex Mono",monospace;border:1px solid var(--line);border-radius:999px;padding:3px 12px;white-space:nowrap}}
svg{{display:block}}
.ax{{font:400 11px "IBM Plex Mono",monospace;color:var(--sub);display:flex;justify-content:space-between;margin-top:4px}}
</style>
<body><script>if(location.hash==="#dark")document.body.classList.add("dark")</script>
<div class="eb"><span class="dial"></span>( 00 / log )</div>
<div class="row">
  <div>
    <div class="num">{s["total"]:,}</div>
    <div class="cap">contributions · last 365 days</div>
  </div>
  <div>
    <svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" fill="none">
      <line x1="0" y1="{h - 0.5}" x2="{w}" y2="{h - 0.5}" stroke="var(--line)"/>
      <polyline points="{line}" stroke="var(--ink)" stroke-width="1.25" stroke-linejoin="round" stroke-linecap="round" fill="none"/>
      <circle cx="{ex:.1f}" cy="{ey:.1f}" r="3.5" fill="var(--acc)"/>
    </svg>
    <div class="ax"><span>52 weeks ago</span><span>this week</span></div>
  </div>
</div>
<div class="pills">
  <span class="pill">{s["per_day"]} / day</span>
  <span class="pill">best day {s["best_count"]} · {s["best_day"]}</span>
  <span class="pill">busiest {s["busiest"]}</span>
  <span class="pill">quietest {s["quietest"]}</span>
</div>
"""


def render(page):
    chrome = os.environ.get("CHROME", "google-chrome")
    with tempfile.TemporaryDirectory() as tmp:
        src = pathlib.Path(tmp) / "log.html"
        src.write_text(page, encoding="utf-8")
        for theme in ("light", "dark"):
            subprocess.run(
                [
                    chrome, "--headless=new", "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
                    "--force-device-scale-factor=2", "--default-background-color=00000000",
                    "--virtual-time-budget=8000", "--window-size=840,190",
                    f"--screenshot={ASSETS / f'log-{theme}.png'}",
                    f"file://{src}#{theme}",
                ],
                check=True, timeout=120, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )


def main():
    summary = summarize(*fetch())
    out = ASSETS / "log.json"
    text = json.dumps(summary, ensure_ascii=False, indent=2) + "\n"
    if out.exists() and out.read_text(encoding="utf-8") == text and not os.environ.get("FORCE"):
        print("変化なし")
        return
    render(html(summary))
    out.write_text(text, encoding="utf-8")
    print(f"更新: {summary['total']:,} contributions")


if __name__ == "__main__":
    main()
