"""Rebuild profile README with latest blog posts and releases."""
import feedparser
import pathlib
import requests
import os
from datetime import datetime

ROOT = pathlib.Path(__file__).parent

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
    token = os.environ.get("GH_TOKEN", "")
    headers = {"Authorization": f"token {token}"} if token else {}
    repos = requests.get(
        "https://api.github.com/users/Michaelliv/repos?sort=updated&per_page=50",
        headers=headers,
    ).json()
    
    releases = []
    for repo in repos:
        if repo.get("fork"):
            continue
        rel_url = f"https://api.github.com/repos/Michaelliv/{repo['name']}/releases?per_page=3"
        for rel in requests.get(rel_url, headers=headers).json():
            if isinstance(rel, dict) and rel.get("tag_name"):
                date = rel["published_at"][:10]
                releases.append({
                    "text": f"[{repo['name']} {rel['tag_name']}](https://github.com/Michaelliv/{repo['name']}/releases/tag/{rel['tag_name']}) - {date}",
                    "date": date,
                })
    
    releases.sort(key=lambda r: r["date"], reverse=True)
    return "\n\n".join(r["text"] for r in releases[:n])

# --- Build README ---
def build():
    posts = fetch_blog_posts()
    releases = fetch_releases()
    
    template = ROOT / "README.md"
    content = template.read_text()
    
    # Replace between markers
    for section, data in [("blog", posts), ("releases", releases)]:
        start = f"<!-- {section} starts -->"
        end = f"<!-- {section} ends -->"
        content = content[:content.index(start) + len(start)] + "\n" + data + "\n" + content[content.index(end):]
    
    template.write_text(content)
    print("README.md updated")

if __name__ == "__main__":
    build()
