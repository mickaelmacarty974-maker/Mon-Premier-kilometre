# Mon Premier Kilomètre

Forum francophone pour les personnes qui commencent le sport ou la course à pied.

## Démarrage sur Windows

1. Installer Python 3.11 ou supérieur.
2. Dans ce dossier, ouvrir un terminal :
   `py -m venv .venv`
   `.venv\Scripts\activate`
   `pip install -r requirements.txt`
3. Définir une clé secrète persistante (PowerShell) :
   `$env:SECRET_KEY = "remplacer-par-une-longue-cle-secrete-aleatoire"`
4. Lancer une première fois : `python app.py` puis ouvrir http://127.0.0.1:5000

Les comptes, sujets et réponses sont enregistrés dans `forum.sqlite3` (SQLite).

## Déploiement public

L'application nécessite un hébergement **Python avec stockage persistant** (VPS, Render avec disque persistant, etc.). Un simple hébergement statique type Cloudflare Pages ne suffit pas pour les comptes et messages. Pour un lancement public, configurer `SECRET_KEY`, `DATABASE` sur un disque persistant, `HTTPS_ONLY=1` derrière HTTPS, puis démarrer avec :

`waitress-serve --listen=0.0.0.0:8080 app:app`

Initialiser la base avant le premier démarrage : `python -c "from app import init_db; init_db()"`.

**Avant une ouverture au public :** ajouter vérification des emails, réinitialisation des mots de passe, limitation de débit anti-spam, modération et signalement des messages, politique de confidentialité / mentions légales, sauvegardes et procédure de suppression des comptes. La version livrée est une base fonctionnelle, pas un service public prêt à l'échelle.
