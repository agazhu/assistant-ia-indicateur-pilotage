"""
Chaîne d'alimentation de l'indicateur de pilotage de l'Assistant IA.

Étapes :
1. Télécharge les deux jeux de données de data.education.gouv.fr (export CSV).
   Via l'API Explore v2.1 (/exports/csv). Le mode --offline utilise les
   copies locales de data/sources/ (tests).
2. Historise chaque jour le jeu « déploiement en académie », publié sans date.
3. Calcule, par académie : utilisateurs cumulés, nouveaux utilisateurs et
   messages sur 28 jours, vitalité, pénétration (si effectifs renseignés).
4. Applique les seuils (alerte, vigilance, contrôle de qualité).
5. Écrit docs/data/indicateur.json (lu par le tableau de bord) et ajoute une
   ligne à data/historique_national.csv.

Usage : python pipeline/run.py [--offline]
"""
import io
import json
import re
import sys
import unicodedata
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd

RACINE = Path(__file__).resolve().parent.parent
API = "https://data.education.gouv.fr/api/explore/v2.1/catalog/datasets/{}/exports/csv"
PARAMS = {"delimiter": ";", "use_labels": "true", "lang": "fr"}
JEU_SERIE = "fr-en-assistant_ia_deploiement_menjs"
JEU_PROFILS = "assistant-ia-dinum-deploiement-au-ministere-de-leducation-nationale-en-academie"

FENETRE = 28                 # jours glissants (4 semaines complètes)
RATIO_SEUIL = 0.5            # seuils : 50 % de la médiane nationale
JOURS_FIGES = 7              # contrôle de qualité : compteurs inchangés
CONFIG = json.loads((RACINE / "referentiel" / "config.json").read_text(encoding="utf-8"))

ACADEMIES = [
    "Aix-Marseille", "Amiens", "Besançon", "Bordeaux", "Clermont-Ferrand", "Corse",
    "Créteil", "Dijon", "Grenoble", "Guadeloupe", "Guyane", "La Réunion", "Lille",
    "Limoges", "Lyon", "Martinique", "Mayotte", "Montpellier", "Nancy-Metz", "Nantes",
    "Nice", "Normandie", "Orléans-Tours", "Paris", "Poitiers", "Reims", "Rennes",
    "Strasbourg", "Toulouse", "Versailles",
]


def normaliser(texte: str) -> str:
    """Minuscules, sans accents ni ponctuation : rend le code indépendant du
    format des en-têtes (libellés ou noms techniques de l'API)."""
    t = re.sub(r"[\u2019\u2018']", " ", str(texte))
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", t.lower()).strip()


NORM_ACA = {normaliser(a): a for a in ACADEMIES}


def telecharger(jeu: str, local: Path, hors_ligne: bool) -> tuple[pd.DataFrame, str]:
    """Interroge l'API Explore v2.1 de data.education.gouv.fr (point d'accès
    /exports/csv, qui renvoie le jeu complet en un appel, contrairement à
    /records, limité à 100 lignes par appel).
    Sans --offline, un échec de l'API arrête la tâche : on préfère une
    exécution en erreur, visible, à un tableau de bord alimenté par des
    données périmées."""
    url = API.format(jeu)
    if hors_ligne:
        return pd.read_csv(local, sep=";", encoding="utf-8-sig"), "copie locale (mode hors ligne)"
    import requests
    derniere_erreur = None
    for essai in range(3):
        try:
            r = requests.get(url, params=PARAMS, timeout=60)
            r.raise_for_status()
            local.write_bytes(r.content)
            df = pd.read_csv(io.BytesIO(r.content), sep=";", encoding="utf-8-sig")
            print(f"API : {jeu} : {len(df)} lignes, {len(df.columns)} colonnes ({r.url})")
            return df, "API data.education.gouv.fr"
        except Exception as erreur:
            derniere_erreur = erreur
            print(f"[essai {essai + 1}/3] {jeu} : {erreur}")
    sys.exit(f"API indisponible pour {jeu} : {derniere_erreur}")


def classer_colonne(nom: str):
    """Retourne (type, entité) pour une colonne de compteur, sinon None."""
    n = normaliser(nom)
    if "utilisateur" in n:
        genre = "U"
    elif "message" in n:
        genre = "M"
    else:
        return None
    entite = re.sub(r"\b(nombre|d|de|du|utilisateurs|messages)\b", " ", n)
    entite = re.sub(r"\s+", " ", entite).strip()
    for cle, aca in NORM_ACA.items():
        if "academie" in n and "region academique" not in n and entite.endswith(cle):
            return genre, aca, "academie"
    if "region academique" in n:
        return genre, entite, "region"
    if entite in ("domaine education gouv fr", "igesr"):
        return genre, entite, "centrale"
    return genre, entite, "autre"


def preparer_serie(brut: pd.DataFrame):
    col_date = next(c for c in brut.columns if "horodatage" in normaliser(c))
    brut = brut.copy()
    brut["jour"] = (pd.to_datetime(brut[col_date], utc=True)
                    .dt.tz_convert("Europe/Paris").dt.normalize().dt.tz_localize(None))
    brut = brut.sort_values("jour").drop_duplicates("jour", keep="last").set_index("jour")
    meta = {}
    for c in brut.columns:
        info = classer_colonne(c)
        if info:
            meta[c] = info
    observes = brut.index
    serie = brut[list(meta)].apply(pd.to_numeric, errors="coerce").asfreq("D")
    manquants = serie.index.difference(observes)
    serie = serie.interpolate(limit_area="inside")  # jours manquants : interpolation linéaire
    return serie, meta, list(manquants)


def en_vacances(jour: pd.Timestamp) -> bool:
    for p in CONFIG["vacances_scolaires_communes"]:
        if pd.Timestamp(p["debut"]) <= jour <= pd.Timestamp(p["fin"]):
            return True
    return False


def detecter_figements(s: pd.Series, manquants) -> list[dict]:
    """Périodes d'au moins JOURS_FIGES jours observés (hors vacances) sans
    aucune variation des messages : anomalie de collecte probable."""
    obs = s.drop(index=[d for d in manquants if d in s.index])
    variation = obs.diff().fillna(1) != 0
    periodes, debut, n = [], None, 0
    for jour, varie in variation.items():
        if not varie and not en_vacances(jour):
            debut = debut or jour
            n += 1
        else:
            if n >= JOURS_FIGES:
                periodes.append({"debut": debut.date().isoformat(), "fin": prec.date().isoformat(), "jours": n})
            debut, n = None, 0
        prec = jour
    if n >= JOURS_FIGES:
        periodes.append({"debut": debut.date().isoformat(), "fin": prec.date().isoformat(), "jours": n})
    return periodes


def main(hors_ligne: bool = False):
    aujourdhui = date.today().isoformat()
    brut, origine_serie = telecharger(JEU_SERIE, RACINE / "data/sources/beta.csv", hors_ligne)
    profils, origine_profils = telecharger(JEU_PROFILS, RACINE / "data/sources/production.csv", hors_ligne)

    # Historisation du jeu par profil (publié sans date) : un instantané par jour.
    profils.to_csv(RACINE / "data/historique_production" / f"{aujourdhui}.csv", sep=";", index=False)

    serie, meta, manquants = preparer_serie(brut)
    t = serie.index.max()
    t0 = t - pd.Timedelta(days=FENETRE)
    if t0 < serie.index.min():
        sys.exit("Série trop courte pour la fenêtre de 28 jours.")
    part_vacances = sum(en_vacances(d) for d in pd.date_range(t0 + pd.Timedelta(days=1), t)) / FENETRE

    effectifs = pd.read_csv(RACINE / "referentiel/effectifs_academies.csv", sep=";", dtype={"effectif": "Int64"})
    effectifs = dict(zip(effectifs["academie"], effectifs["effectif"]))

    lignes = []
    for aca in ACADEMIES:
        cu = next((c for c, m in meta.items() if m[0] == "U" and m[1] == aca), None)
        cm = next((c for c, m in meta.items() if m[0] == "M" and m[1] == aca), None)
        if cu is None or cm is None:
            continue
        u, m = serie[cu], serie[cm]
        nouveaux = u[t] - u[t0]
        messages = m[t] - m[t0]
        eff = effectifs.get(aca)
        lignes.append({
            "academie": aca,
            "utilisateurs": int(u[t]),
            "nouveaux_28j": int(round(nouveaux)),
            "croissance_28j_pct": round(100 * nouveaux / (u[t] - nouveaux), 1) if u[t] > nouveaux else None,
            "messages_28j": int(round(messages)),
            "vitalite": round(messages / u[t], 2) if u[t] else None,
            "effectif": int(eff) if pd.notna(eff) else None,
            "penetration_pct": round(100 * u[t] / eff, 2) if pd.notna(eff) and eff else None,
            "figements": detecter_figements(m, manquants),
        })
    df = pd.DataFrame(lignes)

    med_vit = float(df["vitalite"].median())
    seuil_vit = round(RATIO_SEUIL * med_vit, 2)
    pen_dispo = df["penetration_pct"].notna().sum() >= 15
    med_pen = float(df["penetration_pct"].median()) if pen_dispo else None
    suspendu = part_vacances > 0.5

    def statut(r):
        motifs = []
        if pen_dispo and r["penetration_pct"] is not None and r["penetration_pct"] < RATIO_SEUIL * med_pen:
            motifs.append("pénétration sous le seuil d'alerte")
        if not suspendu and r["vitalite"] is not None and r["vitalite"] < seuil_vit:
            motifs.append("vitalité sous le seuil de vigilance")
        fige_recent = any(pd.Timestamp(f["fin"]) >= t0 for f in r["figements"])
        if fige_recent:
            motifs.append("compteurs figés, collecte à vérifier")
        return motifs

    df["motifs"] = df.apply(statut, axis=1)

    # Périmètre ministériel : académies + régions académiques + centrale + IGÉSR
    cols_men_u = [c for c, m in meta.items() if m[0] == "U" and m[2] in ("academie", "region", "centrale")]
    cols_men_m = [c for c, m in meta.items() if m[0] == "M" and m[2] in ("academie", "region", "centrale")]
    cols_tous_u = [c for c, m in meta.items() if m[0] == "U"]
    u_men = serie[cols_men_u].sum(axis=1)
    u_men_t = int(u_men[t])
    hebdo = u_men.resample("W-SUN").last().diff().dropna()
    semaine_complete = hebdo.index <= t
    hebdo = hebdo[semaine_complete]

    # Profils (jeu sans date)
    col_aca = next(c for c in profils.columns if normaliser(c) == "libelle aca")
    noms_profils = [c for c in profils.columns if normaliser(c) in
                    ("chefs d etablissement", "enseignants", "administration", "inspecteurs")]
    tot_profils = {c: int(profils[c].sum()) for c in noms_profils}

    sortie = {
        "genere_le": datetime.now(timezone.utc).isoformat(timespec="minutes"),
        "dernier_releve": t.date().isoformat(),
        "sources": {"serie": origine_serie, "profils": origine_profils,
                    "api": [API.format(JEU_SERIE), API.format(JEU_PROFILS)]},
        "jours_interpoles": [d.date().isoformat() for d in manquants],
        "parametres": {"fenetre_jours": FENETRE, "ratio_seuil": RATIO_SEUIL, "jours_figes": JOURS_FIGES,
                       "part_fenetre_en_vacances": round(part_vacances, 2), "vigilance_suspendue": suspendu},
        "national": {
            "utilisateurs_perimetre_ministere": u_men_t,
            "utilisateurs_toutes_entites": int(serie[cols_tous_u].sum(axis=1)[t]),
            "messages_toutes_entites": int(serie[[c for c, m in meta.items() if m[0] == "M"]].sum(axis=1)[t]),
            "effectif_national": CONFIG["effectif_national"],
            "penetration_nationale_pct": round(100 * u_men_t / CONFIG["effectif_national"], 2),
            "cible": CONFIG["cible_ministerielle"],
            "atteinte_cible_pct": round(100 * u_men_t / CONFIG["cible_ministerielle"], 1),
            "mediane_vitalite": round(med_vit, 2),
            "seuil_vitalite": seuil_vit,
            "mediane_penetration_pct": med_pen,
            "penetration_par_academie_disponible": bool(pen_dispo),
        },
        "hebdomadaire": [{"semaine_fin": d.date().isoformat(), "nouveaux": int(v)} for d, v in hebdo.items()],
        "academies": json.loads(df.to_json(orient="records", force_ascii=False)),
        "profils": {
            "date_collecte": aujourdhui,
            "totaux": tot_profils,
            "par_academie": json.loads(profils[[col_aca] + noms_profils].rename(columns={col_aca: "academie"})
                                       .to_json(orient="records", force_ascii=False)),
        },
    }
    (RACINE / "docs/data/indicateur.json").write_text(json.dumps(sortie, ensure_ascii=False, indent=1), encoding="utf-8")

    histo = RACINE / "data/historique_national.csv"
    ligne = pd.DataFrame([{
        "date_calcul": aujourdhui, "dernier_releve": t.date().isoformat(),
        "utilisateurs_ministere": u_men_t,
        "penetration_nationale_pct": sortie["national"]["penetration_nationale_pct"],
        "atteinte_cible_pct": sortie["national"]["atteinte_cible_pct"],
        "mediane_vitalite": round(med_vit, 2),
        "nb_academies_signalees": int((df["motifs"].str.len() > 0).sum()),
    }])
    if histo.exists():
        ancien = pd.read_csv(histo, sep=";")
        ligne = pd.concat([ancien[ancien["date_calcul"] != aujourdhui], ligne])
    ligne.to_csv(histo, sep=";", index=False)

    signalees = df[df["motifs"].str.len() > 0][["academie", "motifs"]]
    print(f"Sources : {origine_serie} / {origine_profils}")
    print(f"Relevé du {t.date()} : {u_men_t} utilisateurs (périmètre ministère), "
          f"pénétration {sortie['national']['penetration_nationale_pct']} %, "
          f"médiane de vitalité {med_vit:.2f}, seuil {seuil_vit}")
    print(signalees.to_string(index=False) if len(signalees) else "Aucune académie signalée.")


if __name__ == "__main__":
    main(hors_ligne="--offline" in sys.argv)
