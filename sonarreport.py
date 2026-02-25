import os
import json
import argparse
import requests

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None


DEFAULT_METRICS = ",".join(
    [
        "bugs",
        "vulnerabilities",
        "code_smells",
        "security_hotspots",
        "coverage",
        "duplicated_lines_density",
        "ncloc",
        "reliability_rating",
        "security_rating",
        "sqale_rating",
    ]
)


def get_json(session, base_url, path, params=None):
    url = f"{base_url.rstrip('/')}{path}"
    r = session.get(url, params=params, timeout=90)
    r.raise_for_status()
    return r.json()


def get_text(session, base_url, path, params=None):
    url = f"{base_url.rstrip('/')}{path}"
    r = session.get(url, params=params, timeout=90)
    r.raise_for_status()
    return r.text


def paged(session, base_url, path, params=None, list_key=None, page_size=500):
    params = dict(params or {})
    page = 1
    out = []
    while True:
        page_params = {**params, "p": page, "ps": page_size}
        data = get_json(session, base_url, path, page_params)
        if list_key is None:
            list_key = next((k for k, v in data.items() if isinstance(v, list)), None)
        items = data.get(list_key, []) if list_key else []
        out.extend(items)
        paging = data.get("paging", {})
        total = paging.get("total")
        if total is None:
            if not items:
                break
        else:
            if page * page_size >= total:
                break
        page += 1
    return out


def main():
    if load_dotenv is not None:
        load_dotenv()

    parser = argparse.ArgumentParser(description="Export one SonarQube project report JSON for AI code fixing")
    parser.add_argument("--url", default=os.getenv("SONAR_URL"), help="SonarQube URL")
    parser.add_argument("--token", default=os.getenv("SONAR_TOKEN"), help="SonarQube token")
    parser.add_argument("--project-key", required=True, help="SonarQube project key")
    parser.add_argument("--output", default="sonar_single_project_report.json", help="Output JSON file")
    parser.add_argument("--metrics", default=DEFAULT_METRICS, help="Comma-separated metric keys")
    parser.add_argument("--include-source", action="store_true", help="Include raw source of affected files")
    parser.add_argument("--max-source-chars", type=int, default=120000, help="Max chars per source file")
    args = parser.parse_args()
    if not args.url or not args.token:
        raise SystemExit("Missing --url/--token (or SONAR_URL/SONAR_TOKEN env vars).")
    s = requests.Session()
    s.auth = (args.token, "")  # Sonar token auth
    project_key = args.project_key
    # Core report data
    quality_gate = get_json(s, args.url, "/api/qualitygates/project_status", {"projectKey": project_key})
    measures = get_json(s, args.url, "/api/measures/component", {"component": project_key, "metricKeys": args.metrics})
    # Important: additionalFields=_all gives richer issue context for fixing
    issues = paged(
        s,
        args.url,
        "/api/issues/search",
        params={"componentKeys": project_key, "resolved": "false", "additionalFields": "_all"},
        list_key="issues",
        page_size=500,
    )

    hotspots = []
    hotspots_error = None
    try:
        hotspots = paged(
            s, args.url, "/api/hotspots/search", params={"projectKey": project_key}, list_key="hotspots", page_size=500
        )
    except requests.HTTPError as exc:
        status_code = exc.response.status_code if exc.response is not None else None
        if status_code == 403:
            hotspots_error = (
                "403 Forbidden on /api/hotspots/search "
                "(missing Security Hotspots permission or endpoint unavailable for this token)"
            )
        else:
            raise

    report = {
        "sonarqube_url": args.url.rstrip("/"),
        "project_key": project_key,
        "quality_gate": quality_gate,
        "measures": measures,
        "issue_count": len(issues),
        "hotspot_count": len(hotspots),
        "hotspot_error": hotspots_error,
        "issues": issues,
        "hotspots": hotspots,
    }
    # Optional: include source for affected files only (helps AI propose exact patches)
    if args.include_source:
        affected_components = set()
        for i in issues:
            comp = i.get("component")
            if comp:
                affected_components.add(comp)
        for h in hotspots:
            comp = h.get("component")
            if comp:
                affected_components.add(comp)
        sources = {}
        for comp in sorted(affected_components):
            try:
                raw = get_text(s, args.url, "/api/sources/raw", {"key": comp})
                if len(raw) > args.max_source_chars:
                    raw = raw[: args.max_source_chars] + "\n\n...[TRUNCATED]..."
                sources[comp] = raw
            except Exception as e:
                sources[comp] = f"[SOURCE_FETCH_FAILED] {e}"
        report["affected_file_sources"] = sources
        report["affected_file_count"] = len(affected_components)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"Saved: {args.output}")
    print(f"Issues: {len(issues)} | Hotspots: {len(hotspots)}")
    if hotspots_error:
        print(f"Hotspots warning: {hotspots_error}")


if __name__ == "__main__":
    main()
