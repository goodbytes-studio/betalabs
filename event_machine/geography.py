"""Déduction de la province canadienne à partir de la ville d'un inscrit.

La ville d'un inscrit n'est pas le siège de son entreprise : la déduction reste une hypothèse
(`[Déduit]`) et ne sert jamais à exclure un compte (décision D36, source S61).
"""

from __future__ import annotations

import re
import unicodedata

_QUEBEC_CITIES = {
    "montreal", "quebec city", "quebec", "laval", "sherbrooke", "longueuil", "boucherville", "trois rivieres", "saguenay",
    "mirabel", "brossard", "drummondville", "mascouche", "st bruno de montarville", "saint bruno de montarville",
    "varennes", "terrebonne", "sainte therese", "alma", "repentigny", "blainville", "l ancienne lorette", "victoriaville",
    "saint basile le grand", "chambly", "rimouski", "bois des filion", "val d or", "saint augustin de desmaures",
    "deux montagnes", "candiac", "salaberry de valleyfield", "saint jerome", "prevost", "l ile perrot",
    "saint jean sur richelieu", "shannon", "stanbridge east", "richelieu", "saint cyprien de napierville", "beaconsfield",
    "pointe des cascades", "bromont", "sainte catherine", "pincourt", "warwick", "saint mathieu du parc",
    "mont saint hilaire", "sainte anne des plaines", "lavaltrie", "beauharnois", "matagami", "mont tremblant",
    "pointe claire", "mount royal", "lorraine", "mercier", "granby", "carignan", "nicolet", "dorval", "beloeil", "lanoraie",
    "gatineau", "levis", "saint hyacinthe", "rosemere", "boisbriand", "saint lambert", "westmount", "outremont", "verdun",
    "saint constant", "chateauguay", "vaudreuil dorion", "saint eustache", "sorel tracy", "joliette", "magog",
    "rouyn noranda", "sept iles", "baie comeau", "chicoutimi", "jonquiere", "saint georges", "thetford mines",
    "shawinigan", "cowansville", "la pocatiere", "rivière du loup", "riviere du loup", "saint sauveur", "sainte adele",
}
_OTHER_CITIES = {
    "toronto": "ontario", "mississauga": "ontario", "ottawa": "ontario", "hamilton": "ontario", "london": "ontario",
    "brampton": "ontario", "markham": "ontario", "vaughan": "ontario", "kitchener": "ontario", "waterloo": "ontario",
    "oakville": "ontario", "burlington": "ontario", "windsor": "ontario", "kingston": "ontario",
    "vancouver": "british columbia", "victoria": "british columbia", "calgary": "alberta", "edmonton": "alberta",
    "winnipeg": "manitoba", "halifax": "nova scotia", "saskatoon": "saskatchewan", "regina": "saskatchewan",
}
CITY_PROVINCE = {**{c: "quebec" for c in _QUEBEC_CITIES}, **_OTHER_CITIES}


def _norm(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(c for c in text if not unicodedata.combining(c)).casefold()
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def province_from_city(city: object, country: object = "") -> str:
    """Province déduite d'une ville canadienne, ou chaîne vide si inconnue ou hors Canada."""
    if _norm(country) not in ("", "canada"):
        return ""
    return CITY_PROVINCE.get(_norm(city), "")
