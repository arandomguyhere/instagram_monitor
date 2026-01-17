#!/usr/bin/env python3
"""
Friends List → Monitoring Queue integrator

- Reads friends extraction output (followers/following/mutuals) for one or more users
- Merges into monitoring_data/monitoring_queue.json with priority & de-duplication
- Emits GitHub Actions outputs: queue_size, new_items, batches_json

Usage:
  python workflow_integration.py \
      --friends-file data/alice_friends_analysis.json \
      --priority mutuals,following,followers \
      --batch-size 8 \
      --days-between 2

You can pass multiple --friends-file arguments.
"""
from __future__ import annotations
import argparse, json, os
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict

QUEUE_PATH = Path("monitoring_data/monitoring_queue.json")
QUEUE_PATH.parent.mkdir(parents=True, exist_ok=True)


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_json(p: Path, default):
    if p.exists():
        with p.open("r", encoding="utf-8") as f:
            return json.load(f)
    return default


def save_json_atomic(p: Path, obj):
    tmp = p.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
    tmp.replace(p)


def normalize_username(u: str) -> str:
    return (u or "").strip().lstrip("@").lower()


def score_bucket(name: str, weights: Dict[str, int]) -> int:
    return weights.get(name, 0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--friends-file", action="append", required=True,
                    help="Path(s) to *_friends_analysis.json")
    ap.add_argument("--priority", default="mutuals,following,followers",
                    help="Comma order for priority scoring (high→low)")
    ap.add_argument("--batch-size", type=int, default=8)
    ap.add_argument("--days-between", type=int, default=2,
                    help="Min days between rechecks of same user")
    ap.add_argument("--max-queue", type=int, default=5000)
    args = ap.parse_args()

    order = [s.strip().lower() for s in args.priority.split(",") if s.strip()]
    weights = {name: (len(order) - i) * 10 for i, name in enumerate(order)}

    queue = load_json(QUEUE_PATH, {
        "version": 1,
        "updated_at": utcnow_iso(),
        "items": []  # list of {"username","score","last_checked_at","source_tags":[]}
    })

    idx = {it["username"]: it for it in queue["items"]}
    new_count = 0

    for fp in args.friends_file:
        data = load_json(Path(fp), {})
        # Accept either schema
        buckets = {
            "mutuals": data.get("mutual_friends") or data.get("mutuals") or [],
            "followers": data.get("followers_only") or data.get("followers") or [],
            "following": data.get("followings_only") or data.get("following") or [],
        }
        target = normalize_username(data.get("target") or data.get("username"))

        for bucket_name, users in buckets.items():
            for u in users or []:
                user = normalize_username(u)
                if not user or (target and user == target):
                    continue
                score = score_bucket(bucket_name, weights)
                if user in idx:
                    item = idx[user]
                    item["score"] = max(item.get("score", 0), score)
                    item.setdefault("source_tags", [])
                    if bucket_name not in item["source_tags"]:
                        item["source_tags"].append(bucket_name)
                else:
                    idx[user] = {
                        "username": user,
                        "score": score,
                        "last_checked_at": None,
                        "source_tags": [bucket_name]
                    }
                    new_count += 1

    queue["items"] = list(idx.values())

    # Sort: never-checked first, then oldest check, then score desc, then username
    def sort_key(it):
        lc = it.get("last_checked_at") or ""
        # Use timezone-aware datetime.min to avoid comparison issues
        ts = datetime.min.replace(tzinfo=timezone.utc) if not lc else datetime.fromisoformat(lc)
        return (lc is not None, ts, -it.get("score", 0), it["username"])

    queue["items"].sort(key=sort_key)

    # Eligibility window
    cutoff = datetime.now(timezone.utc) - timedelta(days=args.days_between)
    eligible = [it for it in queue["items"]
                if it["last_checked_at"] is None
                or datetime.fromisoformat(it["last_checked_at"]) <= cutoff]

    first_batch = [it["username"] for it in eligible[:args.batch_size]]

    if len(queue["items"]) > args.max_queue:
        queue["items"] = queue["items"][:args.max_queue]

    queue["updated_at"] = utcnow_iso()
    save_json_atomic(QUEUE_PATH, queue)

    # GitHub Actions outputs
    gha_out = os.getenv("GITHUB_OUTPUT")
    if gha_out:
        with open(gha_out, "a", encoding="utf-8") as f:
            f.write(f"queue_size={len(queue['items'])}\n")
            f.write(f"new_items={new_count}\n")
            f.write(f"batches_json={json.dumps([first_batch])}\n")

    print(f"[integration] queue_size={len(queue['items'])} new_items={new_count} first_batch={first_batch}")


if __name__ == "__main__":
    main()
