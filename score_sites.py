"""lead-machine / score_sites.py
The free third stage: run every lead's website through Google PageSpeed
Insights (no key needed at low volume) and write back a performance score
plus a ready-made personalization line for outreach.

A slow, dated site IS the opening line of your cold email. This stage
finds it for you.

    python score_sites.py            # scores leads.csv -> leads_scored.csv
    python score_sites.py --top 50   # only the first N rows
"""
import csv
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

BASE = Path(__file__).parent
CFG = json.load(open(BASE / "config.json", encoding="utf-8"))
PREFIX = CFG.get("output_prefix", "leads")
# Keyless calls share a tiny global quota and 429 fast. A FREE key from
# https://developers.google.com/speed/docs/insights/v5/get-started fixes it:
#   set PSI_API_KEY=...   (or add "psi_api_key" to config.json)
KEY = os.environ.get("PSI_API_KEY") or CFG.get("psi_api_key", "")
PSI = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed?strategy=mobile&category=performance" \
      + (f"&key={KEY}" if KEY else "") + "&url="


def score(url, tries=3):
    for a in range(tries):
        try:
            with urllib.request.urlopen(PSI + urllib.parse.quote(url, safe=""), timeout=120) as r:
                d = json.load(r)
            perf = d["lighthouseResult"]["categories"]["performance"]["score"]
            lcp = d["lighthouseResult"]["audits"]["largest-contentful-paint"]["displayValue"]
            return round(perf * 100), lcp
        except urllib.error.HTTPError as e:
            if e.code == 429 and a < tries - 1:
                wait = 30 * (a + 1)
                print(f"    429 rate-limited, waiting {wait}s (get a free PSI_API_KEY to avoid this)", flush=True)
                time.sleep(wait)
                continue
            return None, None
        except Exception:
            return None, None
    return None, None


def line_for(company, perf, lcp):
    if perf is None:
        return ""
    if perf < 40:
        return f"ran {company}'s site through Google's own speed test - it scores {perf}/100 on mobile and takes {lcp} to show its main content. that's measurably costing you leads."
    if perf < 70:
        return f"{company}'s site scores {perf}/100 on Google's mobile speed test ({lcp} to main content) - fixable, and worth fixing before the next campaign."
    return f"{company}'s site is technically solid ({perf}/100) - the opportunity is conversion, not speed."


def main():
    top = None
    if "--top" in sys.argv:
        top = int(sys.argv[sys.argv.index("--top") + 1])

    rows = list(csv.DictReader(open(BASE / f"{PREFIX}.csv", encoding="utf-8-sig")))
    if top:
        rows = rows[:top]

    for i, row in enumerate(rows, 1):
        perf, lcp = score(row["website"])
        row["site_score"] = perf if perf is not None else ""
        row["site_lcp"] = lcp or ""
        row["opening_line"] = line_for(row["company"], perf, lcp)
        print(f"{i}/{len(rows)} {row['domain']}: {perf}", flush=True)
        time.sleep(1.5)  # be polite to the free API

    out = BASE / f"{PREFIX}_scored.csv"
    with open(out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    print(f"wrote {out.name}")


if __name__ == "__main__":
    main()
