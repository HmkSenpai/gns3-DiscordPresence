# Comment ça marche

## Vue d'ensemble

```
 ┌──────────────────────┐        ┌─────────────────────────┐        ┌──────────────┐
 │  Serveur GNS3        │        │  GNS3 Presence          │        │  Discord     │
 │                      │        │                         │        │              │
 │  API REST v2  ───────┼──poll──┼─▶ découverte + rendu   │──IPC──┼─▶ profil     │
 │  fichiers .gns3 ─────┼──fallback┼─▶ rate limiting       │  pipe │   Rich       │
 │                      │        │                         │        │   Presence   │
 └──────────────────────┘        └─────────────────────────┘        └──────────────┘
```

Trois briques indépendantes, testables séparément :

| Module | Rôle |
|---|---|
| `discovery.py` | Trouver le serveur GNS3 sans rien coder en dur |
| `gns3_api.py` + `state.py` | Lire l'état du lab (API ou fichiers) |
| `render.py` | Transformer l'état en activité Discord |
| `presence.py` | Publier sans flooder Discord |
| `config.py` | Charger, fusionner et recharger la configuration |

---

## 1. Découverte du serveur GNS3

C'est la brique la plus importante pour la portabilité. Aucun port, chemin ou
mot de passe n'est codé en dur.

### Ordre des candidats

1. `[gns3] url` du fichier de configuration.
2. Variable d'environnement `GNS3_URL`.
3. Fichiers de configuration du serveur GNS3 :
   - Windows : `%APPDATA%\GNS3\<version>\gns3_server.ini` (et `.conf`)
   - macOS : `~/Library/Application Support/GNS3/<version>/`
   - Linux : `~/.config/GNS3/<version>/`
   Les sections `[Server]` donnent `host`, `port`, `protocol`, `auth`,
   `user` et `projects_path`.
4. Serveurs déclarés par l'interface graphique (`gns3_gui.ini` → `Servers`),
   utile pour la **GNS3 VM** (contrôleur dans une VM).
5. Ports habituels : `3080`, `80`, `8000`, `8080`.

### Test en parallèle

Tous les candidats sont testés **simultanément** (threads) : sur un poste où
le pare-feu laisse expirer les connexions, une recherche séquentielle
multiplierait le temps de démarrage par le nombre de ports.

Le premier candidat qui répond à `GET /v2/version` **dans l'ordre de
priorité** est retenu. En cas d'échec, une nouvelle recherche est tentée au
bout de 30 secondes seulement (pas à chaque cycle).

### Repli sur les fichiers

Si l'API est injoignable (serveur arrêté, contrôleur distant hors ligne), les
fichiers `.gns3` du dossier `projects_path` sont lus directement. On obtient
le nom du projet, les nœuds et les liens — mais **pas** les états de démarrage
(pour le restart) : l'API reste la source de vérité.

---

## 2. Lecture de l'état

### API

```
GET /v2/version                         → version du serveur
GET /v2/projects                       → liste des projets + statut
GET /v2/projects/{project_id}/nodes    → nœuds + statut
GET /v2/projects/{project_id}/links    → liens
```

Les statuts utilisés sont ceux **officiels** de GNS3 2.2 :

| Entité | Valeurs |
|---|---|
| Projet | `opened`, `closed` |
| Nœud | `started`, `stopped`, `suspended` |

> Vérifié dans le source de `gns3-server` v2.2.61 :
> `gns3server/schemas/project.py` (enum `opened`/`closed`) et
> `gns3server/controller/project.py`.

### Projet courant

1. Le projet avec le statut `opened` (celui de l'interface graphique).
2. Sinon, l'unique projet ayant des nœuds.
3. Sinon, **filet de sécurité** : le projet dont le fichier `.gns3` a été
   modifié dans les N dernières minutes (`gns3.fallback_recent_minutes`).

---

## 3. Rendu de l'activité

```
LabState ──▶ contexte (variables) ──▶ preset ──▶ règles ──▶ vie privée ──▶ Activity
```

- **Contexte** : `{project}`, `{running}`, `{summary}`, `{dominant_type}`…
- **Preset** : `minimal`, `student`, `teacher`, `streamer`, `compact` — appliqué
  seulement si la clé n'a pas été définie par l'utilisateur.
- **Règles** : la première règle qui correspond au nom du projet l'emporte.
- **Vie privée** : le nom du projet est remplacé, les boutons sont masqués.

Le rendu respecte les limites de Discord : 128 caractères pour `details` et
`state`, 2 boutons maximum, URL `http(s)` obligatoire.

---

## 4. Publication

Discord impose ~5 mises à jour d'activité par 20 secondes.

Le `Publisher` applique donc deux filtres :

1. **Changement** : le payload est haché (SHA-256) ; si le hash est identique
   au dernier envoyé, rien n'est publié.
2. **Fréquence** : au moins `min_update_interval` secondes (15 s par défaut)
   entre deux publications.

Si Discord est fermé puis rouvert, la connexion est rétablie automatiquement
(10 secondes avant la nouvelle tentative). À la sortie, la présence est effacée
(`clear()`) pour ne pas laisser une activité fantôme.

### Protocole

Le transport est le **Discord IPC** local : un named pipe (`\\.\pipe\discord-ipc-0`
sous Windows) ou un socket Unix. C'est le même mécanisme que celui utilisé par
les jeux. Aucune donnée ne transite par Internet.

La bibliothèque [`pypresence`](https://github.com/qwertyquerty/pypresence)
implémente ce protocole ; le tool ne dépend que de `pypresence` (+ `tomli` sur
Python < 3.11). Le tray est optionnel (`pystray` + `pillow`).

---

## 5. Cycle de vie

```
démarrage
   │
   ├─► chargement de la configuration (+ rechargement à chaud)
   │
   ├─► découverte du serveur GNS3
   │
   └─► boucle (toutes les N secondes)
         ├─ lecture de l'état (API, ou fichiers en secours)
         ├─ rendu (preset → règles → vie privée)
         └─ publication (si changé et si le délai minimum est respecté)
```

Arrêt : `Ctrl+C` ou menu du tray → effacement de la présence → fermeture propre.
