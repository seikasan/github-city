"""GitHub statistics -> bounded city parameters -> static, self-contained SVG.

Python 3.12+, standard library only. Network requests happen here, never in SVG.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import date, datetime, time, timedelta, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sys
import tempfile
import urllib.error
import urllib.request

API = "https://api.github.com/graphql"
COUNTS = ("commits", "pull_requests", "reviews", "issues", "recent_activity", "active_days", "public_repositories", "stars")
DEFAULTS = {
    "username": "seikasan",
    "seed": None,
    "scales": {"commits": 2500, "pull_requests": 150, "reviews": 200, "recent_activity": 200, "public_repositories": 40, "stars": 300},
    "appearance": {"min_height": 72, "max_height": 330, "min_buildings": 2, "max_buildings": 9, "min_window_light": 0.12, "max_window_light": 0.88, "accent": None},
    "overrides": {},
}

STATS_QUERY = """query CityStats($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    login
    contributionsCollection(from: $from, to: $to) {
      totalCommitContributions
      totalPullRequestContributions
      totalPullRequestReviewContributions
      totalIssueContributions
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}"""
REPOS_QUERY = """query CityRepos($login: String!, $after: String) {
  user(login: $login) {
    repositories(first: 100, after: $after, privacy: PUBLIC,
                 isFork: false, ownerAffiliations: [OWNER],
                 orderBy: {field: NAME, direction: ASC}) {
      nodes { stargazerCount primaryLanguage { name color } }
      pageInfo { hasNextPage endCursor }
    }
  }
}"""


def stable_seed(label: str) -> int:
    return int.from_bytes(hashlib.sha256(label.encode("utf-8")).digest()[:8], "big")


def load_config(path: Path | None) -> dict:
    config = json.loads(json.dumps(DEFAULTS))
    if path:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("Configuration must be a JSON object")
        for key, value in raw.items():
            if key not in config:
                raise ValueError(f"Unknown configuration key: {key}")
            if isinstance(config[key], dict):
                if not isinstance(value, dict):
                    raise ValueError(f"{key} must be an object")
                if key != "overrides" and value.keys() - config[key].keys():
                    raise ValueError(f"Unknown key in {key}")
                config[key].update(value)
            else:
                config[key] = value
    for k, v in config["scales"].items():
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v <= 0:
            raise ValueError(f"Scale {k} must be finite and positive")
    a = config["appearance"]
    if not (32 <= a["min_height"] <= a["max_height"] <= 350):
        raise ValueError("Heights must satisfy 32 <= min_height <= max_height <= 350")
    if not all(type(a[k]) is int for k in ("min_buildings", "max_buildings")) or not (1 <= a["min_buildings"] <= a["max_buildings"] <= 9):
        raise ValueError("Building count must satisfy 1 <= min_buildings <= max_buildings <= 9")
    if not (0 <= a["min_window_light"] <= a["max_window_light"] <= 1):
        raise ValueError("Window light rates must be between 0 and 1")
    if a["accent"] is not None and not re.fullmatch(r"#[0-9a-fA-F]{6}", a["accent"]):
        raise ValueError("accent must be null or a six-digit hex color")
    return config


def graphql(query: str, variables: dict, token: str) -> dict:
    request = urllib.request.Request(API, data=json.dumps({"query": query, "variables": variables}).encode(), headers={
        "Authorization": f"Bearer {token}", "Content-Type": "application/json", "User-Agent": "github-isometric-city/1.0",
    }, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            payload = json.load(response)
    except urllib.error.HTTPError as exc:
        # Never echo request headers, tokens or full HTTP bodies.
        raise RuntimeError(f"GitHub API returned HTTP {exc.code}; check token permissions and rate limit") from None
    except (urllib.error.URLError, TimeoutError) as exc:
        raise RuntimeError("Could not reach GitHub API; existing SVG was not changed") from None
    if payload.get("errors"):
        messages = "; ".join(str(e.get("message", "GraphQL error")) for e in payload["errors"])
        raise RuntimeError(f"GitHub GraphQL error: {messages}")
    if not payload.get("data") or not payload["data"].get("user"):
        raise RuntimeError("GitHub user was not found or API response was incomplete")
    return payload["data"]


def fetch_stats(username: str, token: str, end: date | None = None, request=graphql) -> dict:
    """Use the last 365 completed UTC dates. Today's partial day is excluded."""
    if not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})", username):
        raise ValueError("Invalid GitHub username")
    end = end or datetime.now(timezone.utc).date()
    start = end - timedelta(days=365)
    from_dt = datetime.combine(start, time.min, timezone.utc)
    to_dt = datetime.combine(end, time.min, timezone.utc) - timedelta(seconds=1)
    variables = {"login": username, "from": from_dt.isoformat(), "to": to_dt.isoformat()}
    user = request(STATS_QUERY, variables, token)["user"]
    c = user["contributionsCollection"]
    days = {}
    for week in c["contributionCalendar"]["weeks"]:
        for day in week["contributionDays"]:
            d = date.fromisoformat(day["date"])
            if start <= d < end:
                days[d] = day["contributionCount"]
    # A partial response must not make the city shrink as if missing dates were zero.
    if len(days) != 365:
        raise RuntimeError(f"Expected 365 contribution dates; received {len(days)}")
    stats = {"username": user["login"], "period": {"from": start.isoformat(), "to": (end - timedelta(days=1)).isoformat(), "timezone": "UTC"},
        "commits": c["totalCommitContributions"], "pull_requests": c["totalPullRequestContributions"],
        "reviews": c["totalPullRequestReviewContributions"], "issues": c["totalIssueContributions"],
        "recent_activity": sum(n for d, n in days.items() if d >= end - timedelta(days=30)),
        "active_days": sum(n > 0 for n in days.values()),
        "public_repositories": 0, "stars": 0, "languages": [], "source": "github-api"}
    languages = Counter()
    colors = {}
    cursor = None
    seen = set()
    while True:
        repos = request(REPOS_QUERY, {"login": username, "after": cursor}, token)["user"]["repositories"]
        for repo in repos["nodes"]:
            if repo is None:
                raise RuntimeError("Incomplete repository page")
            stats["public_repositories"] += 1
            stats["stars"] += repo["stargazerCount"]
            lang = repo.get("primaryLanguage")
            if lang:
                languages[lang["name"]] += 1
                colors[lang["name"]] = lang.get("color") or "#66cddd"
        info = repos["pageInfo"]
        if not info["hasNextPage"]:
            break
        cursor = info["endCursor"]
        if not cursor or cursor in seen:
            raise RuntimeError("Repository pagination did not advance")
        seen.add(cursor)
    stats["languages"] = [{"name": name, "color": colors[name], "repositories": count} for name, count in sorted(languages.items())]
    return validate_stats(stats)


def validate_stats(stats: dict) -> dict:
    if not isinstance(stats.get("username"), str) or not stats["username"]:
        raise ValueError("Statistics need a non-empty username")
    for key in COUNTS:
        v = stats.get(key)
        if type(v) is not int or v < 0:
            raise ValueError(f"Statistic {key} must be a non-negative integer")
    if stats["active_days"] > 365:
        raise ValueError("active_days cannot exceed 365")
    for lang in stats.get("languages", []):
        if not isinstance(lang.get("name"), str) or not re.fullmatch(r"#[0-9a-fA-F]{6}", lang.get("color", "")):
            raise ValueError("Languages need a name and a six-digit hex color")
        if type(lang.get("repositories")) is not int or lang["repositories"] <= 0:
            raise ValueError("Language repository weight must be a positive integer")
    return stats


def normalize(value: int, ceiling: float) -> float:
    return min(1.0, math.log1p(value) / math.log1p(ceiling))


def parameters(stats: dict, config: dict) -> dict:
    validate_stats(stats)
    s, a = config["scales"], config["appearance"]
    n = {k: normalize(stats[k], ceiling) for k, ceiling in s.items()}
    def count(lo, hi, value): return int(math.floor(lo + (hi - lo) * value + .5))
    result = {
        "seed": stable_seed(str(config["seed"]) if config["seed"] is not None else stats["username"].lower()),
        "building_count": count(a["min_buildings"], a["max_buildings"], n["public_repositories"]),
        "skyline_height": round(a["min_height"] + (a["max_height"] - a["min_height"]) * n["commits"], 2),
        "window_light_rate": round(a["min_window_light"] + (a["max_window_light"] - a["min_window_light"]) * n["recent_activity"], 4),
        "neon_buildings": count(0, 9, n["pull_requests"]),
        "rooftop_beacons": count(0, 9, n["reviews"]),
        "car_count": count(0, 16, n["recent_activity"]),
        "star_count": count(30, 150, n["stars"]),
        "tree_count": count(6, 20, min(1, stats["active_days"] / 250)),
        "accent": a["accent"],
    }
    limits = {"building_count": (1, 9, int), "skyline_height": (32, 350, float), "window_light_rate": (0, 1, float),
              "neon_buildings": (0, 9, int), "rooftop_beacons": (0, 9, int), "car_count": (0, 16, int),
              "star_count": (0, 150, int), "tree_count": (0, 20, int)}
    for k, v in config["overrides"].items():
        if k not in limits:
            raise ValueError(f"Unknown override: {k}")
        lo, hi, kind = limits[k]
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or not lo <= v <= hi or (kind is int and type(v) is not int):
            raise ValueError(f"Override {k} must be between {lo} and {hi}")
        result[k] = v
    result["neon_buildings"] = min(result["neon_buildings"], result["building_count"])
    result["rooftop_beacons"] = min(result["rooftop_beacons"], result["building_count"])
    return result


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as f:
        temporary = Path(f.name)
        try:
            f.write(content)
            f.flush()
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path(__file__).with_name("city.config.json"))
    parser.add_argument("--username")
    parser.add_argument("--stats-file", type=Path, help="Offline JSON input; no network or token needed")
    parser.add_argument("--output", type=Path, default=Path("dist/city.svg"))
    parser.add_argument("--export-parameters", type=Path)
    args = parser.parse_args(argv)
    try:
        config = load_config(args.config)
        if args.stats_file:
            stats = validate_stats(json.loads(args.stats_file.read_text(encoding="utf-8")))
            if args.username:
                stats["username"] = args.username
        else:
            token = os.environ.get("GH_CITY_TOKEN", "")
            if not token:
                raise RuntimeError("Set the GH_CITY_TOKEN Actions secret (or environment variable)")
            stats = fetch_stats(args.username or config["username"], token)
        params = parameters(stats, config)
        from city_renderer import render_city
        svg = render_city(stats, params)
        atomic_write(args.output, svg)
        if args.export_parameters:
            atomic_write(args.export_parameters, json.dumps(params, indent=2) + "\n")
        print(f"Generated {args.output}: {params['building_count']} buildings; data source: {stats.get('source', 'offline')}")
        return 0
    except (ValueError, KeyError, TypeError, OSError, RuntimeError) as exc:
        print(f"City generation failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
