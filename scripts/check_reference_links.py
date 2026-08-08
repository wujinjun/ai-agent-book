#!/usr/bin/env python3
"""Check the curated reference catalog without running as part of offline tests."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

import httpx
import yaml

ROOT = Path(__file__).resolve().parents[1]


async def _check_one(
    client: httpx.AsyncClient,
    semaphore: asyncio.Semaphore,
    item: dict[str, Any],
) -> dict[str, Any]:
    async with semaphore:
        last_error = "unknown"
        for attempt in range(2):
            try:
                response = await client.get(
                    str(item["url"]),
                    headers={"Range": "bytes=0-2047"},
                )
                status_code = response.status_code
                if 200 <= status_code < 400:
                    state = "ok"
                elif status_code in {401, 403, 429}:
                    state = "restricted"
                else:
                    state = "failed"
                return {
                    "id": item["id"],
                    "url": item["url"],
                    "state": state,
                    "status_code": status_code,
                    "final_url": str(response.url),
                }
            except httpx.HTTPError as exc:
                last_error = type(exc).__name__
                if attempt == 0:
                    await asyncio.sleep(0.25)
        return {
            "id": item["id"],
            "url": item["url"],
            "state": "failed",
            "error": last_error,
        }


async def check_links(root: Path = ROOT, *, concurrency: int = 12) -> dict[str, Any]:
    references = yaml.safe_load((root / "notes/references.yml").read_text(encoding="utf-8"))
    overrides_path = root / "notes/reference-link-overrides.yml"
    overrides = yaml.safe_load(overrides_path.read_text(encoding="utf-8")) or {}
    semaphore = asyncio.Semaphore(concurrency)
    timeout = httpx.Timeout(20.0, connect=10.0)
    headers = {"User-Agent": "ai-agent-book-reference-audit/1.0"}
    async with httpx.AsyncClient(
        follow_redirects=True,
        timeout=timeout,
        headers=headers,
        trust_env=False,
    ) as client:
        results = await asyncio.gather(
            *(_check_one(client, semaphore, item) for item in references)
        )
    for result in results:
        override = overrides.get(result["id"])
        if result["state"] == "failed" and override:
            result.update(
                {
                    "state": "verified_separately",
                    "verification": override,
                }
            )
    counts = {
        state: sum(item["state"] == state for item in results)
        for state in ("ok", "restricted", "verified_separately", "failed")
    }
    return {
        "schema_version": 1,
        "checked": "2026-08-08",
        "total": len(results),
        "counts": counts,
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("notes/reference-link-audit.json"))
    parser.add_argument("--concurrency", type=int, default=12)
    args = parser.parse_args()
    report = asyncio.run(check_links(concurrency=args.concurrency))
    output = args.output if args.output.is_absolute() else ROOT / args.output
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["counts"], ensure_ascii=False))
    return 1 if report["counts"]["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
