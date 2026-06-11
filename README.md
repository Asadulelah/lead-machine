# lead-machine 🕷️

**448 qualified B2B leads, 285 with verified emails, for about $6. In one night. No Apollo, no Sales Navigator, no subscription.**

This is the exact pipeline, genericized. Three stages, all config-driven:

```
scrape.py  ->  Google Maps via one Apify actor, queued city by city
filter.py  ->  ICP filter + portal blacklist + dedupe -> ranked CSV
score_sites.py -> free Google PageSpeed pass -> a written opening line per lead
```

## Why it works

Google Maps is the most honest B2B database on earth: real businesses, real addresses, real review counts, and (with contact scraping on) emails + socials pulled straight from their own websites. The expensive tools resell this with a UI on top.

The third stage is the underrated one: it runs every lead's site through Google's own speed test and **writes the first line of your cold email for you**:

> "ran {company}'s site through Google's own speed test - it scores 31/100 on mobile and takes 9.1s to show its main content. that's measurably costing you leads."

That line is personalized, verifiable, and about THEIR money. It beats "I hope this email finds you well" by a margin you can feel.

## Setup

```bash
npm i -g apify-cli && apify login      # pay-per-event; a 10-city sweep = a few dollars
cp config.example.json config.json     # put YOUR niche in: queries, cities, ICP regexes
python scrape.py                       # launches + babysits the runs (respects the 8GB account cap)
python filter.py                       # merge -> filter -> dedupe -> leads.csv
python score_sites.py --top 50         # adds site_score + opening_line columns
```

For the scoring stage, grab a free PageSpeed API key (one click, no card) and `set PSI_API_KEY=...` - keyless calls share a tiny global quota.

## Field notes (paid for in real runs)

- The Apify CLI prints an update banner into stdout: parse JSON from the first `{`
- On Windows, subprocess needs `encoding='utf-8'` or Apify's emoji output crashes cp1252
- Free accounts cap concurrent actor memory at 8GB: queue runs at `--memory 2048`, 3 at a time
- Filter rejects in this order: no website → portal/franchise domain → excluded category → weak category match → duplicate domain. Log the counts; silent filtering lies to you
- Sort by has-email first, then review count: review count is a free proxy for "established firm"

## Honest limits

Maps can't verify revenue or headcount: use reviews + address + category as proxies and verify the shortlist manually. And scrape responsibly: this is for building a targeted prospect list, not for spam cannons.

---

Built by [Asadulelah](https://github.com/Asadulelah). The night this pipeline first ran, the alternative quote was a $99/month data subscription.
