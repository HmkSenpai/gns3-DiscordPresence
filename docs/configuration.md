# Configuration

Toute la configuration vit dans un unique fichier TOML.

## Où est le fichier ?

Le tool cherche dans cet ordre et s'arrête au **premier** trouvé :

1. le chemin passé avec `--config` ou la variable `GNS3_PRESENCE_CONFIG` ;
2. `config.toml` **à côté** du script ou de l'exécutable (mode portable) ;
3. le fichier utilisateur :
   - Windows : `%APPDATA%\GNS3Presence\config.toml`
   - macOS : `~/Library/Application Support/GNS3Presence/config.toml`
   - Linux : `~/.config/GNS3Presence/config.toml`

`python -m gns3presence --print-config` affiche la configuration **résolue**
(tas par défaut + tes surcharges), ce qui est la façon la plus rapide de
comprendre ce qui est réellement appliqué.

Le fichier est **rechargé à chaud** : tu peux l'éditer pendant un TP, la
présence est mise à jour au cycle suivant.

---

## `[discord]`

| Clé | Défaut | Description |
|---|---|---|
| `app_id` | `""` | **Obligatoire.** Application ID du portail Discord. |
| `poll_interval` | `15` | Secondes entre deux lectures de l'API GNS3. |
| `min_update_interval` | `15` | Délai minimal entre deux publications Discord. |
| `clear_when_idle` | `true` | Supprime la présence quand GNS3 n'est plus ouvert. |

> `min_update_interval` ne descend pas en dessous de 15 s : l'API Discord
> limite à ~5 appels d'activity par 20 secondes.

---

## `[gns3]`

| Clé | Défaut | Description |
|---|---|---|
| `url` | `"auto"` | URL du contrôleur, ou `auto` pour la découverte. |
| `username` | `""` | Utilisateur si le serveur exige une authentification. |
| `password_env` | `"GNS3_PASSWORD"` | Variable d'environnement contenant le mot de passe. |
| `timeout` | `3.0` | Timeout réseau (secondes) par requête. |
| `projects_path` | `"auto"` | Dossier des projets `.gns3` (mode portable / secours). |
| `fallback_recent_minutes` | `10` | Si l'API ne renvoie aucun projet ouvert, on prend le projet modifié dans les N dernières minutes (`0` = désactivé). |

### Authentification

Le mot de passe n'est **jamais** écrit dans le fichier de configuration : il est
lu dans une variable d'environnement.

```bash
# PowerShell
$env:GNS3_PASSWORD = "mon-mot-de-passe"
python -m gns3presence
```

> GNS3 ne stocke le mot de passe que **haché** dans sa configuration : il est
> techniquement irrécupérable. D'où la variable d'environnement.

### Serveur distant

```toml
[gns3]
url = "http://192.168.1.10:3080"
username = "admin"
```

---

## `[presence]`

| Clé | Défaut | Description |
|---|---|---|
| `preset` | `"student"` | `minimal`, `student`, `teacher`, `streamer`, `compact`. |
| `details` | `"{project}"` | Deuxième ligne de la carte d'activité. |
| `state` | `"{running}/{total} {t_nodes} · {links} {t_links}"` | Troisième ligne. |
| `large_image` | `"gns3"` | Clé de l'image principale. |
| `large_text` | `"GNS3 {version}"` | Infobulle de l'image principale. |
| `small_image` | `"{dominant_type}"` | Clé de la petite image. |
| `small_text` | `"{dominant_label}"` | Infobulle de la petite image. |
| `timestamp` | `"project"` | `project` (depuis l'ouverture du lab), `session`, `none`. |
| `party` | `true` | Affiche le compteur « x sur y ». |
| `buttons` | `[]` | Jusqu'à 2 boutons `[{label, url}]`. |

### Presets

| Preset | `details` | `state` |
|---|---|---|
| `minimal` | `{project}` | `{running}/{total}` |
| `student` | `{project}` | `{running}/{total} {t_nodes} · {links} {t_links}` |
| `teacher` | `{project}` | `{running}/{total} {t_nodes} · {summary}` |
| `streamer` | `{project}` | `{running}/{total} {t_nodes} · {elapsed}` |
| `compact` | `{project}` | `{running}/{total}` |

> Priorité : **ta configuration** > preset > valeur par défaut.

### `[presence.idle]`

Utilisé quand aucun lab n'est ouvert (GNS3 lancé mais aucun projet, ou GNS3
arrêté).

```toml
[presence.idle]
details = "Au repos"
state = "Prêt pour un nouveau lab"
large_image = "idle"
large_text = "GNS3"
small_image = ""
small_text = ""
```

---

## Variables de modèle

| Variable | Description |
|---|---|
| `{project}` | Nom du projet |
| `{project_id}` | Identifiant du projet |
| `{running}` | Nœuds démarrés |
| `{total}` | Nœuds au total |
| `{links}` | Nombre de liens |
| `{summary}` | `3 routeurs · 2 switchs · 3 PC` |
| `{dominant_type}` | Clé d'image du type dominant (`router`, `switch`, `pc`…) |
| `{dominant_label}` | Libellé lisible (`routeur`) |
| `{elapsed}` | Temps écoulé (`42 min`, `1 h 12 min`) |
| `{version}` | Version du serveur GNS3 |
| `{server_url}` | URL du contrôleur |
| `{source}` | `api`, `files` ou `none` |
| `{state}` | `running`, `loaded`, `idle`, `closed` |
| `{t_nodes}`, `{t_links}` | « nœuds », « liens » (traduits) |
| `{count.router}` | Nombre de routeurs |
| `{running.switch}` | Switchs démarrés |

---

## `[privacy]`

| Clé | Défaut | Description |
|---|---|---|
| `enabled` | `false` | Masque toujours le nom du projet. |
| `patterns` | `["exam", "examen", "cc", "concours", "eval", "noté", "corrigé"]` | Motifs qui déclenchent le masquage (regex, insensible à la casse). |
| `hide_node_names` | `true` | Ne montre pas les noms de nœuds. |
| `hide_buttons` | `true` | Supprime les boutons en mode discret. |
| `replacement` | `"Un lab réseau"` | Texte affiché à la place du nom du projet. |

---

## `[images]` et `[categories]`

`[images]` associe une catégorie à une **clé d'asset** Discord (le nom du
fichier PNG uploadé dans le portail).

`[categories]` associe une catégorie aux **types de nœuds GNS3**.

```toml
[images]
router = "router"
switch = "switch"
pc = "pc"
firewall = "firewall"
vm = "vm"
unknown = "gns3"

[categories]
router = ["dynamips", "iou", "router", "cisco"]
switch = ["ethernet_switch", "frame_relay_switch", "atm_switch", "switch"]
pc = ["vpcs", "pc", "virtual_pc", "workstation"]
firewall = ["firewall", "asa", "fortigate", "pfsense"]
vm = ["qemu", "vmware", "virtualbox", "hyper-v", "docker", "linux"]
```

Tu peux ajouter une catégorie (par exemple `antivirus`) et y classer des
équipements : il suffit d'ajouter la clé dans les deux sections et de créer
l'asset correspondant.

---

## `[[rules]]` — affichage par projet

La **première** règle qui correspond est appliquée.

| Clé | Description |
|---|---|
| `match` | Motif : glob (`TP0-*`), regex complète (`/^TP.*$/`) ou `re:...` |
| `details`, `state` | Textes |
| `large_image`, `large_text`, `small_image`, `small_text` | Images |
| `party` | `true` / `false` |
| `timestamp` | `project` / `session` / `none` |
| `buttons` | Liste de boutons (remplace ceux du preset) |
| `privacy` | `true` force le mode discret pour ce projet |

```toml
[[rules]]
match = "TP0-*"
details = "TP0 - {project}"
state = "{running}/{total} {t_nodes} · {summary}"
large_image = "gns3"
small_image = "{dominant_type}"

[[rules]]
match = "re:exam|concours"
privacy = true

[[rules]]
match = "Streaming-*"
details = "En direct - {project}"
buttons = [{ label = "Regarder", url = "https://twitch.tv/..." }]
```

---

## `language`

`"fr"` (défaut) ou `"en"`. Change les mots traduits (`nœuds`, `liens`,
`routeurs`…).
