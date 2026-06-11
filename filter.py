"""lead-machine / filter.py
Merge every dataset from runs.json, filter against your ICP (config.json),
dedupe by domain, rank (has-email first, then review count), and write
<prefix>.csv + <prefix>.json.

Run after scrape.py finishes:
    python filter.py
"""
import csv
import json
import re
import shutil
import subprocess
from pathlib import Path

BASE = Path(__file__).parent
CFG = json.load(open(BASE / "config.json", encoding="utf-8"))
APIFY = shutil.which("apify") or "apify"

F = CFG["filters"]
INCLUDE = re.compile(F["include_categories"], re.I)
EXCLUDE = re.compile(F["exclude_categories"], re.I)
BLACKLIST = re.compile(F["domain_blacklist"], re.I)


def fetch_dataset(dataset_id):
    r = subprocess.run([APIFY, "datasets", "get-items", dataset_id, "--format", "json"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    txt = (r.stdout or "").strip()
    start = txt.find("[")
    return json.loads(txt[start:]) if start >= 0 else []


def main():
    runs = json.load(open(BASE / "runs.json", encoding="utf-8"))
    raw, leads, seen = 0, [], set()
    rejected = {"no_site": 0, "excluded_cat": 0, "portal": 0, "dupe": 0, "weak": 0}

    for run in runs:
        items = fetch_dataset(run["datasetId"])
        raw += len(items)
        for it in items:
            site = (it.get("website") or "").strip()
            if not site:
                rejected["no_site"] += 1; continue
            domain = re.sub(r"^https?://(www\.)?", "", site).split("/")[0].lower()
            if BLACKLIST.search(site):
                rejected["portal"] += 1; continue
            cat = it.get("categoryName") or ""
            cats = " ".join([cat] + (it.get("categories") or []))
            title = it.get("title") or ""
            if EXCLUDE.search(cats) or EXCLUDE.search(title):
                rejected["excluded_cat"] += 1; continue
            if not INCLUDE.search(cats) and not INCLUDE.search(title):
                rejected["weak"] += 1; continue
            if domain in seen:
                rejected["dupe"] += 1; continue
            seen.add(domain)
            emails = it.get("emails") or []
            leads.append({
                "company": title,
                "category": cat,
                "market": run["location"],
                "address": it.get("address") or "",
                "phone": it.get("phone") or "",
                "website": site,
                "domain": domain,
                "email_1": emails[0] if emails else "",
                "emails_all": "; ".join(emails[:5]),
                "linkedin": (it.get("linkedIns") or [""])[0] if it.get("linkedIns") else "",
                "instagram": (it.get("instagrams") or [""])[0] if it.get("instagrams") else "",
                "google_rating": it.get("totalScore") or "",
                "reviews": it.get("reviewsCount") or 0,
                "maps_url": it.get("url") or "",
            })

    leads.sort(key=lambda x: (x["email_1"] == "", -(x["reviews"] or 0)))

    prefix = CFG.get("output_prefix", "leads")
    (BASE / f"{prefix}.json").write_text(json.dumps(leads, indent=1, ensure_ascii=False), encoding="utf-8")
    with open(BASE / f"{prefix}.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(leads[0].keys()))
        w.writeheader(); w.writerows(leads)

    with_email = sum(1 for l in leads if l["email_1"])
    print(f"raw={raw} kept={len(leads)} with_email={with_email} rejected={rejected}")


if __name__ == "__main__":
    main()
