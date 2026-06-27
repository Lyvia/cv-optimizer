"""
guide_content.py — Static help text for the "How to Use" tab.
Kept as plain markdown constants (English + French) — this is fixed
help content, not something that needs templating. Selected by the
same global interface-language switcher as the rest of the UI.
"""

GUIDE_EN = """
## How this app works

**1. Pick the interface and output language** (top of the page) — the interface
language controls every label and button. The output language controls only the
*generated* CV, cover letter, and analysis; it doesn't need to match the language of
the CV or job description you paste in.

**2. Go to the "Input" tab**
- Paste or upload your CV (PDF, DOCX, or TXT)
- Paste or upload the job description — this is optional; without it, the app still
  produces a general ATS analysis and a general-purpose optimized CV
- Optionally enable anonymization to strip your name, email, phone, and links before
  anything is sent to the AI (recommended)
- Click **Generate**

**3. Check the "CV Analysis" tab**
A match score, strengths, gaps, ATS issues, and a top-5 priority action list.

**4. Open the "Results" tab**
At the top, pick one of 3 ready-made visual styles, or switch to Advanced mode to set
your own main text color, heading color, and font (4 choices). The live preview updates
instantly and never calls the AI — feel free to experiment freely. Below that, two
sub-tabs:
- **CV** — the optimized CV, DOCX/PDF downloads, the change log, and a collapsible
  "Refine this CV with AI" chat. Each refinement instruction shows its proposed changes
  as a line-by-line diff: accept or ignore each change individually, or use Accept All /
  Ignore All. Accepting is final for the session — a one-time warning appears before the
  first acceptance.
- **Cover Letter** — the letter, DOCX/PDF downloads, and a similar refine chat; each
  response can replace the current letter with one confirmation click.

A "Download everything" button bundles both current documents into a ZIP.

### AI usage limit
To keep this free for everyone, each session is capped at **10 AI generations**
(the initial Generate click counts as 1; each refinement instruction — CV or letter —
also counts as 1). The remaining count is shown near the Generate button and in the
Results tab's refine chats.

### ⚠️ Disclaimer
AI-generated content can contain mistakes, inaccuracies, or invented details. **You are
responsible for reviewing and validating the final CV and cover letter before sending
them** to an employer.
"""

GUIDE_FR = """
## Comment fonctionne l'application

**1. Choisissez la langue de l'interface et la langue de sortie** (en haut de la page) —
la langue de l'interface contrôle tous les labels et boutons. La langue de sortie ne
contrôle que le CV, la lettre de motivation et l'analyse *générés* ; elle n'a pas besoin
de correspondre à la langue du CV ou de la fiche de poste que vous collez.

**2. Allez dans l'onglet « Input »**
- Collez ou importez votre CV (PDF, DOCX ou TXT)
- Collez ou importez la fiche de poste — c'est optionnel ; sans elle, l'application
  produit quand même une analyse ATS générale et un CV optimisé de façon générale
- Activez si besoin l'anonymisation pour retirer nom, email, téléphone et liens avant
  tout envoi à l'IA (recommandé)
- Cliquez sur **Generate**

**3. Consultez l'onglet « CV Analysis »**
Un score de correspondance, les points forts, les lacunes, les problèmes ATS et un top 5
des actions prioritaires.

**4. Ouvrez l'onglet « Results »**
En haut, choisissez un des 3 styles visuels prêts à l'emploi, ou passez en mode avancé
pour définir votre propre couleur de texte principal, couleur des titres et police
(4 choix). L'aperçu se met à jour instantanément et n'appelle jamais l'IA — essayez
librement. En dessous, deux sous-onglets :
- **CV** — le CV optimisé, les téléchargements DOCX/PDF, le journal des modifications, et
  un chat repliable « Refine this CV with AI ». Chaque instruction de raffinement affiche
  ses changements proposés sous forme de diff ligne par ligne : acceptez ou ignorez
  chaque changement individuellement, ou utilisez Accept All / Ignore All. Une fois
  accepté, c'est définitif pour la session — un avertissement unique apparaît avant la
  première acceptation.
- **Cover Letter** — la lettre, les téléchargements DOCX/PDF, et un chat de raffinement
  similaire ; chaque réponse peut remplacer la lettre actuelle en un clic de confirmation.

Un bouton « Download everything » regroupe les deux documents actuels dans un ZIP.

### Limite d'utilisation de l'IA
Pour que ce service reste gratuit pour tous, chaque session est limitée à
**10 générations IA** (le premier clic sur Generate compte pour 1 ; chaque instruction de
raffinement — CV ou lettre — compte aussi pour 1). Le nombre restant est affiché près du
bouton Generate et dans les chats de raffinement de l'onglet Results.

### ⚠️ Avertissement
Le contenu généré par l'IA peut contenir des erreurs, des imprécisions ou des détails
inventés. **Vous êtes responsable de relire et de valider le CV et la lettre de
motivation finaux avant de les envoyer** à un employeur.
"""
