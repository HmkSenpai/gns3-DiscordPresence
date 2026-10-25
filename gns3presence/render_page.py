"""HTML page of the web interface (embedded in the executable)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .editor import CHOICES, TEXT_FIELDS, TOGGLES


def _toggle_html(item: Dict[str, Any]) -> str:
    return f"""
      <label class="switch">
        <input type="checkbox" data-key="{item['key']}" id="t_{item['key']}">
        <span class="slider"></span>
        <span class="switch-label">
          <strong>{item['label']}</strong>
          <em>{item['help']}</em>
        </span>
      </label>"""


def _choice_html(item: Dict[str, Any], extra_options: Optional[List[str]] = None) -> str:
    options = list(item["options"])
    for option in extra_options or []:
        if option not in options:
            options.append(option)
    rendered = "".join(f'<option value="{option}">{option}</option>' for option in options)
    return f"""
      <div class="field">
        <label for="c_{item['key']}">{item['label']}</label>
        <select data-key="{item['key']}" id="c_{item['key']}">{rendered}</select>
      </div>"""


def _text_html(item: Dict[str, Any]) -> str:
    placeholder = item.get("placeholder", "")
    return f"""
      <div class="field">
        <label for="x_{item['key']}">{item['label']}</label>
        <input type="text" data-key="{item['key']}" id="x_{item['key']}"
               placeholder="{placeholder}" spellcheck="false">
      </div>"""


def render_page(token: str) -> str:
    """Return the complete HTML page."""
    from .editor import available_assets

    assets = available_assets()
    toggles = "".join(_toggle_html(item) for item in TOGGLES)
    choices = "".join(
        _choice_html(item, assets if item["key"] == "presence.large_image" else None)
        for item in CHOICES
    )
    texts = "".join(_text_html(item) for item in TEXT_FIELDS)
    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>GNS3 Presence - Personnalisation</title>
<style>
  :root {{
    --bg: #16181d;
    --panel: #1f2229;
    --panel-2: #262a33;
    --border: #313742;
    --text: #e8eaed;
    --muted: #9aa3b2;
    --accent: #31a854;
    --accent-2: #4a90d9;
    --danger: #e5534b;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; padding: 0 0 60px;
    background: var(--bg); color: var(--text);
    font-family: "Segoe UI", system-ui, -apple-system, Roboto, sans-serif;
    font-size: 15px; line-height: 1.5;
  }}
  header {{
    padding: 22px 28px; border-bottom: 1px solid var(--border);
    display: flex; align-items: center; gap: 16px; flex-wrap: wrap;
    background: linear-gradient(180deg, #1b1e25, #16181d);
  }}
  header h1 {{ font-size: 19px; margin: 0; font-weight: 600; letter-spacing: .2px; }}
  header .badge {{
    font-size: 12px; padding: 3px 10px; border-radius: 999px;
    background: rgba(49,168,84,.15); color: var(--accent); border: 1px solid rgba(49,168,84,.35);
  }}
  header .spacer {{ flex: 1; }}
  .status-dot {{ width: 9px; height: 9px; border-radius: 50%; background: var(--muted); display: inline-block; }}
  .status-dot.on {{ background: var(--accent); box-shadow: 0 0 8px rgba(49,168,84,.7); }}
  .wrap {{ max-width: 1180px; margin: 0 auto; padding: 24px 28px; }}
  .grid {{ display: grid; grid-template-columns: 330px 1fr; gap: 24px; align-items: start; }}
  @media (max-width: 900px) {{ .grid {{ grid-template-columns: 1fr; }} }}
  .card {{
    background: var(--panel); border: 1px solid var(--border);
    border-radius: 12px; padding: 20px 22px; margin-bottom: 20px;
  }}
  .card h2 {{
    font-size: 13px; text-transform: uppercase; letter-spacing: .09em;
    color: var(--muted); margin: 0 0 16px; font-weight: 600;
  }}
  /* Apercu */
  .preview {{
    background: #313338; border-radius: 12px; padding: 16px;
    display: flex; gap: 14px; align-items: center; margin-bottom: 14px;
  }}
  .preview .art {{
    width: 74px; height: 74px; border-radius: 12px; flex: none;
    background: linear-gradient(140deg, var(--accent), #237a41);
    display: flex; align-items: center; justify-content: center;
    font-size: 30px; font-weight: 700; color: #fff;
  }}
  .preview .art.small {{ width: 26px; height: 26px; font-size: 12px; border-radius: 7px; align-self: flex-end; }}
  .preview .meta {{ min-width: 0; }}
  .preview .app {{ font-size: 12px; color: #b5bac1; font-weight: 600; letter-spacing: .02em; }}
  .preview .title {{ font-size: 15px; font-weight: 600; margin-top: 3px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
  .preview .desc {{ font-size: 13px; color: #b5bac1; margin-top: 2px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
  .preview .timer {{ font-size: 12px; color: #949ba4; margin-top: 5px; }}
  .lab-info {{ font-size: 13px; color: var(--muted); }}
  .lab-info b {{ color: var(--text); font-weight: 600; }}
  /* Switches */
  .switch {{ display: flex; gap: 12px; align-items: flex-start; padding: 11px 0; cursor: pointer; }}
  .switch + .switch {{ border-top: 1px solid var(--panel-2); }}
  .switch input {{ display: none; }}
  .slider {{
    flex: none; width: 38px; height: 22px; border-radius: 999px;
    background: #3a3f4b; position: relative; transition: background .16s; margin-top: 1px;
  }}
  .slider::after {{
    content: ""; position: absolute; top: 3px; left: 3px;
    width: 16px; height: 16px; border-radius: 50%; background: #fff;
    transition: transform .16s;
  }}
  .switch input:checked + .slider {{ background: var(--accent); }}
  .switch input:checked + .slider::after {{ transform: translateX(16px); }}
  .switch-label strong {{ display: block; font-weight: 500; font-size: 14px; }}
  .switch-label em {{ display: block; font-style: normal; font-size: 12px; color: var(--muted); margin-top: 1px; }}
  /* Fields */
  .field {{ margin-bottom: 14px; }}
  .field label {{ display: block; font-size: 13px; color: var(--muted); margin-bottom: 5px; }}
  .field input, .field select {{
    width: 100%; padding: 9px 11px; border-radius: 8px;
    border: 1px solid var(--border); background: var(--panel-2); color: var(--text);
    font-size: 14px; font-family: inherit;
  }}
  .field input:focus, .field select:focus {{ outline: none; border-color: var(--accent-2); }}
  .cols {{ display: grid; grid-template-columns: 1fr 1fr; gap: 0 18px; }}
  @media (max-width: 620px) {{ .cols {{ grid-template-columns: 1fr; }} }}
  /* Buttons */
  .actions {{ display: flex; gap: 10px; margin-top: 6px; flex-wrap: wrap; }}
  button {{
    font: inherit; font-size: 14px; font-weight: 500; cursor: pointer;
    padding: 9px 18px; border-radius: 8px; border: 1px solid transparent;
    background: var(--accent); color: #fff; transition: filter .15s;
  }}
  button:hover {{ filter: brightness(1.1); }}
  button.secondary {{ background: var(--panel-2); color: var(--text); border-color: var(--border); }}
  button.danger {{ background: transparent; color: var(--danger); border-color: rgba(229,83,75,.4); }}
  #toast {{
    position: fixed; bottom: 22px; left: 50%; transform: translateX(-50%) translateY(20px);
    background: var(--panel-2); border: 1px solid var(--border); color: var(--text);
    padding: 11px 20px; border-radius: 9px; font-size: 14px; opacity: 0;
    transition: opacity .2s, transform .2s; pointer-events: none; z-index: 10;
  }}
  #toast.show {{ opacity: 1; transform: translateX(-50%) translateY(0); }}
  #toast.ok {{ border-color: rgba(49,168,84,.5); }}
  #toast.err {{ border-color: rgba(229,83,75,.5); }}
  .hint {{ font-size: 12px; color: var(--muted); margin-top: 14px; line-height: 1.6; }}
  code {{ background: var(--panel-2); padding: 1px 6px; border-radius: 4px; font-size: 12px; }}
</style>
</head>
<body>
<header>
  <h1>GNS3 Presence</h1>
  <span class="badge">Personnalisation</span>
  <span class="spacer"></span>
  <span class="lab-info"><span class="status-dot" id="dot"></span> <span id="conn">connexion...</span></span>
</header>

<div class="wrap">
  <div class="grid">
    <div>
      <div class="card">
        <h2>Apercu en direct</h2>
        <div class="preview">
          <div class="art" id="pv-art">G</div>
          <div class="meta">
            <div class="app" id="pv-app">GNS3 Presence</div>
            <div class="title" id="pv-title">&mdash;</div>
            <div class="desc" id="pv-desc">&mdash;</div>
            <div class="timer" id="pv-timer"></div>
          </div>
        </div>
        <div class="lab-info" id="lab-info">Aucune donnee.</div>
      </div>

      <div class="card">
        <h2>Ce qui est affiche</h2>
        {toggles}
      </div>
    </div>

    <div>
      <div class="card">
        <h2>Style</h2>
        <div class="cols">
          {choices}
        </div>
        <div class="field" style="margin-top:6px">
          <label for="x_presence.small_image">Icone de l'equipement (cle d'asset)</label>
          <input type="text" data-key="presence.small_image" id="x_presence.small_image"
                 spellcheck="false" placeholder="{{dominant_type}} ou router / switch / pc">
          <em style="font-size:12px;color:var(--muted);font-style:normal">
            La cle est le nom du fichier uploade dans Rich Presence &gt; Art Assets,
            sans l'extension. {{dominant_type}} suit l'equipement dominant du lab.
          </em>
        </div>
      </div>

      <div class="card">
        <h2>Textes</h2>
        <div class="cols">
          {texts}
        </div>
        <div class="hint">
          Variables disponibles : <code>{{project}}</code> <code>{{running}}</code>
          <code>{{total}}</code> <code>{{links}}</code> <code>{{summary}}</code>
          <code>{{elapsed}}</code> <code>{{dominant_type}}</code>
          <code>{{version}}</code>
        </div>
      </div>

      <div class="card">
        <h2>Confidentialite</h2>
        <label class="switch">
          <input type="checkbox" data-key="privacy.enabled" id="t_privacy.enabled">
          <span class="slider"></span>
          <span class="switch-label">
            <strong>Mode discret</strong>
            <em>Masque le nom du lab (utile pour les examens).</em>
          </span>
        </label>
        <div class="field" style="margin-top:12px">
          <label for="x_privacy.replacement">Texte affiche a la place</label>
          <input type="text" data-key="privacy.replacement" id="x_privacy.replacement" spellcheck="false">
        </div>
      </div>

      <div class="card">
        <h2>Actions</h2>
        <div class="actions">
          <button id="save">Enregistrer et appliquer</button>
          <button class="secondary" id="reload">Recharger depuis le fichier</button>
          <button class="danger" id="reset">Revenir aux reglages par defaut</button>
        </div>
        <div class="hint" id="cfgpath"></div>
      </div>
    </div>
  </div>
</div>

<div id="toast"></div>

<script>
const TOKEN = new URLSearchParams(location.search).get("token") || "";
const $ = (id) => document.getElementById(id);

let settings = {{}};

function toast(message, ok = true) {{
  const el = $("toast");
  el.textContent = message;
  el.className = "show " + (ok ? "ok" : "err");
  clearTimeout(el._t);
  el._t = setTimeout(() => {{ el.className = ""; }}, 2600);
}}

function collect() {{
  const out = {{}};
  document.querySelectorAll("input[data-key], select[data-key]").forEach((el) => {{
    out[el.dataset.key] = el.type === "checkbox" ? el.checked : el.value;
  }});
  return out;
}}

function apply(values) {{
  settings = Object.assign({{}}, values);
  document.querySelectorAll("input[data-key], select[data-key]").forEach((el) => {{
    const v = settings[el.dataset.key];
    if (v === undefined) return;
    if (el.type === "checkbox") el.checked = !!v;
    else el.value = v;
  }});
}}

function renderPreview(pv, lab) {{
  if (!pv) return;
  $("pv-title").textContent = pv.details || "(aucun detail)";
  $("pv-desc").textContent = pv.state || "(aucun etat)";
  const art = $("pv-art");
  art.textContent = (pv.large_image || "g").charAt(0).toUpperCase();
  art.title = pv.large_image || "";
  const timer = $("pv-timer");
  if (pv.start) {{
    const minutes = Math.floor((Date.now() / 1000 - pv.start) / 60);
    timer.textContent = "il y a " + minutes + " min";
  }} else {{
    timer.textContent = "";
  }}
  if (lab) {{
    $("lab-info").innerHTML =
      "Lab : <b>" + (lab.project || "-") + "</b><br>" +
      "Etat : <b>" + lab.state + "</b> (" + lab.source + ")<br>" +
      "Noeuds : <b>" + lab.running + "/" + lab.total + "</b> &middot; Liens : <b>" + lab.links + "</b>";
  }}
}}

async function loadState() {{
  const res = await fetch("/api/state?token=" + encodeURIComponent(TOKEN));
  if (!res.ok) {{ toast("Acces refuse", false); return; }}
  const data = await res.json();
  apply(data.settings);
  renderPreview(data.preview, data.lab);
  $("cfgpath").textContent = "Fichier : " + data.config_path;
  $("dot").classList.add("on");
  $("conn").textContent = "connecte";
}}

async function preview() {{
  const res = await fetch("/api/preview?token=" + encodeURIComponent(TOKEN), {{
    method: "POST",
    headers: {{ "Content-Type": "application/json", "X-Preset-Token": TOKEN }},
    body: JSON.stringify({{ settings: collect() }})
  }});
  if (!res.ok) {{ toast("Apercu impossible", false); return; }}
  const data = await res.json();
  renderPreview(data.preview, null);
}}

$("save").addEventListener("click", async () => {{
  const res = await fetch("/api/save?token=" + encodeURIComponent(TOKEN), {{
    method: "POST",
    headers: {{ "Content-Type": "application/json", "X-Preset-Token": TOKEN }},
    body: JSON.stringify({{ settings: collect() }})
  }});
  const data = await res.json();
  if (data.ok) {{
    toast("Configuration enregistree : " + data.message);
    renderPreview(data.preview, null);
  }} else {{
    toast("Echec : " + data.message, false);
  }}
}});

$("reload").addEventListener("click", () => {{ loadState(); toast("Recharge"); }});

$("reset").addEventListener("click", async () => {{
  if (!confirm("Revenir aux reglages par defaut ? Le fichier de configuration sera modifie.")) return;
  const res = await fetch("/api/save?token=" + encodeURIComponent(TOKEN), {{
    method: "POST",
    headers: {{ "Content-Type": "application/json", "X-Preset-Token": TOKEN }},
    body: JSON.stringify({{ settings: {{}}, reset: true }})
  }});
  const data = await res.json();
  if (data.ok) {{ toast("Reglages par defaut appliques"); loadState(); }}
  else toast("Echec : " + data.message, false);
}});

let timer = null;
document.querySelectorAll("input[data-key], select[data-key]").forEach((el) => {{
  el.addEventListener("change", () => {{
    preview();
    clearTimeout(timer);
    timer = setTimeout(save, 900);
  }});
}});

loadState();
setInterval(loadState, 4000);
</script>
</body>
</html>
"""
