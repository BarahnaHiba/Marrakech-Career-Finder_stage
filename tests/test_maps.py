import json
from unittest.mock import patch

import maps


def test_geocode_une_adresse_openstreetmap_et_cache_le_resultat(monkeypatch):
    monkeypatch.setattr(maps, "_CACHE_GEOCODAGE", {})
    monkeypatch.setattr(maps, "_DERNIERE_REQUETE", 0.0)
    donnees = json.dumps([{
        "lat": "31.6295",
        "lon": "-7.9811",
        "display_name": "Marrakech, Maroc",
    }]).encode()

    class Reponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def read(self):
            return donnees

    with patch.object(maps, "urlopen", return_value=Reponse()) as ouvrir:
        with patch.object(maps.time, "sleep") as pause:
            resultat = maps.geocoder_entreprise("Entreprise", "Guéliz", "Marrakech")
            seconde_lecture = maps.geocoder_entreprise("Entreprise", "Guéliz", "Marrakech")

    assert resultat == {
        "latitude": 31.6295,
        "longitude": -7.9811,
        "libelle": "Marrakech, Maroc",
    }
    assert seconde_lecture == resultat
    ouvrir.assert_called_once()
    pause.assert_not_called()
    demande = ouvrir.call_args.args[0]
    assert "nominatim.openstreetmap.org" in demande.full_url
    assert "Marrakech" in demande.full_url
    assert "MarrakechCareerFinder" in demande.get_header("User-agent")


def test_geocodage_sans_lieu_ne_fait_pas_dappel_reseau():
    with patch.object(maps, "urlopen") as ouvrir:
        assert maps.geocoder_entreprise("Entreprise", "", "") is None

    ouvrir.assert_not_called()
