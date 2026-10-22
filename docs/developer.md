# Guide développeur

## Installation

```bash
git clone https://github.com/Hinmaka/gns3-DiscordPresence.git
cd gns3-DiscordPresence
python -m venv .venv
.venv\Scripts\activate          # Windows
source .venv/bin/activate       # Linux / macOS
pip install -e ".[dev,tray]"
```

## Tests et lint

```bash
pytest                      # 28 tests, aucun accès réseau ni Discord requis
ruff check .
ruff format .
```

Les tests utilisent des états synthétiques : aucun serveur GNS3 n'est
nécessaire.

## Architecture

```
gns3presence/
├── __init__.py     version et métadonnées
├── __main__.py     python -m gns3presence
├── cli.py          arguments, diagnostic (--check), boucle principale, autostart
├── config.py       valeurs par défaut, fusion profonde, rechargement à chaud
├── discovery.py    découverte du serveur GNS3 (fichiers, env, ports)
├── gns3_api.py     client REST v2 (stdlib) + lecture des fichiers .gns3
├── state.py        LabState, sélection du projet, détection de processus
├── render.py       presets, règles, vie privée, rendu de l'activité
├── presence.py     publication Discord (pypresence), rate limiting
├── i18n.py         traductions fr/en
├── log.py          logs console + fichier rotatif
└── tray.py         icône de notification (optionnel)

entrypoint.py      point d'entrée pour PyInstaller (imports absolus)
tools/             génération des icônes, scripts de maintenance
tests/             suite de tests pytest
```

### Points d'extension

| Besoin | Où agir |
|---|---|
| Nouveau preset | `PRESETS` dans `render.py` |
| Nouveau type d'équipement | `[categories]` + `[images]` dans la config |
| Nouveau format de serveur | `discovery.py` |
| Autre transport Discord | `presence.py` |
| WebSocket GNS3 (temps réel) | `state.py` (`/v2/projects/{id}/notifications/ws`) |

## Construire l'exécutable

```bash
pip install pyinstaller
pyinstaller --onefile --name gns3-presence \
    --collect-all pypresence \
    entrypoint.py
```

Le binaire obtenu se trouve dans `dist/`. En mode *onefile*, le fichier
`config.toml` est cherché **à côté** de l'exécutable (mode portable).

> Un exécutable non signé déclenche SmartScreen. Publie plutôt les sources
> Python, ou signe le binaire avec un certificat.

## Publication

Le workflow `.github/workflows/release.yml` construit l'exécutable pour
Windows, Linux et macOS à chaque tag `v*` et publie une *release* avec les
checksums.

```bash
git tag v1.0.0
git push origin v1.0.0
```

## Idiomes du projet

- Python >= 3.9, annotations `from __future__ import annotations`.
- Pas de dépendance obligatoire hors `pypresence` (+ `tomli` avant 3.11) :
  l'API GNS3 et les logs n'utilisent que la bibliothèque standard.
- Le code est en anglais, la documentation en français (le README contient un
  résumé anglais).
- Toute nouvelle fonctionnalité s'accompagne d'un test.
