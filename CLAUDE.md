# CV Optimizer — CLAUDE.md

## Stack
Python · Streamlit · Anthropic SDK
CSS custom injecté via `src/styles.py` → `st.markdown(unsafe_allow_html=True)`

## Commandes
```
streamlit run app.py              # démarrer l'app
pip install -r requirements.txt   # installer les dépendances
python -m pytest test_anonymizer.py -v  # lancer les tests
docker build -t cv-optimizer .    # build Docker
```

## Structure
```
app.py                  # entry point Streamlit — orchestration UI
src/
  prompts.py            # system prompts LLM — fichier critique
  llm_client.py         # appels API Claude — point d'entrée unique
  parsers.py            # parsing des CVs entrants
  anonymizer.py         # anonymisation des données
  exporters.py          # export PDF/DOCX
  preview.py            # prévisualisation du CV
  guide_content.py      # contenu de guidage utilisateur
  styles.py             # CSS custom Streamlit
test_anonymizer.py      # tests unitaires anonymizer
.env                    # ne jamais lire ni modifier
```

## API Claude
Clé d'API : variable d'env `ANTHROPIC_API_KEY` uniquement.
Tous les appels API passent par `src/llm_client.py` — ne jamais appeler l'API ailleurs.
Modèle par défaut : `claude-sonnet-4-6`
Utiliser Opus uniquement si raisonnement complexe explicitement demandé.

## Style de code
- Typage Python systématique (type hints)
- Fonctions courtes, une responsabilité
- Commentaires en français

## Interdictions
- Ne jamais hardcoder une clé API ou donnée sensible
- Ne jamais modifier `src/prompts.py` sans confirmation explicite
- Ne jamais créer de nouveaux appels API Claude hors `src/llm_client.py`
- Ne pas introduire de dépendances absentes de `requirements.txt` sans demander
- Ne pas refactorer du code hors scope de la tâche demandée
- Ne pas utiliser `st.experimental_*` (APIs dépréciées)

## Avant toute tâche longue
- Poser 1 question si l'intention est ambiguë
- Annoncer les fichiers qui vont être modifiés
- Signaler si une modification touche `src/prompts.py` ou `src/llm_client.py`