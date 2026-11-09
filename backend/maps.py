import json
import threading
import time
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


_CACHE_GEOCODAGE = {}
_VERROU_GEOCODAGE = threading.Lock()
_DERNIERE_REQUETE = 0.0
_USER_AGENT = "MarrakechCareerFinder/1.0 (https://github.com/BarahnaHiba/Marrakech-Career-Finder_stage)"


def geocoder_entreprise(nom, adresse, ville):
    if not any(valeur and valeur.strip() for valeur in (adresse, ville)):
        return None
    morceaux = [valeur.strip() for valeur in (nom, adresse, ville, "Maroc") if valeur and valeur.strip()]

    requete = ", ".join(morceaux)
    with _VERROU_GEOCODAGE:
        global _DERNIERE_REQUETE
        if requete in _CACHE_GEOCODAGE:
            return _CACHE_GEOCODAGE[requete]

        attente = 1.0 - (time.monotonic() - _DERNIERE_REQUETE)
        if attente > 0:
            time.sleep(attente)

        _DERNIERE_REQUETE = time.monotonic()
        url = "https://nominatim.openstreetmap.org/search?" + urlencode({
            "q": requete,
            "format": "jsonv2",
            "limit": 1,
        })
        demande = Request(url, headers={"User-Agent": _USER_AGENT})
        with urlopen(demande, timeout=8) as reponse:
            resultats = json.loads(reponse.read().decode("utf-8"))

        coordonnees = None
        if resultats:
            coordonnees = {
                "latitude": float(resultats[0]["lat"]),
                "longitude": float(resultats[0]["lon"]),
                "libelle": resultats[0].get("display_name", requete),
            }
        _CACHE_GEOCODAGE[requete] = coordonnees
        return coordonnees


__all__ = ["URLError", "geocoder_entreprise"]
