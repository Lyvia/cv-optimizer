# 📄 CV Optimizer AI

[🇬🇧 English](README.md) | 🇫🇷 Français

> Importez un CV et (optionnellement) une fiche de poste → obtenez un CV optimisé ATS, une lettre de motivation sur mesure, une analyse détaillée, et une explication de chaque modification effectuée. Entièrement piloté par l'IA, multilingue, multi-fournisseur.

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.35%2B-red)](https://streamlit.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## ⚠️ Avertissement

Le contenu généré par l'IA peut contenir des erreurs ou des imprécisions. **Vous êtes
responsable de relire et de valider le CV et la lettre de motivation finaux** avant de
les envoyer à un employeur. Cet outil est une aide à la rédaction — il ne remplace pas
votre propre jugement.

---

## ✨ Fonctionnalités

- **CV optimisé ATS** — réécrit votre CV avec les mots-clés et la structure exacts que recherchent les systèmes ATS
- **Fonctionne avec ou sans fiche de poste** — fournissez-en une pour un résultat ciblé, ou passez-la pour une optimisation ATS générale
- **Lettre de motivation sur mesure** — unique pour le poste, pas de modèle générique
- **Analyse du CV** — score, points forts, lacunes, problèmes ATS, actions prioritaires
- **Journal des modifications** — explique chaque changement et sa raison
- **Chat de raffinement IA** — donnez des instructions en langage naturel pour ajuster n'importe quel résultat
- **Choix de style visuel** — 3 modèles prêts à l'emploi ou un mode avancé (couleur du texte, couleur des titres, police), avec un aperçu instantané, gratuit et local qui ne consomme jamais de token IA
- **Interface bilingue** — toute l'interface bascule entre anglais et français avec un seul bouton, indépendamment de la langue de sortie
- **Langue de sortie** — français, anglais, espagnol, allemand, italien (indépendante de la langue de l'interface)
- **Quota IA par session** — limité à 10 générations IA par session pour garder l'application soutenable
- **Multi-fournisseur** — Anthropic Claude, Google Gemini (gratuit), Groq (gratuit)
- **Export DOCX & PDF** — téléchargez le CV et la lettre en `.docx` ou `.pdf`, avec le style visuel choisi
- **Raffinement IA en ligne avec relecture des changements** — affinez le CV ou la lettre par chat depuis l'onglet Résultats ; les changements du CV s'affichent comme un diff ligne par ligne que vous acceptez ou ignorez individuellement (ou tous à la fois) avant qu'ils ne deviennent définitifs
- **Téléchargement groupé** — récupérez tout dans un seul `.zip`
- **Anonymisation des données personnelles** — retire optionnellement nom, email, téléphone, liens avant tout envoi à l'IA

---

## 🏗️ Architecture

```
cv-optimizer/
├── app.py                  ← Interface Streamlit + logique d'orchestration
├── src/
│   ├── parsers.py          ← Extraction PDF / DOCX / TXT
│   ├── llm_client.py       ← Interface unifiée LLM (Anthropic / Gemini / Groq)
│   ├── prompts.py          ← Modèles de prompts avec injection de langue
│   ├── utils.py            ← strip_fences() — nettoie les ``` parasites de l'IA
│   ├── differ.py           ← Diff ligne par ligne + reconstruction accept/ignore
│   ├── exporters.py        ← Conversion Markdown → DOCX (sensible au style)
│   ├── pdf_exporter.py     ← Conversion Markdown → PDF (sensible au style, fpdf2)
│   ├── styles.py           ← Définitions de style visuel (modèles, polices, couleurs)
│   ├── preview.py          ← Aperçu HTML local et gratuit (sans appel IA)
│   ├── anonymizer.py       ← Détection des données personnelles & substitution
│   ├── i18n.py             ← Dictionnaire de chaînes d'interface EN/FR
│   └── guide_content.py    ← Contenu long de l'onglet « Comment utiliser » (EN/FR)
├── requirements.txt
├── Dockerfile
├── .env.example
├── README.md
└── README.fr.md
```

**Flux de données :**

```
[Fichier CV + fiche de poste optionnelle]
         │
         ▼
    parsers.py  (extraction du texte)
         │
         ▼
    prompts.py  (construction des prompts)
         │
         ▼
   llm_client.py  (appel à l'API du LLM) → utils.strip_fences()
         │
         ├── Analyse du CV             →  Onglet « CV Analysis »
         ├── CV optimisé + changements →  Onglet « Results » › sous-onglet CV
         └── Lettre de motivation      →  Onglet « Results » › sous-onglet Cover Letter
                  │                          │
                  │                          └─ chat de raffinement → differ.py (relecture du diff)
                  ▼
     exporters.py / pdf_exporter.py + styles.py  (→ .docx / .pdf stylé)
```

---

## 💰 Coûts & fournisseurs

| Fournisseur | Modèle | Coût | Niveau gratuit |
|---|---|---|---|
| **Anthropic** | claude-3-5-haiku | ~$0,01 / génération | ❌ |
| **Anthropic** | claude-3-5-sonnet | ~$0,04 / génération | ❌ |
| **Google** | gemini-2.5-flash | $0,00 | ✅ avec limite de débit |
| **Google** | gemini-2.0-flash | $0,00 | ✅ avec limite de débit |
| **Groq** | llama-3.1-8b | $0,00 | ✅ avec limite de débit |
| **Groq** | llama-3.3-70b | $0,00 | ✅ avec limite de débit |

**Recommandation pour un coût nul :** Google Gemini 2.5 Flash ou Groq Llama 3.3 70B.
**Recommandation pour la meilleure qualité :** Anthropic claude-3-5-sonnet (~0,04€ par génération complète).

Pour rester soutenable quel que soit le fournisseur, chaque session de navigateur est
limitée à **10 générations IA** (le premier clic sur « Generate » compte pour 1, chaque
instruction de raffinement dans le chat compte aussi pour 1).

---

## 🚀 Démarrage rapide

### Prérequis

- Python 3.10+
- Une clé API d'au moins un fournisseur (voir les liens ci-dessous)

### 1. Cloner le dépôt

```bash
git clone https://github.com/YOUR_USERNAME/cv-optimizer.git
cd cv-optimizer
```

### 2. Créer un environnement virtuel

```bash
python -m venv venv
source venv/bin/activate        # macOS / Linux
# venv\Scripts\activate         # Windows
```

### 3. Installer les dépendances

```bash
pip install -r requirements.txt
```

### 4. Configurer les variables d'environnement (optionnel)

```bash
cp .env.example .env
# Modifiez .env et ajoutez vos clés API
```

> Les clés API peuvent aussi être saisies directement dans la barre latérale de l'application — `.env` n'est pas obligatoire.

### 5. Lancer l'application

```bash
streamlit run app.py
```

Ouvrez [http://localhost:8501](http://localhost:8501) dans votre navigateur.

---

## 🐳 Docker

```bash
# Build
docker build -t cv-optimizer .

# Run
docker run -p 8501:8501 cv-optimizer

# Avec des variables d'environnement
docker run -p 8501:8501 \
  -e GOOGLE_API_KEY=votre_cle \
  cv-optimizer
```

---

## ☁️ Déployer sur Streamlit Community Cloud (gratuit)

1. Poussez ce dépôt sur GitHub
2. Allez sur [share.streamlit.io](https://share.streamlit.io/)
3. Connectez votre dépôt GitHub
4. Définissez `app.py` comme fichier principal
5. Ajoutez vos clés API dans **Settings → Secrets** (format : `GOOGLE_API_KEY = "votre_cle"`)
6. Déployez

---

## 🔑 Obtenir des clés API

| Fournisseur | URL | Gratuit ? |
|---|---|---|
| Anthropic | https://console.anthropic.com/ | Non (paiement à l'usage) |
| Google AI Studio | https://aistudio.google.com/app/apikey | Oui |
| Groq | https://console.groq.com/keys | Oui |

---

## 📋 Guide d'utilisation

L'application elle-même intègre un **onglet « 📘 Comment utiliser »** avec le même guide.
Toute l'interface — y compris ce guide — bascule entre anglais et français grâce au
bouton tout en haut de la page.

### Étape 1 — Choisir la langue de l'interface et la langue de sortie (en haut de la page)

Ce sont les deux premiers contrôles de la page : la **langue de l'interface** (anglais/
français, affecte tous les labels et boutons) et la **langue de sortie** (anglais,
français, espagnol, allemand, italien — affecte uniquement les documents *générés*,
indépendamment de la langue de l'interface et de la langue de votre CV/fiche de poste).

### Étape 2 — Fournir les entrées (onglet « 📤 Entrée »)

- **CV** : importez un fichier PDF, DOCX ou TXT — ou collez le texte directement
- **Fiche de poste** : mêmes options, **optionnelle** — sans elle, vous obtenez quand
  même une analyse ATS générale et un CV optimisé de façon générale
- Cliquez sur **🚀 Générer**

Le traitement prend 30 à 90 secondes (3 appels API), et compte pour 1 des 10 générations
IA de la session.

### Étape 3 — Consulter les résultats (onglet « ✨ Résultats »)

En haut : choisissez un des 3 styles visuels prêts à l'emploi, ou passez en mode avancé
pour définir votre propre couleur de texte, couleur des titres et police (4 choix) —
l'aperçu se met à jour instantanément et n'appelle jamais l'IA. En dessous, deux
sous-onglets :

- **CV** — le CV optimisé ATS, les boutons de téléchargement DOCX/PDF, le journal des
  modifications, et un chat repliable **« 🔄 Affiner ce CV avec l'IA »**. Chaque instruction
  de raffinement affiche ses changements proposés sous forme de diff ligne par ligne :
  acceptez ou ignorez chaque changement individuellement, ou utilisez Tout accepter/Tout
  ignorer. Une fois accepté, c'est définitif pour la session — un avertissement unique
  apparaît avant la première acceptation.
- **Lettre de motivation** — la lettre, les boutons DOCX/PDF, et un chat de raffinement
  similaire ; chaque réponse peut remplacer la lettre actuelle en un clic de confirmation.

Un bouton « Tout télécharger » en ZIP regroupe les deux documents actuels.

### Étape 4 — Vérifier l'analyse (onglet « 🔍 Analyse du CV »)
- Score de correspondance (0-100)
- Points forts par rapport au poste
- Mots-clés et compétences manquants
- Problèmes techniques ATS
- Top 5 des actions prioritaires

Chaque instruction de raffinement (CV ou lettre) compte pour 1 des 10 générations IA de
la session.

---

## 🔧 Détails techniques

### Extraction de documents

| Format | Bibliothèque | Notes |
|---|---|---|
| PDF | `pdfplumber` | PDF textuels uniquement. Les scans image nécessitent un OCR (non inclus). |
| DOCX | `python-docx` | Extrait les paragraphes + cellules de tableaux |
| TXT | natif | UTF-8 avec repli en latin-1 |

### Conception des prompts LLM

Chaque prompt :
- Impose la langue de sortie en tête
- Utilise une structure de sections stricte (impose des titres markdown)
- Demande des résultats quantifiés
- Utilise un séparateur `---CHANGES---` pour scinder le CV de son explication en un seul appel
- Bascule vers une version générale de la tâche si aucune fiche de poste n'est fournie

### Style visuel & export DOCX/PDF

`styles.py` définit `StyleConfig` (couleur du texte principal, couleur des titres,
couleur d'accent, police, plus les indicateurs `heading_uppercase`/`heading_border` par
modèle) ainsi que 3 modèles prêts à l'emploi et 4 choix de police. `preview.py`
transforme n'importe quel `StyleConfig` en HTML local pour un aperçu instantané et sans
token. `exporters.py` (DOCX) et `pdf_exporter.py` (PDF, via `fpdf2`) appliquent tous les
deux ce même `StyleConfig` lors de la génération, en analysant le markdown produit par
le LLM :
- `#` → H1 (centré, couleur des titres)
- `##` → H2 (majuscules + bordure inférieure, chacune togglable par style)
- `###` → H3
- `-` / `*` → liste à puces
- `1.` → liste numérotée
- `**texte**` → gras
- `*texte*` → italique
- `---` → ligne horizontale (bordure)

Compatible ATS : pas de tableaux, pas de zones de texte, pas d'éléments flottants. Les
réponses du LLM passent aussi par `utils.strip_fences()` pour retirer tout ``` parasite
avant affichage ou export.

### Raffinement du CV avec relecture du diff

`differ.py` calcule un diff ligne par ligne (`difflib`) entre le CV actuellement accepté
et une nouvelle version affinée par l'IA. Chaque bloc (`equal` / `added` / `removed` /
`replaced`) reçoit un `chunk_id` ; les décisions d'acceptation/ignorance par bloc sont
stockées dans l'état de session et `rebuild_text()` reconstruit le CV de travail à partir
de ces décisions — rien n'est appliqué avant acceptation explicite, et les suppressions
pures ne prennent effet que via « Tout accepter ».

---

## 🤝 Contribuer

Les pull requests sont bienvenues. Pour les changements majeurs, ouvrez d'abord une issue.

```bash
# Lancer en local avec rechargement à chaud
streamlit run app.py --server.runOnSave true
```

---

## 📜 Licence

MIT — voir le fichier [LICENSE](LICENSE).
