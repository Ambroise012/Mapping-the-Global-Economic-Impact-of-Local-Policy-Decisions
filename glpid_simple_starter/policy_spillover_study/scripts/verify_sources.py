import hashlib
from html.parser import HTMLParser
import os
from pathlib import Path
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

import psycopg
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]
USER_AGENT = "GLPID policy-spillover source-check/1.0"
REQUEST_TIMEOUT = 30
MAX_ATTEMPTS = 3
MIN_HOST_DELAY_SECONDS = 1.5


class PageMetadata(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title_parts = []
        self.title_open = False
        self.meta = {}

    def handle_starttag(self, tag, attrs):
        values = {key.lower(): value for key, value in attrs if key and value}
        if tag.lower() == "title":
            self.title_open = True
        if tag.lower() == "meta":
            name = values.get("name", "").lower()
            property_name = values.get("property", "").lower()
            content = values.get("content", "").strip()
            if content and name == "description":
                self.meta["description"] = content
            elif content and property_name == "og:title" and not self.meta.get("title"):
                self.meta["title"] = content
            elif content and property_name == "og:description" and not self.meta.get("description"):
                self.meta["description"] = content

    def handle_endtag(self, tag):
        if tag.lower() == "title":
            self.title_open = False

    def handle_data(self, data):
        if self.title_open and data.strip():
            self.title_parts.append(data.strip())

    @property
    def title(self):
        return " ".join(self.title_parts).strip() or self.meta.get("title")


def connect():
    load_dotenv(PROJECT_ROOT / ".env")
    required = ("PGHOST", "PGPORT", "PGDATABASE", "PGUSER", "PGPASSWORD")
    missing = [key for key in required if not os.getenv(key)]
    if missing:
        raise RuntimeError("Paramètres PostgreSQL manquants dans .env : " + ", ".join(missing))
    return psycopg.connect(
        host=os.environ["PGHOST"],
        port=int(os.environ["PGPORT"]),
        dbname=os.environ["PGDATABASE"],
        user=os.environ["PGUSER"],
        **{"password": os.environ["PGPASSWORD"]},
    )


def parse_metadata(body, content_type):
    if content_type and "html" not in content_type.lower():
        return None, None
    parser = PageMetadata()
    parser.feed(body.decode("utf-8", "replace"))
    description = parser.meta.get("description")
    if description:
        description = " ".join(description.split())[:1000]
    return parser.title, description


def parse_retry_after(value):
    if value and value.isdigit():
        return min(max(int(value), 1), 300)
    return None


def fetch_page(url):
    request = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.5",
        },
    )
    for attempt in range(MAX_ATTEMPTS):
        try:
            with urlopen(request, timeout=REQUEST_TIMEOUT) as response:
                body = response.read()
                content_type = response.headers.get("Content-Type")
                metadata = parse_metadata(body, content_type)
                status = response.status
                response_url = response.geturl()
                if status != 200:
                    return {
                        "http_status": status,
                        "final_url": response_url,
                        "content_type": content_type,
                        "page_title": None,
                        "meta_description": None,
                        "content_sha256": None,
                        "error_text": (
                            f"HTTP {status}: réponse reçue, mais document non validé."
                        ),
                    }
                return {
                    "http_status": status,
                    "final_url": response_url,
                    "content_type": content_type,
                    "page_title": metadata[0],
                    "meta_description": metadata[1],
                    "content_sha256": hashlib.sha256(body).hexdigest(),
                    "error_text": None,
                }
        except HTTPError as exc:
            if exc.code in (429, 500, 502, 503, 504) and attempt < MAX_ATTEMPTS - 1:
                wait = parse_retry_after(exc.headers.get("Retry-After"))
                time.sleep(wait if wait is not None else 2 ** (attempt + 1))
                continue
            return {
                "http_status": exc.code,
                "final_url": exc.geturl(),
                "content_type": exc.headers.get("Content-Type"),
                "page_title": None,
                "meta_description": None,
                "content_sha256": None,
                "error_text": f"HTTP {exc.code}: {str(exc.reason)[:500]}",
            }
        except (URLError, TimeoutError, OSError) as exc:
            if attempt < MAX_ATTEMPTS - 1:
                time.sleep(2 ** (attempt + 1))
                continue
            return {
                "http_status": None,
                "final_url": url,
                "content_type": None,
                "page_title": None,
                "meta_description": None,
                "content_sha256": None,
                "error_text": f"{type(exc).__name__}: {str(exc)[:500]}",
            }
    raise RuntimeError(f"Épuisement inattendu des tentatives pour {url}")


def load_sources():
    with connect() as conn:
        return conn.execute(
            """
            SELECT DISTINCT s.source_id, s.url
            FROM sources s
            JOIN policy_diffusion_events e ON e.source_id = s.source_id
            WHERE s.url LIKE 'https://%'
            ORDER BY s.source_id
            """
        ).fetchall()


def persist_check(source_id, result):
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO policy_diffusion_source_checks
                    (source_id, http_status, final_url, content_type, page_title,
                     meta_description, content_sha256, error_text)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    source_id,
                    result["http_status"],
                    result["final_url"],
                    result["content_type"],
                    result["page_title"],
                    result["meta_description"],
                    result["content_sha256"],
                    result["error_text"],
                ),
            )
            if result["http_status"] == 200 and not result["error_text"]:
                cur.execute(
                    "UPDATE sources SET accessed_at = CURRENT_DATE WHERE source_id = %s",
                    (source_id,),
                )


def main():
    try:
        sources = load_sources()
        if not sources:
            raise RuntimeError("Aucune source HTTPS à vérifier. Exécutez seed_study.py.")
        previous_host = None
        successful = 0
        failed = 0
        for index, (source_id, url) in enumerate(sources):
            host = urlparse(url).netloc.lower()
            if previous_host is not None:
                time.sleep(MIN_HOST_DELAY_SECONDS if host == previous_host else 0.5)
            result = fetch_page(url)
            persist_check(source_id, result)
            if result["error_text"]:
                failed += 1
                print(f"{source_id}: échec vérifiable — {result['error_text']}")
            else:
                successful += 1
                title = result["page_title"] or "(titre absent)"
                print(f"{source_id}: HTTP {result['http_status']} — {title}")
            previous_host = host
        print(
            f"Vérification terminée : {successful} succès HTTP, {failed} échecs "
            f"sur {len(sources)} sources. Aucune page complète n’est stockée."
        )
    except (RuntimeError, psycopg.Error) as exc:
        print(f"Erreur : {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
