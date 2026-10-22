# Dépannage

## Rien ne s'affiche sur mon profil Discord

Vérifie dans l'ordre :

1. **Discord est-il lancé ?** `python -m gns3presence --check` doit indiquer
   `[OK] Discord client : running`.
2. **L'affichage des activités est-il activé ?**
   Paramètres utilisateur → Activités → *Afficher l'activité en cours sur le
   profil*. Certains clients (mobile, mode serveur simplifié) masquent
   l'activité des applications non-jeu.
3. **L'Application ID est-il correct ?** Il doit s'agir du `client_id` de
   l'application Discord, pas de son identifiant interne d'activité.
4. **L'application est-elle bien celle du portail ?** Une présence ne
   s'affiche que si l'application existe et si son nom est « Authorized ».

## `[KO] application id : missing`

Renseigne `discord.app_id` dans `config.toml`. Vérifie le chemin du fichier
utilisé avec :

```bash
python -m gns3presence --print-config
```

## `[KO] GNS3 server : unreachable`

- GNS3 est-il démarré (le serveur, pas forcément l'interface) ?
- Le port est-il inhabituel ? Lance `--check -v` pour voir la liste des
  URLs testées.
- Solution : renseigne `[gns3] url = "http://localhost:3080"`.

Si tu utilises la **GNS3 VM**, le contrôleur est dans la VM : son IP change à
chaque démarrage. Utilise l'adresse de la VM (`http://172.29.x.x:80`) ou laisse
la découverte automatique (`gns3_gui.ini` contient le serveur déclaré).

## `[KO] 401 Unauthorized`

Le serveur GNS3 est en mode authentifié. Le mot de passe stocké par GNS3 est
haché et **non récupérable** : il faut le connaître.

```toml
[gns3]
username = "admin"
password_env = "GNS3_PASSWORD"
```

```bash
# PowerShell
$env:GNS3_PASSWORD = "mon-mot-de-passe"
```

## Les icônes n'apparaissent pas

- Les assets doivent être **uploadés** dans le portail
  (*Rich Presence → Art Assets*), pas seulement présents dans le dépôt.
- La clé = nom du fichier **sans** l'extension : `router.png` → `router`.
- Les images doivent faire 512×512 (grande) ou 128×128 (petite) et peser moins
  de 512 Ko.
- Un `small_image` vide masque volontairement la petite icône.

## La présence ne se met pas à jour

- Le délai minimum est de 15 s : c'est voulu (limite Discord).
- Le contenu doit avoir changé : le tool ne republie jamais un payload
  identique.
- Vérifie le log : `%APPDATA%\GNS3Presence\logs\gns3presence.log`.

## `wpcap.dll est introuvable`

C'est **GNS3 / Dynamips** qui le demande, pas ce tool : WinPcap ou Npcap
n'est pas installé sur le poste. Les labs Cisco IOS (Dynamips) ne démarreront
pas. Installe [Npcap](https://npcap.com/) (mode « Npcap in WinPcap API
compatible mode »).

## `Could not determine the Dynamips version`

Même cause : Dynamips ne démarre pas dans cet environnement. Cela n'empêche pas
le tool de lire l'état du lab ; en revanche l'API GNS3 refuse d'ouvrir un
projet si l'hyperviseur Dynamips est cassé.

## Le tool ne trouve pas mon projet

- Vérifie `projects_path` : par défaut il est lu dans la configuration GNS3.
- Le mode secours lit les fichiers `.gns3` : le dossier doit contenir des
  fichiers `*.gns3` (GNS3 2.x).
- Augmente `fallback_recent_minutes` si tu travailles sur des projets
  différents en permanence.

## L'icône de notification ne s'affiche pas

- Elle nécessite `pystray` et `pillow` : `pip install pystray pillow`.
- Utilise `--no-tray` pour tourner en console.
- Sous Wayland (Linux), l'intégration systray peut être limited.

## Le tool démarre mais ne se ferme pas avec la session Windows

Utilise `--install-autostart` : l'entrée de registre est créée dans
`HKCU\Software\Microsoft\Windows\CurrentVersion\Run`, ce qui est propre et
réversible avec `--uninstall-autostart`.

## Vérification rapide

```bash
python -m gns3presence --check --verbose
python -m gns3presence --dry-run --once
```

Le premier donne l'état de tous les composants, le second affiche exactement
ce qui serait publié sur Discord.
