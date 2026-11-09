import pandas as pd, json, os

dl = os.path.expanduser("~/Downloads")

for nom in ("entreprises_marrakech.xlsx", "entreprises_marrakech (1).xlsx"):
    chemin = os.path.join(dl, nom)
    print("\n=====", nom, "=====")
    for feuille, df in pd.read_excel(chemin, sheet_name=None).items():
        print(f"Feuille '{feuille}' : {len(df)} lignes")
        print("Colonnes :", list(df.columns))
        print(df.head(2).to_string())

chemin = os.path.join(dl, "entreprises_marrakech.json")
with open(chemin, encoding="utf-8") as f:
    data = json.load(f)
print("\n===== entreprises_marrakech.json =====")
print("Type :", type(data).__name__, "| éléments :", len(data))
if isinstance(data, list) and data:
    print("Clés :", list(data[0].keys()))