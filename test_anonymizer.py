"""
test_anonymizer.py — Vérifie ce que l'anonymiseur détecte et remplace.
Lance avec : python test_anonymizer.py

Tu peux modifier CV_SAMPLE ci-dessous avec ton propre texte.
"""

import sys
import os

# Permet de lancer le script depuis la racine du projet
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.anonymizer import anonymize

# ─── CV de test ───────────────────────────────────────────────────────────────
# Remplace ce bloc par ton propre texte pour tester

CV_SAMPLE = """
Marie Dupont
marie.dupont@gmail.com | +33 6 12 34 56 78
linkedin.com/in/marie-dupont | github.com/mariedupont
12 rue des Lilas, 75011 Paris
https://mariedupont.dev

EXPÉRIENCE PROFESSIONNELLE

Chef de Projet Digital — Acme Corp (2021–2024)
- Géré une équipe de 8 personnes
- Augmenté le taux de conversion de 32%

FORMATION

Master Management — HEC Paris (2019)

COMPÉTENCES
Python, SQL, Figma, Jira
"""

# ─── Test ─────────────────────────────────────────────────────────────────────

def run_test(text: str):
    print("=" * 60)
    print("TEXTE ORIGINAL")
    print("=" * 60)
    print(text)

    result = anonymize(text)

    print("\n" + "=" * 60)
    print("TEXTE ANONYMISÉ (envoyé à l'IA)")
    print("=" * 60)
    print(result.anonymized_text)

    print("\n" + "=" * 60)
    print(f"ÉLÉMENTS REMPLACÉS ({len(result.summary)})")
    print("=" * 60)
    if result.summary:
        for item in result.summary:
            print(f"  • {item}")
    else:
        print("  Aucun élément détecté.")

    print("\n" + "=" * 60)
    print("TABLE DE CORRESPONDANCE (placeholders → valeurs réelles)")
    print("=" * 60)
    if result.replacements:
        for placeholder, original in result.replacements.items():
            print(f"  {placeholder:30s} → {original}")
    else:
        print("  Vide.")

    print("\n" + "=" * 60)
    print("VÉRIFICATION RAPIDE")
    print("=" * 60)
    # Check that originals are gone from anonymized text
    all_ok = True
    for placeholder, original in result.replacements.items():
        if original in result.anonymized_text:
            print(f"  ❌ '{original}' est encore présent dans le texte anonymisé !")
            all_ok = False
    if all_ok and result.replacements:
        print("  ✅ Toutes les valeurs sensibles ont été remplacées.")
    elif not result.replacements:
        print("  ⚠️  Rien n'a été remplacé — vérifie que le texte contient des données personnelles.")


if __name__ == "__main__":
    # Si un fichier est passé en argument, l'utiliser
    if len(sys.argv) > 1:
        filepath = sys.argv[1]
        if not os.path.exists(filepath):
            print(f"Fichier introuvable : {filepath}")
            sys.exit(1)
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
        print(f"Test sur le fichier : {filepath}\n")
    else:
        text = CV_SAMPLE
        print("Test sur le CV d'exemple (modifie CV_SAMPLE dans le script pour tester le tien)\n")

    run_test(text)
