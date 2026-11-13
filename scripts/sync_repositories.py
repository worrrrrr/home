#!/usr/bin/env python3
"""Update the public repository inventory in README.md."""

from __future__ import annotations

import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

OWNER = os.environ.get("GITHUB_OWNER", "worrrrrr")
README = Path("README.md")
START = "<!-- REPOSITORIES:START -->"
END = "<!-- REPOSITORIES:END -->"


def fetch_page(page: int) -> list[dict]:
    query = urllib.parse.urlencode({
        "type": "owner",
        "sort": "updated",
        "direction": "desc",
        "per_page": 100,
        "page": page,
    })
    request = urllib.request.Request(
        f"https://api.github.com/users/{OWNER}/repos?{query}",
        headers={
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "home-repository-index",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def load_repositories() -> list[dict]:
    result: list[dict] = []
    page = 1
    while True:
        batch = fetch_page(page)
        result.extend(
            repo for repo in batch
            if repo.get("owner", {}).get("login", "").lower() == OWNER.lower()
            and not repo.get("private", True)
        )
        if len(batch) < 100:
            break
        page += 1
    return sorted(result, key=lambda item: item.get("updated_at") or "", reverse=True)


def render(repositories: list[dict]) -> str:
    if not repositories:
        return "_ยังไม่พบ Public repository_"

    rows = [
        "| Repository | รายละเอียด | ภาษา | อัปเดตล่าสุด |",
        "|---|---|---|---|",
    ]
    for repo in repositories:
        description = (repo.get("description") or "—").replace("|", "\\|").replace("\n", " ")
        if repo.get("archived"):
            description = f"Archived · {description}"
        updated = repo.get("updated_at")
        date = (
            datetime.fromisoformat(updated.replace("Z", "+00:00"))
            .astimezone(timezone.utc).strftime("%Y-%m-%d")
            if updated else "—"
        )
        rows.append(
            f"| [{repo['name']}]({repo['html_url']}) | {description} | "
            f"{repo.get('language') or '—'} | {date} |"
        )
    return "\n".join(rows)


def main() -> int:
    if not README.exists():
        print("README.md not found", file=sys.stderr)
        return 1

    original = README.read_text(encoding="utf-8")
    if START not in original or END not in original:
        print("README markers missing; refusing to overwrite content", file=sys.stderr)
        return 1

    repositories = load_repositories()
    before, remainder = original.split(START, 1)
    _, after = remainder.split(END, 1)
    updated = f"{before}{START}\n{render(repositories)}\n{END}{after}"

    if updated == original:
        print(f"Already up to date ({len(repositories)} public repositories).")
        return 0

    README.write_text(updated, encoding="utf-8")
    print(f"Indexed {len(repositories)} public repositories.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
