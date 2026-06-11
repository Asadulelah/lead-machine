"""lead-machine / scrape.py
Queue-launch one Google-Maps scrape per location via the Apify CLI,
respecting the free-account concurrent-memory cap. Tracks every run
in runs.json so filter.py can collect the datasets later.

Setup:
    npm i -g apify-cli && apify login     (pay-per-event; a 10-city sweep costs a few dollars)
    cp config.example.json config.json    (edit queries/locations/filters)

Run:
    python scrape.py
"""
import json
import shutil
import subprocess
import time
from pathlib import Path

BASE = Path(__file__).parent
CFG = json.load(open(BASE / "config.json", encoding="utf-8"))
APIFY = shutil.which("apify") or "apify"
RUNS = BASE / "runs.json"


def cli(args):
    # NOTE: the CLI prints an update banner into stdout; parse JSON from the first brace.
    # encoding='utf-8' matters on Windows: Apify's output contains emoji that crash cp1252.
    r = subprocess.run([APIFY] + args + ["--json"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    s = r.stdout or ""
    i = s.find("{")
    if i < 0:
        return None, (r.stderr or s)[:200]
    try:
        return json.loads(s[i:]), None
    except Exception as e:
        return None, str(e)


def run_status(run_id):
    out, _ = cli(["runs", "info", run_id])
    return (out or {}).get("status", "UNKNOWN")


def main():
    runs = json.load(open(RUNS, encoding="utf-8")) if RUNS.exists() else []
    active = [r["runId"] for r in runs]
    started = {r["location"] for r in runs}
    pending = [c for c in CFG["locations"] if c not in started]

    while pending or any(run_status(r) in ("RUNNING", "READY") for r in active):
        statuses = {r: run_status(r) for r in active}
        running = [r for r, s in statuses.items() if s in ("RUNNING", "READY")]
        print(f"[queue] running={len(running)} pending={len(pending)} done={len(active) - len(running)}", flush=True)

        while pending and len(running) < CFG["max_concurrent_runs"]:
            loc = pending.pop(0)
            payload = {
                "searchStringsArray": CFG["queries"],
                "locationQuery": loc,
                "maxCrawledPlacesPerSearch": CFG["max_places_per_search"],
                "language": "en",
                "skipClosedPlaces": True,
                "website": "withWebsite" if CFG["filters"]["require_website"] else "allPlaces",
                "scrapeContacts": True,
            }
            out, err = cli(["actors", "start", CFG["apify_actor"],
                            "-i", json.dumps(payload), "--memory", str(CFG["memory_mb"])])
            if out:
                runs.append({"location": loc, "runId": out["id"], "datasetId": out["defaultDatasetId"]})
                active.append(out["id"]); running.append(out["id"])
                RUNS.write_text(json.dumps(runs, indent=2), encoding="utf-8")
                print(f"STARTED {loc} -> {out['id']}", flush=True)
            else:
                pending.insert(0, loc)   # likely the account memory cap; retry next cycle
                print(f"WAIT {loc}: {err}", flush=True)
                break

        if not pending and not running:
            break
        time.sleep(30)

    print("ALL_RUNS_FINISHED", flush=True)


if __name__ == "__main__":
    main()
