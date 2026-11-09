import os
import pandas as pd

print("Fichiers dans 'DATA SUR EXCEL' :")
for nom in os.listdir("DATA SUR EXCEL"):
    print("  ", nom)

print("\n--- data_nettoyee.xlsx ---")
feuilles = pd.read_excel("data_nettoyee.xlsx", sheet_name=None)
for nom, df in feuilles.items():
    print(f"\nFeuille '{nom}' : {len(df)} lignes")
    print("Colonnes :", list(df.columns))
    print(df.head(2).to_string())