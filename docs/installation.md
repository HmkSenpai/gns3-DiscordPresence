# Installation

## Prérequis

| Élément | Exigence |
|---|---|
| Python | 3.9 ou plus (3.11+ recommandé) |
| GNS3 | 2.2 ou plus (l'API v2 est utilisée) |
| Discord | Le client **desktop** doit être lancé (c'est lui qui possède le named pipe IPC) |
| Réseau | Aucun : tout est local |

> Discord Rich Presence ne fonctionne qu'avec le client **desktop**. Le client
> mobile ne lit pas les activités des applications tierces.

---

## 1. Installation depuis les sources

```bash
git clone https://github.com/Hinmaka/gns3-DiscordPresence.git
cd gns3-DiscordPresence

python -m venv .venv
.venv\Scripts\activate            # Windows
source .venv/bin/activate         # Linux / macOS

pip install -r requirements.txt
```

Installation minimale (sans icône de notification) :

```bash
pip install pypresence            # + tomli si Python < 3.11
```

---

## 2. Installation avec `pipx` (installation isolée, recommandée)

```bash
pipx install "gns3-discordpresence @ git+https://github.com/Hinmaka/gns3-DiscordPresence.git"
gns3-presence --check
```

---

## 3. Exécutable portable

Télécharge l'archive correspondant à ton système depuis la page
[Releases](https://github.com/Hinmaka/gns3-DiscordPresence/releases) :

| Système | Archive |
|---|---|
| Windows | `gns3-presence-windows.zip` |
| Linux | `gns3-presence-linux.tar.gz` |
| macOS | `gns3-presence-macos.tar.gz` |

Décompresse **dans un dossier de ton choix** (par exemple `C:\Tools\GNS3Presence`) :

```
GNS3Presence/
├── gns3-presence.exe
└── exemples/
    ├── config.toml      ← config commentée, copiée à la 1re utilisation
    ├── LISEZ-MOI.txt
    └── assets/          ← icônes à uploader sur Discord
```

Le binaire embarque Python, `pypresence` et l'icône de notification : **rien à
installer, aucune dépendance**.

> **SmartScreen** : un binaire non signé est signalé par Windows. Clique sur
> *Informations complémentaires* → *Exécuter quand même*, ou utilise la
> version Python.

---

## 4. Premier lancement : l'assistant

Le programme ne demande **aucune configuration manuelle**. Au premier
lancement, l'assistant s'affiche :

```
====================================================
 GNS3 Presence - assistant de premier lancement
====================================================
Aucune application Discord n'est encore configuree.

  1. Utiliser l'application partagee 'GNS3 Presence'
     -> zero configuration, l'affichage est immediat sur votre profil

  2. Utiliser ma propre application Discord
     -> https://discord.com/developers/applications
```

### Option 1 — l'application partagée

Aucun réglage à faire. L'assistant écrit un `config.toml` à côté de
l'exécutable et la présence s'affiche immédiatement avec les icônes par défaut
du projet.

> Cette application est celle créée par l'auteur du projet. L'Application ID
> est public : tout le monde peut l'utiliser. Si tu veux tes propres icônes
> et ton propre nom d'application, prends l'option 2.

### Option 2 — ta propre application Discord

1. <https://discord.com/developers/applications> → **New Application**.
2. Nom de l'application : `GNS3 Presence` (évite d'utiliser la marque `GNS3`
   seule, qui appartient à GNS3 Technologies).
3. **General Information** → copie l'**Application ID** et colle-le dans
   l'assistant.
4. **Rich Presence** → **Art Assets** → uploade les images du dossier
   `exemples/assets/` : `gns3`, `router`, `switch`, `pc`, `firewall`, `vm`,
   `idle`. La clé de chaque asset est le nom du fichier sans extension.

L'assistant peut être relancé à tout moment :

```bash
gns3-presence --setup
```

### Où est écrit le `config.toml` ?

| Situation | Emplacement |
|---|---|
| Exécutable portable (dossier `exemples/` à côté) | à côté de l'exécutable |
| Installation Python | `%APPDATA%\GNS3Presence\config.toml` (Windows), `~/.config/GNS3Presence/config.toml` (Linux), `~/Library/Application Support/GNS3Presence/config.toml` (macOS) |

Le fichier est **rechargé à chaud** : modifie-le sans relancer le programme.

---

## 5. Personnalisation graphique

Au lancement, une **interface web locale** s'ouvre automatiquement dans le
navigateur :

```
┌──────────────────────────────────────────┬─────────────────────────────┐
│  APERÇU EN DIRECT                        │  CE QUI EST AFFICHÉ         │
│  ┌────────────────────────────────┐      │  ☐ Montrer le nom du projet │
│  │ GNS3 Presence                  │      │  ☐ Montrer les nœuds       │
│  │ TP0-CamTrust                   │      │  ☐ Montrer le temps écoulé │
│  │ 6/8 nœuds · 12 liens          │      │  ☐ Montrer l'icône equip.  │
│  │ il y a 42 min                  │      │  ☐ Mode discret            │
│  └────────────────────────────────┘      │                             │
│  Lab : TP0-CamTrust (running)            │  [Enregistrer et appliquer] │
└──────────────────────────────────────────┴─────────────────────────────┘
```

- Serveur local sur `127.0.0.1:8765` : **jamais** accessible depuis le réseau.
- Chaque session a un jeton aléatoire dans l'URL.
- L'aperçu affiche exactement ce qui sera publié sur Discord.
- Les réglages sont écrits dans `config.toml` et appliqués immédiatement.

```bash
gns3-presence              # interface + présence (par défaut)
gns3-presence --web        # force l'ouverture de l'interface
gns3-presence --no-web     # sans interface
gns3-presence --web-port 9000
```

---

## 6. Vérification

```bash
gns3-presence --check
```

Tout doit être en `[OK]`. Si `GNS3 server` est en `[KO]`, démarre GNS3 ou
renseigne `[gns3] url`.

Puis lance le tool :

```bash
gns3-presence
```

---

## 7. Démarrage automatique

| Système | Commande |
|---|---|
| Windows | `python -m gns3presence --install-autostart` |
| macOS | `python -m gns3presence --install-autostart` (agent `launchd`) |
| Linux | `python -m gns3presence --install-autostart` (entrée `~/.config/autostart`) |

Pour annuler : `--uninstall-autostart`.

---

## 8. Mise à jour

```bash
git pull
pip install -r requirements.txt
```

Ou, avec un exécutable, télécharge la nouvelle archive et remplace l'ancien
binaire (ton `config.toml` n'est pas touché).
