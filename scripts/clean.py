

import pandas as pd

import numpy as np

import re

import os

from datetime import datetime


GRN = "\033[92m"

YLW = "\033[93m"

RED = "\033[91m"

RST = "\033[0m"

BLD = "\033[1m"


def ok(msg): print(f"{GRN}  ✓  {msg}{RST}")


def warn(msg): print(f"{YLW}  ⚠  {msg}{RST}")


def log(msg, c=RST): print(f"{c}{msg}{RST}")


report_lines = []


def rep(msg): report_lines.append(msg); print(msg)


log("\n"+"="*60, BLD)

log("  SIGB — Nettoyage des données bibliographiques", BLD)

log("="*60+"\n", BLD)


for f in ["bua.xls", "buf.csv"]:

    if not os.path.exists(f):

        log(f"ERREUR : '{f}' introuvable !", RED)

        input("\nEntrée pour quitter...")

        exit(1)

ok("Fichiers sources trouvés")


# ── 1. Chargement ────────────────────────────────────────────
log("\n[1/7] Chargement des fichiers...", BLD)
COLS = ['Cote', 'Titre', 'Auteur', 'Lieu', 'Edition',
        'Annee', 'NbPages', 'Matiere', 'Inventaire']

# Add converters={'Cote': str} or dtype={'Cote': str} to stop Excel's auto-dating logic
bua = pd.read_excel("bua.xls", engine="xlrd", dtype={'Cote': str})
bua.columns = COLS
log(f"  →  BUA chargé  : {len(bua):,} lignes")

buf = pd.read_csv("buf.csv", sep=";", encoding="latin-1",
                  header=None, on_bad_lines="skip", dtype={'Cote': str})
buf.columns = COLS
log(f"  →  BUF chargé  : {len(buf):,} lignes")

# ── DEBUG RAW : lire bua.xls sans renommer les colonnes ──

raw = pd.read_excel("bua.xls", engine="xlrd")

print("\n[DEBUG RAW] Premières valeurs colonne 0 (Cote) brutes:")

print(raw.iloc[:, 0].head(30).to_string())

print("\nType colonne Cote:", raw.iloc[:, 0].dtype)


bua = pd.read_excel("bua.xls", engine="xlrd")

bua.columns = COLS

log(f"  →  BUA chargé  : {len(bua):,} lignes")


buf = pd.read_csv("buf.csv", sep=";", encoding="latin-1",

                  header=None, on_bad_lines="skip")

buf.columns = COLS

log(f"  →  BUF chargé  : {len(buf):,} lignes")


rep("\n"+"="*60)

rep(f"  RAPPORT DE NETTOYAGE — {datetime.now().strftime('%d/%m/%Y %H:%M')}")

rep("="*60)

rep(f"\nBUA brut : {len(bua):,} lignes")

rep(f"BUF brut : {len(buf):,} lignes")


# ── 2. Nettoyage chaînes ─────────────────────────────────────

log("\n[2/7] Nettoyage des chaînes...", BLD)


def clean_strings(df, name):

    for col in df.columns:

        df[col] = df[col].astype(str).str.strip().str.strip('"').str.strip("'")

        df[col] = df[col].replace(

            {'nan': np.nan, 'NaN': np.nan, 'None': np.nan, '': np.nan})

    ok(f"{name} : chaînes nettoyées")

    return df


bua = clean_strings(bua, "BUA")

buf = clean_strings(buf, "BUF")


# ── DEBUG : cotes problématiques après clean_strings ─────────

print("\n[DEBUG] Cotes BUA contenant un nom de mois APRÈS clean_strings:")

problematic = bua[bua['Cote'].astype(str).str.contains(

    r'janv|févr|mars|avr|mai|juin|juil|août|sept|oct|nov|déc|jan|feb|mar|apr|may|jun|jul|aug|sep|dec',

    case=False, na=False, regex=True

)]

print(problematic[['Cote']].head(20).to_string())

print(f"Total cotes avec nom de mois : {len(problematic)}")


# ── 3. Suppression des مكرر (doublons arabes) ────────────────

log("\n[3/7] Suppression des notices مكرر (doublons arabes)...", BLD)

avant = len(bua)

bua_mkrr = bua[bua['Cote'].astype(str).str.contains('مكرر', na=False)]

warn(f"BUA : {len(bua_mkrr)} notices marquées مكرر trouvées")

rep(f"  [BUA] Notices مكرر supprimées : {len(bua_mkrr)}")

bua = bua[~bua['Cote'].astype(str).str.contains(

    'مكرر', na=False)].reset_index(drop=True)

ok(f"BUA : {avant} → {len(bua)} lignes après suppression مكرر")


# ── 4. Restauration des cotes converties en dates par Excel ──

log("\n[4/7] Restauration des cotes converties en dates...", BLD)

MONTH_MAP = {

    'janv': '01', 'févr': '02', 'mars': '03', 'avr': '04', 'mai': '05', 'juin': '06',

    'juil': '07', 'août': '08', 'sept': '09', 'oct': '10', 'nov': '11', 'déc': '12',

    'jan': '01', 'feb': '02', 'mar': '03', 'apr': '04', 'may': '05', 'jun': '06',

    'jul': '07', 'aug': '08', 'sep': '09', 'oct': '10', 'nov': '11', 'dec': '12',

    'fév': '02', 'aou': '08', 'aout': '08',

}


def restore_cote(val):

    if pd.isna(val):

        return val

    s = str(val).strip().strip('"').strip("'")

    # Cas 1 — "02-févr"  →  "02/01"  (num-mois)

    m = re.match(r'^(\d{1,2})[-/]([a-zA-Zéûîôàèùâêîôûàü]+)$', s)

    if m:

        num, mon = m.group(1), m.group(2).lower()

        if mon in MONTH_MAP:

            return f"{num}/{MONTH_MAP[mon]}"

    # Cas 2 — "mars-43"  →  "03/43"  (mois-num)

    m = re.match(r'^([a-zA-Zéûîôàèùâêîôûàü]+)[-/](\d+)$', s)

    if m:

        mon, num = m.group(1).lower(), m.group(2)

        if mon in MONTH_MAP:

            return f"{MONTH_MAP[mon]}/{num}"

    # Cas 3 — suffixe "-mois" après une cote complexe ex: "82-31_533/01-janv"

    m = re.match(r'^(.+?)[-/]([a-zA-Zéûîôàèùâêîôûàü]+)$', s)

    if m:

        prefix, mon = m.group(1), m.group(2).lower()

        if mon in MONTH_MAP:

            return f"{prefix}/{MONTH_MAP[mon]}"

    return s


# ── Appliquer restore_cote ────────────────────────────────────
avant_buf = buf['Cote'].copy()

buf['Cote'] = buf['Cote'].apply(restore_cote)

n_restored_buf = (buf['Cote'] != avant_buf.apply(

    lambda x: str(x).strip())).sum()

warn(f"BUF : {n_restored_buf} cotes restaurées")

rep(f"  [BUF] Cotes restaurées : {n_restored_buf}")


avant_bua = bua['Cote'].copy()

bua['Cote'] = bua['Cote'].apply(restore_cote)

n_restored_bua = (bua['Cote'] != avant_bua.apply(

    lambda x: str(x).strip())).sum()

warn(f"BUA : {n_restored_bua} cotes restaurées")

rep(f"  [BUA] Cotes restaurées : {n_restored_bua}")


# ── DEBUG : vérifier ce qui reste après restauration ─────────

print("\n[DEBUG] Cotes BUA contenant encore un nom de mois APRÈS restauration:")

still_bad = bua[bua['Cote'].astype(str).str.contains(

    r'janv|févr|mars|avr|mai|juin|juil|août|sept|oct|nov|déc|jan|feb|mar|apr|may|jun|jul|aug|sep|dec',

    case=False, na=False, regex=True

)]

print(still_bad[['Cote']].head(20).to_string())

print(f"Total restants : {len(still_bad)}")


ok("Cotes nettoyées")


# ── 5. Annee ─────────────────────────────────────────────────

log("\n[5/7] Nettoyage colonne Annee...", BLD)


def clean_annee(df, name):

    df['Annee'] = df['Annee'].astype(str).str.replace(

        r'\.0$', '', regex=True).str.strip()

    df['Annee'] = df['Annee'].replace({'nan': np.nan, '': np.nan})

    df['Annee'] = pd.to_numeric(df['Annee'], errors='coerce')

    masque = df['Annee'].notna() & ~df['Annee'].between(1800, 2026)

    n = masque.sum()

    if n:

        warn(f"{name} : {n} année(s) invalide(s) → NULL")

        rep(f"  [{name}] Annee invalide : {n} → NULL")

    df.loc[masque, 'Annee'] = np.nan

    df['Annee'] = df['Annee'].astype('Int64')

    ok(f"{name} : Annee nettoyée")

    return df


bua = clean_annee(bua, "BUA")

buf = clean_annee(buf, "BUF")


# ── 6. NbPages ───────────────────────────────────────────────

log("\n[6/7] Nettoyage colonne NbPages...", BLD)


def clean_pages(df, name):

    def extract(val):

        if pd.isna(val):

            return np.nan

        digits = re.sub(r'[^\d]', '', str(val))

        return int(digits) if digits else np.nan

    df['NbPages'] = df['NbPages'].apply(extract).astype('Int64')

    ok(f"{name} : NbPages nettoyé")

    return df


bua = clean_pages(bua, "BUA")

buf = clean_pages(buf, "BUF")


# ── 7. Doublons + Inventaires ────────────────────────────────

log("\n[7/7] Doublons et inventaires...", BLD)


for df, name in [(bua, "BUA"), (buf, "BUF")]:

    avant2 = len(df)

    df.drop_duplicates(inplace=True)

    df.reset_index(drop=True, inplace=True)

    n = avant2 - len(df)

    if n:

        warn(f"{name} : {n} doublon(s) exact(s) supprimé(s)")

        rep(f"  [{name}] Doublons : {n}")

    else:

        ok(f"{name} : aucun doublon exact")


def corriger_inv(df, name):

    compteur = {}

    nouveaux = []

    n = 0

    for val in df['Inventaire']:

        if pd.isna(val):

            nouveaux.append(val)

            continue

        v = str(val).strip()

        if v in compteur:

            compteur[v] += 1

            nouveaux.append(f"{v}_{chr(96+compteur[v])}")

            n += 1

        else:

            compteur[v] = 1

            nouveaux.append(v)

    df['Inventaire'] = nouveaux

    if n:

        warn(f"{name} : {n} inventaire(s) renommé(s)")

        rep(f"  [{name}] Inventaires renommés : {n}")

    else:

        ok(f"{name} : aucun inventaire dupliqué")

    return df


bua = corriger_inv(bua, "BUA")

buf = corriger_inv(buf, "BUF")


# ── Ajout Source ─────────────────────────────────────────────

bua['Source'] = 'BUA'

buf['Source'] = 'BUF'


# ── Sauvegarde ───────────────────────────────────────────────

log("\n[✓] Sauvegarde...", BLD)

bua.to_csv("bua_clean.xls", index=False, encoding="utf-8-sig", sep=";")

ok(f"bua_clean.xls ({len(bua):,} lignes)")


buf.to_csv("buf_clean.csv", index=False, encoding="utf-8-sig", sep=";")

ok(f"buf_clean.csv  ({len(buf):,} lignes)")


rep(f"\nBUA propre : {len(bua):,} lignes  (dont {avant-len(bua)} مكرر supprimés)")

rep(f"BUF propre : {len(buf):,} lignes")

rep(f"Total      : {len(bua)+len(buf):,} notices prêtes pour PostgreSQL")

rep("\n"+"="*60)


with open("rapport_nettoyage.txt", "w", encoding="utf-8") as f:

    f.write("\n".join(report_lines))

ok("rapport_nettoyage.txt sauvegardé")


log("\n"+"="*60, GRN)

log("  NETTOYAGE TERMINÉ", GRN)

log("    📄 bua_clean.xls  📄 buf_clean.csv   📄 rapport_nettoyage.txt", GRN)

log("  ➜  Dans Excel : délimiteur = POINT-VIRGULE", YLW)

log("="*60+"\n", GRN)

input("Appuyez sur Entrée pour fermer...")
