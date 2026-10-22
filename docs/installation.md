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

Décompresse **dans un dossier de ton choix** (par exemple `C:\Tools\GNS3Presence`)
et place ton `config.toml` à côté de l'exécutable :

```
GNS3Presence/
├── gns3-presence.exe
├── config.toml
└── assets/          (facultatif, pour référence)
```

L'exécutable cherche sa configuration :

1. à côté de lui ;
2. sinon dans le dossier utilisateur (`%APPDATA%\GNS3Presence`, …).

> **SmartScreen** : un binaire non signé est signalé par Windows. Clique sur
> *Informations complémentaires* → *Exécuter quand même*, ou utilise la
> version Python.

---

## 4. Configuration de l'application Discord

C'est la partie à faire une seule fois :

1. <https://discord.com/developers/applications> → **New Application**.
2. Nom de l'application : `GNS3 Presence` (évite d'utiliser la marque `GNS3`
   seule).
3. **General Information** → copie l'**Application ID**.
4. **Rich Presence** → **Art Assets** → uploade les fichiers de
   [`assets/large/`](../assets/large) : `gns3`, `router`, `switch`, `pc`,
   `firewall`, `vm`, `idle`.
   La clé de chaque asset est le nom du fichier sans extension.
5. Crée `config.toml` à partir de [`config.example.toml`](../config.example.toml) :

```toml
[discord]
app_id = "123456789012345678"
```

---

## 5. Premier lancement

```bash
python -m gns3presence --check
```

Tout doit être en `[OK]`. Si `GNS3 server` est en `[KO]`, démarre GNS3 ou
renseigne `[gns3] url`.

Puis lance le tool :

```bash
python -m gns3presence
```

---

## 6. Démarrage automatique

| Système | Commande |
|---|---|
| Windows | `python -m gns3presence --install-autostart` |
| macOS | `python -m gns3presence --install-autostart` (agent `launchd`) |
| Linux | `python -m gns3presence --install-autostart` (entrée `~/.config/autostart`) |

Pour annuler : `--uninstall-autostart`.

---

## 7. Mise à jour

```bash
git pull
pip install -r requirements.txt
```

Ou, avec un exécutable, télécharge la nouvelle archive et remplace l'ancien
binaire (ton `config.toml` n'est pas touché).
