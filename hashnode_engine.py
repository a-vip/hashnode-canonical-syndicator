#!/usr/bin/env python3
"""
hashnode_engine.py
Autonomous Hashnode Canonical Syndicator & SEO Authority Booster for aviperera.com.
Syndicates newly published research and essays to Hashnode via their official GraphQL API.
Always sets originalArticleURL pointing back to aviperera.com, transferring 100% of the SEO domain
authority directly to your origin publication with zero duplicate content penalties.
"""

import os
import sys
import json
import html
import re
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

HASHNODE_GQL_ENDPOINT = "https://gql.hashnode.com"
RSS_FEED_URL = "https://aviperera.com/feed/"
STATE_FILE = os.path.join(os.path.dirname(__file__), "state", "hashnode_history.json")

BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/rss+xml, application/xml, text/xml, application/json, */*"
}

DEFAULT_TAGS = [
    {"slug": "artificial-intelligence", "name": "Artificial Intelligence"},
    {"slug": "ai-ethics", "name": "AI Ethics"},
    {"slug": "technology", "name": "Technology"},
    {"slug": "governance", "name": "Governance"}
]

class HTMLToMarkdownParser(HTMLParser):
    """Converts HTML markup into clean GitHub-flavored Markdown for Hashnode."""
    def __init__(self):
        super().__init__()
        self.output = []
        self.href_stack = []
        self.tag_stack = []
        self.in_pre = False

    def handle_starttag(self, tag, attrs):
        self.tag_stack.append(tag)
        attrs_dict = dict(attrs)

        if tag in ("h1", "h2", "h3", "h4"):
            level = {"h1": "## ", "h2": "## ", "h3": "### ", "h4": "#### "}[tag]
            self.output.append(f"\n\n{level}")
        elif tag == "p":
            self.output.append("\n\n")
        elif tag in ("strong", "b"):
            self.output.append("**")
        elif tag in ("em", "i"):
            self.output.append("*")
        elif tag == "a":
            href = attrs_dict.get("href", "")
            self.href_stack.append(href)
            self.output.append("[")
        elif tag == "blockquote":
            self.output.append("\n\n> ")
        elif tag == "li":
            self.output.append("\n- ")
        elif tag == "code":
            if not self.in_pre:
                self.output.append("`")
        elif tag == "pre":
            self.in_pre = True
            self.output.append("\n\n```text\n")
        elif tag == "img":
            src = attrs_dict.get("src", "")
            alt = attrs_dict.get("alt", "image")
            if src:
                self.output.append(f"\n\n![{alt}]({src})\n\n")

    def handle_endtag(self, tag):
        if self.tag_stack and self.tag_stack[-1] == tag:
            self.tag_stack.pop()

        if tag in ("strong", "b"):
            self.output.append("**")
        elif tag in ("em", "i"):
            self.output.append("*")
        elif tag == "a":
            href = self.href_stack.pop() if self.href_stack else ""
            self.output.append(f"]({href})")
        elif tag == "code":
            if not self.in_pre:
                self.output.append("`")
        elif tag == "pre":
            self.in_pre = False
            self.output.append("\n```\n\n")

    def handle_data(self, data):
        self.output.append(data)

    def get_markdown(self) -> str:
        text = "".join(self.output)
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        return text

def html_to_markdown(html_content: str) -> str:
    if not html_content:
        return ""
    parser = HTMLToMarkdownParser()
    try:
        parser.feed(html_content)
        return parser.get_markdown()
    except Exception:
        clean = re.sub(r"<[^>]+>", " ", html_content)
        return html.unescape(clean).strip()

def clean_text(raw_html: str) -> str:
    if not raw_html:
        return ""
    clean = re.sub(r"<[^>]+>", " ", raw_html)
    clean = html.unescape(clean)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean

def format_hashnode_tags(categories: List[str]) -> List[Dict[str, str]]:
    """Converts categories into Hashnode TagInput objects."""
    tags = []
    seen = set()
    for cat in categories:
        clean = clean_text(cat)
        slug = re.sub(r"[^a-zA-Z0-9]+", "-", clean.lower()).strip("-")
        if slug and slug not in seen:
            seen.add(slug)
            tags.append({"slug": slug, "name": clean[:30]})
            if len(tags) >= 4:
                break
    for d in DEFAULT_TAGS:
        if len(tags) >= 4:
            break
        if d["slug"] not in seen:
            seen.add(d["slug"])
            tags.append(d)
    return tags[:4]

def load_state() -> dict:
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "syndicated" not in data:
                    data["syndicated"] = {}
                return data
        except Exception as e:
            print(f"[!] Warning reading state ({e}). Starting fresh.")
    return {"syndicated": {}, "last_run": None}

def save_state(state: dict):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)

def fetch_from_rss() -> List[Dict[str, Any]]:
    """Fetches full post bodies and metadata from RSS feed."""
    try:
        req = urllib.request.Request(RSS_FEED_URL, headers=BROWSER_HEADERS)
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw_xml = resp.read().decode("utf-8", errors="replace")
            clean_xml = re.sub(r"</?([a-zA-Z0-9_-]+):", lambda m: "</" if m.group(0).startswith("</") else "<", raw_xml)
            root = ET.fromstring(clean_xml)
            posts = []
            for item in root.findall(".//item"):
                guid_el = item.find("guid")
                title_el = item.find("title")
                link_el = item.find("link")
                desc_el = item.find("description")
                content_el = item.find("encoded")

                guid = guid_el.text.strip() if guid_el is not None and guid_el.text else ""
                title = clean_text(title_el.text) if title_el is not None and title_el.text else ""
                link = link_el.text.strip() if link_el is not None and link_el.text else ""
                desc = desc_el.text if desc_el is not None and desc_el.text else ""
                content = content_el.text if content_el is not None and content_el.text else ""

                categories = []
                for cat in item.findall("category"):
                    if cat.text:
                        categories.append(clean_text(cat.text))

                image_url = ""
                enclosure = item.find("enclosure")
                if enclosure is not None and "image" in enclosure.get("type", ""):
                    image_url = enclosure.get("url", "").strip()

                post_id = guid if guid else link
                if title and link:
                    posts.append({
                        "id": post_id,
                        "title": title,
                        "link": link,
                        "description": desc,
                        "content_html": content if content else desc,
                        "categories": categories,
                        "image_url": image_url
                    })
            return posts
    except Exception as e:
        print(f"[!] Primary RSS discovery notice: {e}")
        return []

def execute_gql(token: str, query: str, variables: Optional[dict] = None) -> Tuple[bool, dict]:
    """Sends authenticated GraphQL query to Hashnode GQL endpoint."""
    headers = {
        "Authorization": token.strip(),
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "AviHashnodeSyndicator/1.0"
    }
    payload = {"query": query}
    if variables:
        payload["variables"] = variables
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(HASHNODE_GQL_ENDPOINT, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            res_data = json.loads(resp.read().decode("utf-8"))
            if "errors" in res_data:
                print(f"[!] Hashnode GQL Errors: {res_data['errors']}")
                return False, res_data
            return True, res_data.get("data", {})
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="replace")
        print(f"[!] Hashnode HTTP Error {e.code}: {err}")
        return False, {"error": err}
    except Exception as e:
        print(f"[!] Hashnode Exception: {e}")
        return False, {"error": str(e)}

DEFAULT_PUBLICATION_ID = "6a33eb282dbde43083373bb4"
DEFAULT_HOST = "aviperera.hashnode.dev"

def auto_detect_publication(token: str, host: str = DEFAULT_HOST) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Retrieves authenticated author and primary publication ID via me query or host fallback."""
    query_me = """
    query GetMe {
      me {
        id
        username
      }
    }
    """
    ok, data = execute_gql(token, query_me)
    username = data.get("me", {}).get("username", "a-vip") if ok else "a-vip"

    # Query publication by host
    query_host = """
    query GetPubByHost($host: String!) {
      publication(host: $host) {
        id
        title
        url
      }
    }
    """
    ok_host, data_host = execute_gql(token, query_host, {"host": host})
    if ok_host and data_host.get("publication"):
        pub = data_host["publication"]
        return pub.get("id"), pub.get("title", "Avi Perera"), username

    return DEFAULT_PUBLICATION_ID, "Avi Perera", username

def build_hashnode_input(post: dict, publication_id: str) -> dict:
    """Constructs PublishPostInput with canonical link and attribution."""
    title = post["title"]
    canonical_url = post["link"].split("?")[0].rstrip("/") + "/"
    raw_html = post.get("content_html", "")
    markdown_body = html_to_markdown(raw_html)

    citation_footer = (
        f"\n\n---\n\n"
        f"*This research dossier was originally published on "
        f"[**aviperera.com**]({canonical_url}) by Avi Perera. "
        f"All canonical attribution and primary indexing belong to the origin domain.*"
    )
    full_markdown = f"{markdown_body}\n\n{citation_footer}"
    tags = format_hashnode_tags(post.get("categories", []))

    input_data = {
        "title": title,
        "contentMarkdown": full_markdown,
        "publicationId": publication_id,
        "originalArticleURL": canonical_url,
        "tags": tags,
        "subtitle": clean_text(post.get("description", ""))[:120]
    }
    if post.get("image_url"):
        input_data["coverImageOptions"] = {"coverImageURL": post["image_url"]}

    return input_data

def publish_to_hashnode(token: str, post_input: dict) -> Tuple[bool, Optional[str], Optional[str]]:
    """Calls Hashnode GraphQL publishPost mutation."""
    mutation = """
    mutation PublishPost($input: PublishPostInput!) {
      publishPost(input: $input) {
        post {
          id
          title
          slug
          url
        }
      }
    }
    """
    ok, data = execute_gql(token, mutation, {"input": post_input})
    if not ok:
        return False, None, None
    post_res = data.get("publishPost", {}).get("post", {})
    post_id = post_res.get("id")
    post_url = post_res.get("url")
    print(f"[OK] Successfully syndicated to Hashnode: {post_url} (ID: {post_id})")
    return True, post_id, post_url

def main() -> int:
    print("=== Autonomous Hashnode Canonical Syndicator & SEO Authority Booster ===")
    state = load_state()
    posts = fetch_from_rss()
    print(f"Retrieved {len(posts)} publications from aviperera.com")

    token = os.getenv("HASHNODE_TOKEN", "").strip()
    pub_id = os.getenv("HASHNODE_PUBLICATION_ID", DEFAULT_PUBLICATION_ID).strip()

    force_dry_run = "--dry-run" in sys.argv
    has_credentials = bool(token)
    dry_run = force_dry_run or not has_credentials

    author_username = None
    pub_title = None
    if has_credentials and not force_dry_run:
        detected_pub_id, pub_title, author_username = auto_detect_publication(token)
        if not pub_id and detected_pub_id:
            pub_id = detected_pub_id
        if not pub_id:
            print("[!] Could not resolve publication ID. Reverting to dry-run preview.")
            dry_run = True
        else:
            print(f"[OK] Authenticated Hashnode Author @{author_username} | Publication: '{pub_title}' (ID: {pub_id})")

    if dry_run:
        print("[!] Running in PREVIEW / DRY-RUN mode.")
        if not has_credentials:
            print("    Reason: Missing HASHNODE_TOKEN repository secret.")

    unsyndicated = [p for p in posts if p["id"] not in state["syndicated"] and p["link"] not in state["syndicated"]]
    print(f"Publications pending Hashnode canonical syndication: {len(unsyndicated)}")

    processed_items = []

    # Syndicate 1 article per scheduled run for optimal pacing
    for post in unsyndicated[:1]:
        title = post["title"]
        pid = post["id"]
        canonical_url = post["link"]
        post_input = build_hashnode_input(post, publication_id=pub_id or "DEMO_PUB_ID")

        item_summary = {
            "title": title,
            "canonical_url": canonical_url,
            "tags": [t["name"] for t in post_input["tags"]],
            "status": "Dry-Run Preview",
            "hashnode_url": None
        }

        if dry_run:
            print(f"\n[DRY-RUN HASHNODE PREVIEW]")
            print(f"Title: {post_input['title']}")
            print(f"Canonical URL: {post_input['originalArticleURL']}")
            print(f"Tags: {', '.join([t['name'] for t in post_input['tags']])}")
            print(f"Markdown Content length: {len(post_input['contentMarkdown'])} chars")
            processed_items.append(item_summary)
            continue

        # Live Submission
        success, hashnode_id, hashnode_url = publish_to_hashnode(token, post_input)
        if success:
            state["syndicated"][pid] = {
                "title": title,
                "canonical_url": canonical_url,
                "hashnode_id": hashnode_id,
                "hashnode_url": hashnode_url,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            state["last_run"] = datetime.now(timezone.utc).isoformat()
            save_state(state)
            item_summary["status"] = "Syndicated"
            item_summary["hashnode_url"] = hashnode_url
            processed_items.append(item_summary)
        else:
            item_summary["status"] = "Failed"
            processed_items.append(item_summary)

    output_step_summary(processed_items, dry_run=dry_run, has_credentials=has_credentials)
    return 0

def output_step_summary(items: list, dry_run: bool, has_credentials: bool):
    summary_path = os.getenv("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return

    with open(summary_path, "a", encoding="utf-8") as f:
        f.write("## 🚀 Hashnode Canonical Syndicator & SEO Authority Booster\n\n")
        mode_badge = "🟡 *DRY-RUN / PREVIEW*" if dry_run else "🟢 *LIVE HASHNODE SYNDICATION SUCCESS*"
        f.write(f"**Execution Mode:** {mode_badge}\n\n")
        f.write(f"- **Hashnode Credentials:** {'✅ Configured' if has_credentials else '❌ Missing HASHNODE_TOKEN'}\n\n")

        if not items:
            f.write("✅ All recent publications are already syndicated to Hashnode. Zero pending items.\n")
            return

        f.write(f"### Processed Publication ({len(items)} item):\n\n")
        f.write("| Title | Canonical Origin | Hashnode URL | Status |\n")
        f.write("| :--- | :--- | :--- | :--- |\n")
        for it in items:
            h_link = f"[View on Hashnode]({it['hashnode_url']})" if it.get("hashnode_url") else "`N/A`"
            f.write(f"| {it['title']} | [{it['canonical_url']}]({it['canonical_url']}) | {h_link} | `{it['status']}` |\n")

if __name__ == "__main__":
    sys.exit(main())

