# GNS3 Presence

[![CI](https://github.com/Hinmaka/gns3-DiscordPresence/actions/workflows/tests.yml/badge.svg)](https://github.com/Hinmaka/gns3-DiscordPresence/actions/workflows/tests.yml)
[![Python](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Discord](https://img.shields.io/badge/Discord-Rich%20Presence-5865F2?logo=discord&logoColor=white)](https://discord.com/developers/applications)

**Affiche en direct ton activité GNS3 sur ton profil Discord.**

Quand tu travailles sur un lab GNS3, tes amis voient ton projet, le nombre de
nœuds démarrés et depuis combien de tu tournes. Zéro configuration, et ça
fonctionne sur n'importe quel PC : le serveur GNS3 est découvert
automatiquement (port 3080, 80, GNS3 VM, contrôleur distant…).

```
┌──────────────────────────────────────┐
│  GNS3 Presence                       │  ← nom de l'application Discord
│  TP0-CamTrust                        │  ← details
│  6/8 nœuds · 12 liens                │  ← state
│  ⏱ il y a 42 minutes                 │  ← horodatage
│  [Voir le lab]  [Mon GitHub]         │  ← 2 boutons
└──────────────────────────────────────┘
```

---

## Sommaire

- [Ce que ça fait](#ce-que-ça-fait)
- [Démarrage rapide (3 étapes)](#démarrage-rapide-3-étapes)
- [Installation](#installation)
- [Utilisation](#utilisation)
- [Personnalisation](#personnalisation)
- [Confidentialité](#confidentialité)
- [Comment ça marche](#comment-ça-marche)
- [Dépannage](#dépannage)
- [Contribuer](#contribuer)

---

## Ce que ça fait

| | |
|---|---|
| **Projet courant** | Le nom du lab ouvert dans GNS3 |
| **Nœuds actifs** | `6/8 nœuds` + le compteur « x sur y » de Discord |
| **Résumé du lab** | `3 routeurs · 2 switchs · 3 PC` |
| **Horodatage** | Temps écoulé depuis l'ouverture du lab |
| **Icône dynamique** | L'icône suit le type d'équipement dominant (routeur, switch, PC…) |
| **Boutons** | Jusqu'à 2 liens (GitHub, doc du TP, ton serveur Discord…) |
| **Présets** | `minimal`, `student`, `teacher`, `streamer`, `compact` |
| **Règles par projet** | Un affichage différent pour `TP0-*`, `Examen-*`, etc. |
| **Mode discret** | Masque automatiquement le nom des labs d'examen |

---

## Démarrage rapide (3 étapes)

### 1. Télécharge l'exécutable

Depuis la page [Releases](https://github.com/Hinmaka/gns3-DiscordPresence/releases) :
`gns3-presence-windows.zip`, `gns3-presence-linux.tar.gz` ou
`gns3-presence-macos.tar.gz`.

Décompresse le dossier où tu veux. **Aucune installation, aucune dépendance** :
le binaire embarque Python et toutes les librairies.

```
gns3-presence/
├── gns3-presence.exe      ← lance-le
├── config.toml            ← créé automatiquement au 1er lancement
└── exemples/              ← config commentée + icônes à uploader
```

### 2. Lance-le : un assistant s'occupe du reste

Au premier lancement, l'assistant te propose :

```
  1. Utiliser l'application partagée 'GNS3 Presence'
     -> zéro configuration, l'affichage est immédiat sur ton profil

  2. Utiliser ma propre application Discord
     -> https://discord.com/developers/applications
```

- **Option 1** : rien à faire, la présence s'affiche immédiatement avec les
  icônes par défaut du projet.
- **Option 2** : crée ton application, copie l'Application ID, et uploade les
  images de `exemples/assets/` dans *Rich Presence → Art Assets* (la clé de
  chaque asset = nom du fichier **sans** extension). Tu as alors tes propres
  icônes et ton propre nom d'application.

Tu peux changer d'avis à tout moment : `gns3-presence --setup`.

### 3. C'est parti

Lance GNS3, ouvre un lab : ton profil Discord affiche le projet, les nœuds
démarrés et le temps écoulé.

```bash
gns3-presence --check     # diagnostic
gns3-presence             # mode normal
```

> Tu préfères la version Python ? `pip install -r requirements.txt` puis
> `python -m gns3presence` — l'assistant fonctionne à l'identique.

---

## Installation

Guide complet : [`docs/installation.md`](docs/installation.md).

### Option 1 — l'exécutable portable (aucune installation)

Télécharge `gns3-presence-windows.zip` (ou linux/macos) depuis la page
[Releases](https://github.com/Hinmaka/gns3-DiscordPresence/releases),
décompresse le dossier où tu veux et double-clique sur l'exe.

Le binaire embarque Python, `pypresence` et l'icône de notification : **rien à
installer**. Au premier lancement, l'assistant crée le `config.toml` à côté de
l'exe.

### Option 2 — le script (recommandé pour les dévs)

```bash
git clone https://github.com/Hinmaka/gns3-DiscordPresence.git
cd gns3-DiscordPresence
python -m venv .venv
.venv\Scripts\activate          # Windows
source .venv/bin/activate       # Linux / macOS
pip install -r requirements.txt
python -m gns3presence
```

### Option 2 — l'exécutable portable (aucune installation)

Télécharge `gns3-presence.exe` depuis la page
[Releases](https://github.com/Hinmaka/gns3-DiscordPresence/releases),
décompresse le dossier **à côté de GNS3** et double-clique sur l'exe.
Le dossier `config.toml` se trouve à côté de l'exe (mode portable) ou dans :

| Système | Emplacement |
|---|---|
| Windows | `%APPDATA%\GNS3Presence\config.toml` |
| macOS | `~/Library/Application Support/GNS3Presence/config.toml` |
| Linux | `~/.config/GNS3Presence/config.toml` |

### Démarrage automatique avec Windows

```bash
python -m gns3presence --install-autostart   # à installer
python -m gns3presence --uninstall-autostart # à désinstaller
```

---

## Utilisation

```bash
python -m gns3presence                 # mode normal (avec icône dans la zone de notification)
python -m gns3presence --check         # diagnostic complet et sortie
python -m gns3presence --dry-run       # affiche ce qui serait publié, sans toucher Discord
python -m gns3presence --once          # publie une seule fois puis quitte
python -m gns3presence --print-config  # affiche la configuration résolue
python -m gns3presence -v              # logs détaillés
```

| Option | Effet |
|---|---|
| `-c, --config FICHIER` | Utilise un fichier de configuration précis |
| `--setup` | Relance l'assistant (changer d'application Discord) |
| `--shared-app` | Utilise l'application partagée sans toucher à la configuration |
| `--app-id ID` | Impose un Application ID (utile pour les scripts) |
| `--interval SECONDES` | Change l'intervalle d'interrogation de GNS3 |
| `--no-tray` | Désactive l'icône de notification |
| `--install-autostart` | Enregistre le démarrage automatique |

> À la sortie (Ctrl+C, `--once`, fermeture du tool), la présence est **effacée**
> de Discord : pas d'activité fantôme. Laisse le tool tourner pour la garder.

### Diagnostic (`--check`)

```
--------------------------------------------------------------
 GNS3 Presence - diagnostic
--------------------------------------------------------------
[OK] Discord client    : running
[OK] pypresence       : installed
[OK] application id   : 123456789012345678
[OK] GNS3 server      : http://localhost:80 (v2.2.61)
[--] current state    : running (source: api, project: TP0-CamTrust)
[--] nodes            : 6/8 started, 12 links
--------------------------------------------------------------
```

---

## Personnalisation

Tout se passe dans `config.toml` (exemple complet dans
[`config.example.toml`](config.example.toml), référence complète dans
[`docs/configuration.md`](docs/configuration.md)).

```toml
[discord]
app_id = "123456789012345678"

[presence]
preset = "teacher"
details = "{project}"
state  = "{running}/{total} {t_nodes} · {summary}"
large_image = "gns3"
small_image = "{dominant_type}"
timestamp   = "project"
party       = true

[[presence.buttons]]
label = "Voir le lab"
url   = "https://github.com/Hinmaka/gns3-DiscordPresence"

# Un affichage spécifique pour les labs de TP
[[rules]]
match   = "TP0-*"
details = "TP0 - {project}"
state   = "{running}/{total} {t_nodes} · {links} {t_links}"
```

### Variables disponibles dans les modèles

| Variable | Exemple |
|---|---|
| `{project}` | `TP0-CamTrust` |
| `{project_id}` | `861096a7-…` |
| `{running}` / `{total}` | `6` / `8` |
| `{links}` | `12` |
| `{summary}` | `3 routeurs · 2 switchs · 3 PC` |
| `{dominant_type}` | `router` (clé d'icône) |
| `{dominant_label}` | `routeur` |
| `{elapsed}` | `42 min` |
| `{version}` | `2.2.61` |
| `{count.router}` | `3` |
| `{running.switch}` | `2` |

---

## Confidentialité

Rien n'est envoyé sur Internet : le tool parle **uniquement** au client Discord
local (via le named pipe `discord-ipc-0`) et à ton serveur GNS3 local.
Aucun compte, aucune télémétrie, aucun serveur intermédiaire.

Les noms de lab peuvent divulguer un sujet d'examen : le mode discret les masque
automatiquement.

```toml
[privacy]
enabled = true                    # ou false pour ne masquer que les motifs ci-dessous
patterns = ["exam", "examen", "concours", "eval", "noté", "corrigé"]
replacement = "Un lab réseau"
```

---

## Comment ça marche

```
GNS3 (serveur local)                GNS3 Presence                 Discord
┌────────────────────┐             ┌────────────────────┐        ┌──────────┐
│ API REST v2        │───poll──▶  │ rendu + règles     │──IPC──▶│ profil   │
│ + fichiers .gns3   │             │ + rate limiting    │  pipe  │ Rich     │
└────────────────────┘             └────────────────────┘        │ Presence │
                                                                 └──────────┘
```

1. **Découverte** : lecture du fichier de configuration GNS3
   (`gns3_server.ini`), variable `GNS3_URL`, serveurs déclarés par l'interface,
   puis ports habituels (3080, 80, 8000, 8080). Les candidats sont testés **en
   parallèle**.
2. **Lecture d'état** : `GET /v2/projects`, `/v2/projects/{id}/nodes`,
   `/v2/projects/{id}/links`. Si le serveur est injoignable, les fichiers
   `.gns3` du dossier `projects_path` sont lus directement.
3. **Rendu** : application du preset, des règles par projet et du mode discret.
4. **Publication** : le payload n'est envoyé que s'il a changé, et au minimum
   une fois toutes les 15 secondes (l'API Discord tolère ~5 appels / 20 s).

Détail complet : [`docs/how-it-works.md`](docs/how-it-works.md).

---

## Dépannage

| Symptôme | Cause probable | Solution |
|---|---|---|
| Rien ne s'affiche sur Discord | « Afficher l'activité » désactivé | Paramètres utilisateur → Activités → activer l'affichage des activités |
| `application id: missing` | `app_id` non renseigné | Renseigne `discord.app_id` dans `config.toml` |
| `GNS3 server: unreachable` | Serveur arrêté ou port non standard | Lance GNS3, ou renseigne `[gns3] url` |
| Icônes absentes | Assets non uploadés | Uploade les PNG dans *Rich Presence → Art Assets* |
| `401` sur l'API | Serveur GNS3 avec authentification | Renseigne `username` et la variable `password_env` |
| `wpcap.dll introuvable` | WinPcap/Npcap manquant (Windows) | Installe [Npcap](https://npcap.com/) — c'est Dynamips (GNS3) qui le demande, pas ce tool |

Le journal détaillé se trouve dans
`%APPDATA%\GNS3Presence\logs\gns3presence.log` (ou `~/.config/GNS3Presence/logs/`).

---

## Contribuer

Les contributions sont les bienvenues !

```bash
git clone https://github.com/Hinmaka/gns3-DiscordPresence.git
cd gns3-DiscordPresence
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt pytest ruff
pytest              # 28 tests
ruff check .
```

Voir [`docs/developer.md`](docs/developer.md) pour l'architecture détaillée.

---

## English summary

**GNS3 Presence** shows your GNS3 activity on your Discord profile: current
project, running nodes, elapsed time, and up to two buttons. It auto-discovers
your GNS3 server (any port, local or remote) and falls back to reading the
`.gns3` project files when the API is unreachable.

```bash
pip install -r requirements.txt
python -m gns3presence --check
python -m gns3presence
```

Create a Discord application, upload the assets from `assets/large/`, then set
`discord.app_id` in `config.toml`. Everything else is documented in
[`docs/`](docs/).

---

## Licence

MIT — voir [LICENSE](LICENSE).

GNS3 is a trademark of GNS3 Technologies. This project is not affiliated with
nor endorsed by GNS3 Technologies.
