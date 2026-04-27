#!/usr/bin/env python3
"""Merge Agency_Nm and AreaRnd_WN from attributes_agcy.csv into sites.json.

For each site in sites.json whose `id` matches a CSV row's `Project_Nm`
(case-insensitive), set:
  - `agency`  <- Agency_Nm    (empty string if blank)
  - `acreage` <- AreaRnd_WN   (overwrites existing value)
"""

import csv
import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent
CSV_PATH = DATA_DIR / "attributes_agcy.csv"
JSON_PATH = DATA_DIR / "sites.json"


def parse_acreage(value):
    if value is None:
        return None
    s = str(value).strip().replace(",", "")
    if s == "":
        return None
    try:
        n = float(s)
        return int(n) if n.is_integer() else n
    except ValueError:
        return s


def load_csv_lookup(path):
    lookup = {}
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            project = (row.get("Project_Nm") or "").strip()
            if not project:
                continue
            lookup[project.lower()] = {
                "agency": (row.get("Agency_Nm") or "").strip(),
                "acreage": parse_acreage(row.get("AreaRnd_WN")),
            }
    return lookup


def main():
    lookup = load_csv_lookup(CSV_PATH)

    with JSON_PATH.open(encoding="utf-8") as f:
        data = json.load(f)

    sites = data.get("sites", [])
    matched = 0
    unmatched = []
    used_keys = set()
    for site in sites:
        raw_id = (site.get("id") or "").strip()
        site_id = raw_id.lower()
        if not site_id:
            continue

        record = lookup.get(site_id)
        if record is not None:
            site["agency"] = record["agency"]
            if record["acreage"] is not None:
                site["acreage"] = record["acreage"]
            used_keys.add(site_id)
            matched += 1
            continue

        # Composite id: split on '_' and combine matching CSV rows.
        parts = [p.strip().lower() for p in raw_id.split("_") if p.strip()]
        part_records = [(p, lookup[p]) for p in parts if p in lookup]
        if not part_records:
            unmatched.append(raw_id)
            continue

        agencies = []
        for _, rec in part_records:
            a = rec["agency"]
            if a and a not in agencies:
                agencies.append(a)
        site["agency"] = "; ".join(agencies)

        acres = [rec["acreage"] for _, rec in part_records if isinstance(rec["acreage"], (int, float))]
        if acres:
            total = sum(acres)
            site["acreage"] = int(total) if float(total).is_integer() else total

        used_keys.update(p for p, _ in part_records)
        matched += 1

    with JSON_PATH.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"Matched {matched} of {len(sites)} sites.")
    if unmatched:
        print(f"Unmatched site ids ({len(unmatched)}): {', '.join(unmatched)}")
    csv_only = sorted(k for k in lookup if k not in used_keys)
    if csv_only:
        print(f"CSV rows with no matching site ({len(csv_only)}): {', '.join(csv_only)}")


if __name__ == "__main__":
    main()
