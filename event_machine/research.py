"""Small, auditable website researcher. Network failure never becomes a fact."""

from __future__ import annotations

import re
import ipaddress
import socket
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser


MAX_BYTES = 1_000_000
LINK_TERMS = ("programme", "programmation", "agenda", "speaker", "confer", "expos", "partner", "partenaire", "schedule")
THEMES = {
    "intelligence artificielle": ("intelligence artificielle", " ai ", " ia ", "artificial intelligence"),
    "commerce numérique": ("e-commerce", "commerce électronique", "commerce en ligne", "omnichannel", "omnicanal"),
    "expérience client": ("expérience client", "customer experience", "fidélisation", "loyalty"),
    "marketing et données": ("marketing", "publicité", "advertising", "analytics", "données clients"),
    "opérations": ("opérations", "operations", "supply chain", "logistique"),
    "talents et RH": ("ressources humaines", "recrutement", "talent", "human resources"),
    "durabilité": ("durabilité", "sustainability", "circular", "circulaire"),
}


def utc_date() -> str:
    return datetime.now(timezone.utc).date().isoformat()


class Extractor(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.links: list[tuple[str, str]] = []
        self.title = ""
        self._skip = 0
        self._in_title = False
        self._href: str | None = None
        self._anchor: list[str] = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag in ("script", "style", "svg", "noscript"):
            self._skip += 1
        if tag == "title":
            self._in_title = True
        if tag == "a":
            self._href = values.get("href")
            self._anchor = []

    def handle_endtag(self, tag):
        if tag in ("script", "style", "svg", "noscript"):
            self._skip = max(0, self._skip - 1)
        if tag == "title":
            self._in_title = False
        if tag == "a" and self._href:
            self.links.append((self._href, " ".join(self._anchor).strip()))
            self._href = None

    def handle_data(self, data):
        value = " ".join(data.split())
        if not value or self._skip:
            return
        if self._in_title:
            self.title += value + " "
        if self._href:
            self._anchor.append(value)
        self.parts.append(value)


def fetch_page(url: str, timeout: int = 12) -> dict:
    validate_public_url(url)
    parsed = urllib.parse.urlparse(url)
    request = urllib.request.Request(url, headers={"User-Agent": "BETA-Labs-EventResearch/0.1 (+internal analyst)"})
    with urllib.request.build_opener(SafeRedirect()).open(request, timeout=timeout) as response:
        content_type = response.headers.get("Content-Type", "")
        if "html" not in content_type.lower():
            raise ValueError("Expected an HTML page")
        raw = response.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise ValueError("Page exceeds research size limit")
        final_url = response.geturl()
        validate_public_url(final_url)
        charset = response.headers.get_content_charset() or "utf-8"
    extractor = Extractor()
    extractor.feed(raw.decode(charset, errors="replace"))
    return {
        "url": final_url,
        "title": extractor.title.strip(),
        "text": " ".join(extractor.parts)[:80_000],
        "links": extractor.links,
        "checked_at": utc_date(),
        "source_type": "live_web",
    }


def validate_public_url(url: str) -> None:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Only public HTTP(S) URLs are supported")
    if parsed.port not in (None, 80, 443):
        raise ValueError("Only standard HTTP(S) ports are supported")
    try:
        addresses = socket.getaddrinfo(parsed.hostname, parsed.port or (443 if parsed.scheme == "https" else 80))
    except socket.gaierror as exc:
        raise ValueError("Hostname could not be resolved") from exc
    if not addresses or any(not ipaddress.ip_address(item[4][0]).is_global for item in addresses):
        raise ValueError("Private or non-public destination blocked")


class SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        validate_public_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def research_event(event: dict, max_pages: int = 6, allow_network: bool = True) -> tuple[list[dict], list[dict]]:
    """Return pages and errors; source snapshots are accepted when network is unavailable."""
    pages: list[dict] = []
    errors: list[dict] = []
    for item in event.get("reference_pages", []):
        if item.get("url") and item.get("text"):
            pages.append({"url": item["url"], "title": item.get("title", ""),
                          "text": item["text"], "links": [],
                          "checked_at": item.get("checked_at", ""),
                          "source_type": "supplied_snapshot"})
    root = event.get("url", "")
    if not allow_network or not root:
        return pages, errors
    root_host = urllib.parse.urlparse(root).hostname or ""
    queue = [root] + list(event.get("research_urls", []))
    visited = {p["url"] for p in pages}
    while queue and len([p for p in pages if p["source_type"] == "live_web"]) < max_pages:
        url = queue.pop(0)
        if url in visited:
            continue
        visited.add(url)
        if (urllib.parse.urlparse(url).hostname or "") != root_host:
            continue
        try:
            page = fetch_page(url)
        except (OSError, ValueError, UnicodeError, urllib.error.URLError) as exc:
            errors.append({"url": url, "error": type(exc).__name__, "detail": str(exc)[:180]})
            continue
        pages.append(page)
        for href, label in page["links"]:
            linked = urllib.parse.urljoin(page["url"], href).split("#", 1)[0]
            parsed = urllib.parse.urlparse(linked)
            if parsed.scheme in ("http", "https") and parsed.hostname == root_host and linked not in visited:
                if any(term in (linked + " " + label).lower() for term in LINK_TERMS):
                    queue.append(linked)
    return pages, errors


def summarize_event(event: dict, pages: list[dict], errors: list[dict],
                    people: list[dict] | None = None, accounts: list[dict] | None = None,
                    profiles: list[dict] | None = None) -> str:
    lines = [f"# {event['name']} — cartographie", "", "## Contexte et enjeux", "",
             f"Édition : {event.get('edition') or 'À confirmer'} ; date : {event.get('date') or 'À confirmer'}.",
             f"Organisateur : {event.get('organizer') or 'À confirmer'} ; lieu : {event.get('venue') or 'À confirmer'}.",
             "Maturité du marché : à documenter avec des données sectorielles datées ; aucune phase de marché n'est affirmée sur la seule base du programme.", ""]
    if not pages:
        lines += ["**Recherche indisponible.** Aucune page n'a été lue ; ajouter des `reference_pages` ou relancer avec accès réseau.", ""]
    else:
        lines += ["## Thèmes observés", ""]
        for theme, terms in THEMES.items():
            source = next((p for p in pages if any(term in " " + p["text"].lower() + " " for term in terms)), None)
            if source:
                lines.append(f"- {theme} — [{source['title'] or 'source'}]({source['url']}) ({source['source_type']}, {source['checked_at'] or 'date inconnue'}).")
        if lines[-1] == "":
            lines.append("- Aucun thème du dictionnaire n'a été trouvé ; lecture humaine requise.")
        lines += ["", "## Dynamique du marché", "",
                  "[Déduit] Les acheteurs possibles sont les détaillants : besoins à vérifier en acquisition, fidélisation, expérience client, commerce numérique et efficacité opérationnelle. Aucun budget individuel n'est documenté par la page de l'événement.", "",
                  "[Déduit] Les vendeurs possibles sont les agences et fournisseurs de commerce numérique, publicité, données, logistique et IA. Leur offre et leur présence comme exposant doivent être vérifiées dans le programme ou la liste officielle.", "",
                  "## Sources consultées", ""]
        for p in pages:
            lines.append(f"- [{p['title'] or p['url']}]({p['url']}) — {p['source_type']} ; vérifié {p['checked_at'] or 'à une date inconnue'}.")
    if errors:
        lines += ["", "## Pages non accessibles", ""]
        for error in errors:
            lines.append(f"- {error['url']} — {error['error']} : {error['detail']}")
    if people is not None and accounts is not None:
        from collections import Counter
        from .core import infer_org_type
        types = Counter(infer_org_type(a)[0] for a in accounts)
        lines += ["", "## Liste fournie et potentiel BETA Labs", "",
                  f"{len(people)} lignes participants ; {len(accounts)} entreprises rapprochées. Typologies calculées : " +
                  ", ".join(f"{key} {value}" for key, value in sorted(types.items())) + ".", "",
                  "[Déduit] La liste permet de croiser les décideurs des détaillants avec les ICP de " +
                  ", ".join(p.get("name", p["id"]) for p in (profiles or [])) +
                  ". Les motivations, projets, budgets et échéances restent à qualifier en conversation."]
    lines += ["", "Aucun budget, maturité de marché ou motif individuel n'est déduit de la seule page de l'événement."]
    return "\n".join(lines) + "\n"


def scan_account_website(url: str) -> list[dict]:
    """Capture only weak, dated website indicators; never infer paid ads from pixels."""
    page = fetch_page(url)
    text = page["text"].lower()
    findings = []
    for field, terms in {
        "online_store_candidate": ("ajouter au panier", "add to cart", "checkout", "magasinez", "shop now"),
        "loyalty_candidate": ("fidélité", "loyalty", "récompenses", "rewards"),
        "mobile_app_mention": ("application mobile", "mobile app"),
    }.items():
        if any(term in text for term in terms):
            findings.append({"field": field, "value": "mention observée sur la page", "source_url": page["url"],
                             "checked_at": page["checked_at"], "confidence": "faible", "caveat": "Mention du site seulement ; identité du produit et état actuel à vérifier."})
    return findings
