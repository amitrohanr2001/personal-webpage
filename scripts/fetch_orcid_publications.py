#!/usr/bin/env python3
import json
import re
from pathlib import Path
from urllib.request import Request, urlopen

ORCID = "0009-0001-9788-1259"
OUT = Path("src/data/publications.json")
API = f"https://pub.orcid.org/v3.0/{ORCID}/works"

HEADERS = {
    "Accept": "application/vnd.orcid+json",
    "User-Agent": "amitrohanr-site-orcid-sync/1.0",
}

def get_json(url: str) -> dict:
    req = Request(url, headers=HEADERS)
    with urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))

def clean(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())

def main():
    data = get_json(API)

    items = []
    groups = data.get("group", []) or []
    for g in groups:
        summaries = g.get("work-summary", []) or []
        for ws in summaries:
            title = clean(((ws.get("title") or {}).get("title") or {}).get("value"))
            pub_date = ws.get("publication-date") or {}
            year_raw = (pub_date.get("year") or {}).get("value")
            year = int(year_raw) if (year_raw and str(year_raw).isdigit()) else None

            wtype = clean(ws.get("type") or "").lower()

            # Try to find a good external URL (prefer DOI)
            url = ""
            doi = ""
            external_ids = (ws.get("external-ids") or {}).get("external-id", []) or []
            for ext in external_ids:
                t = (ext.get("external-id-type") or "").lower()
                v = clean(ext.get("external-id-value") or "")
                u = (ext.get("external-id-url") or {}).get("value") or ""

                if t == "doi" and v:
                    doi = v
                    url = u or f"https://doi.org/{doi}"
                    break
                if u and not url:
                    url = u

            items.append({
                "title": title or "Untitled",
                "year": year,
                "type": wtype,
                "doi": doi,
                "url": url,
            })

    # De-dupe by (title, year, type)
    seen = set()
    uniq = []
    for p in items:
        key = (p["title"].lower(), p["year"], p["type"])
        if key in seen:
            continue
        seen.add(key)
        uniq.append(p)

    # Sort: newest year first; unknown years last
    uniq.sort(key=lambda p: (p["year"] is None, -(p["year"] or 0), p["title"].lower()))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "orcid": ORCID,
        "updated_by": "github-actions",
        "count": len(uniq),
        "items": uniq,
    }, indent=2), encoding="utf-8")

    print(f"Wrote {OUT} with {len(uniq)} items.")

if __name__ == "__main__":
    main()