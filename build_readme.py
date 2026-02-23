"""Rebuild profile README with latest blog posts, releases, and projects."""
import feedparser
import pathlib
import requests
import os
from datetime import datetime

ROOT = pathlib.Path(__file__).parent
USERNAME = "Michaelliv"
SKIP_REPOS = {"Michaelliv", "blog", "dotskills"}
CONTRIB_ORGS = ["the-shift-dev"]


def gh_headers():
    token = os.environ.get("GH_TOKEN", "")
    return {"Authorization": f"token {token}"} if token else {}


# --- Blog posts from RSS ---
def fetch_blog_posts(n=5):
    feed = feedparser.parse("https://michaellivs.com/rss.xml")
    entries = []
    for entry in feed.entries[:n]:
        date = datetime(*entry.published_parsed[:3]).strftime("%Y-%m-%d")
        entries.append(f"[{entry.title}]({entry.link}) - {date}")
    return "\n\n".join(entries)


# --- Recent releases from GitHub ---
def fetch_releases(n=8):
    headers = gh_headers()
    repos = requests.get(
        f"https://api.github.com/users/{USERNAME}/repos?sort=updated&per_page=50",
        headers=headers,
    ).json()

    releases = []
    for repo in repos:
        if repo.get("fork"):
            continue
        rel_url = f"https://api.github.com/repos/{USERNAME}/{repo['name']}/releases?per_page=3"
        for rel in requests.get(rel_url, headers=headers).json():
            if isinstance(rel, dict) and rel.get("tag_name"):
                date = rel["published_at"][:10]
                releases.append({
                    "text": f"[{repo['name']} {rel['tag_name']}](https://github.com/{USERNAME}/{repo['name']}/releases/tag/{rel['tag_name']}) - {date}",
                    "date": date,
                })

    releases.sort(key=lambda r: r["date"], reverse=True)
    return "\n\n".join(r["text"] for r in releases[:n])


# --- Projects table from GitHub repos ---
def fetch_projects(min_stars=0):
    headers = gh_headers()
    repos = requests.get(
        f"https://api.github.com/users/{USERNAME}/repos?per_page=100",
        headers=headers,
    ).json()

    projects = []
    for repo in repos:
        if repo.get("fork") or repo["name"] in SKIP_REPOS:
            continue
        if not repo.get("description"):
            continue
        if repo.get("stargazers_count", 0) < min_stars:
            continue
        # Clean emoji prefix from description
        desc = repo["description"].lstrip("🤫 ")
        projects.append({
            "name": repo["name"],
            "stars": repo.get("stargazers_count", 0),
            "desc": desc,
            "url": repo["html_url"],
        })

    # Also include public repos from orgs where USERNAME is a contributor
    for org in CONTRIB_ORGS:
        org_repos = requests.get(
            f"https://api.github.com/orgs/{org}/repos?type=public&per_page=100",
            headers=headers,
        ).json()
        for repo in org_repos:
            if repo.get("fork") or repo["name"] in SKIP_REPOS:
                continue
            if not repo.get("description"):
                continue
            if repo.get("stargazers_count", 0) < min_stars:
                continue
            # Check if USERNAME is a contributor
            contributors = requests.get(
                f"https://api.github.com/repos/{org}/{repo['name']}/contributors",
                headers=headers,
            ).json()
            if not any(c.get("login") == USERNAME for c in contributors if isinstance(c, dict)):
                continue
            desc = repo["description"].lstrip("🤫 ")
            projects.append({
                "name": repo["name"],
                "stars": repo.get("stargazers_count", 0),
                "desc": desc,
                "url": repo["html_url"],
            })

    projects.sort(key=lambda p: p["stars"], reverse=True)

    # Build markdown table
    lines = ["| Project | What it does | ★ |", "|---------|-------------|---|"]
    for p in projects:
        desc = p["desc"]
        if len(desc) > 60:
            desc = desc[:59].rstrip() + "…"
        star_str = str(p["stars"]) if p["stars"] > 0 else ""
        lines.append(f"| [{p['name']}]({p['url']}) | {desc} | {star_str} |")
    return "\n".join(lines)


# --- Build README ---
def build():
    posts = fetch_blog_posts()
    releases = fetch_releases()
    projects = fetch_projects()

    template = ROOT / "README.md"
    content = template.read_text()

    # Replace between markers
    for section, data in [("blog", posts), ("releases", releases), ("projects", projects)]:
        start = f"<!-- {section} starts -->"
        end = f"<!-- {section} ends -->"
        if start in content and end in content:
            content = content[:content.index(start) + len(start)] + "\n" + data + "\n" + content[content.index(end):]

    template.write_text(content)
    print("README.md updated")


if __name__ == "__main__":
    build()
