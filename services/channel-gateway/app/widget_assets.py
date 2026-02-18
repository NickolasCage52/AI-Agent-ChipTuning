from __future__ import annotations


def widget_js(base_url: str) -> str:
    # Inject floating button + iframe panel (very small MVP)
    return f"""(() => {{
  const BASE = {base_url!r};
  const BTN_ID = 'autoshop-widget-btn';
  const PANEL_ID = 'autoshop-widget-panel';
  if (document.getElementById(BTN_ID)) return;

  const btn = document.createElement('button');
  btn.id = BTN_ID;
  btn.innerText = 'Задать вопрос';
  btn.style.cssText = 'position:fixed;right:16px;bottom:16px;z-index:99999;background:#e11d2e;color:#fff;border:none;border-radius:14px;padding:12px 14px;font-weight:700;box-shadow:0 10px 24px rgba(0,0,0,0.25);cursor:pointer;';

  const panel = document.createElement('div');
  panel.id = PANEL_ID;
  panel.style.cssText = 'position:fixed;right:16px;bottom:72px;width:360px;max-width:calc(100vw - 32px);height:520px;max-height:calc(100vh - 120px);z-index:99999;border-radius:16px;overflow:hidden;display:none;box-shadow:0 12px 28px rgba(0,0,0,0.35);border:1px solid rgba(255,255,255,0.08);background:#12141a;';

  const iframe = document.createElement('iframe');
  iframe.src = BASE + '/widget';
  iframe.style.cssText = 'width:100%;height:100%;border:0;';
  panel.appendChild(iframe);

  btn.addEventListener('click', () => {{
    panel.style.display = panel.style.display === 'none' ? 'block' : 'none';
  }});

  document.body.appendChild(btn);
  document.body.appendChild(panel);
}})();"""


def widget_html(base_url: str) -> str:
    return f"""<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Widget</title>
  <style>
    :root {{ --bg:#0b0c0f; --fg:#f6f7fb; --muted:#a9b0bf; --card:#12141a; --border:rgba(255,255,255,0.08); --primary:#e11d2e; }}
    body {{ margin:0; background:var(--card); color:var(--fg); font-family:system-ui, -apple-system, Segoe UI, Roboto, Arial; }}
    .wrap {{ display:flex; flex-direction:column; height:100vh; }}
    .head {{ padding:10px 12px; border-bottom:1px solid var(--border); font-weight:700; display:flex; justify-content:space-between; gap:8px; }}
    .muted {{ color:var(--muted); font-weight:500; font-size:12px; }}
    .msgs {{ flex:1; overflow:auto; padding:12px; display:flex; flex-direction:column; gap:8px; }}
    .m {{ max-width:90%; padding:10px 12px; border-radius:14px; border:1px solid var(--border); white-space:pre-wrap; font-size:13px; }}
    .u {{ align-self:flex-end; background:rgba(225,29,46,0.15); }}
    .a {{ align-self:flex-start; background:rgba(255,255,255,0.04); }}
    .bar {{ border-top:1px solid var(--border); padding:10px; display:flex; gap:8px; }}
    input {{ flex:1; border-radius:12px; border:1px solid var(--border); background:rgba(255,255,255,0.02); color:var(--fg); padding:10px 12px; outline:none; }}
    button {{ border-radius:12px; border:none; background:var(--primary); color:#fff; font-weight:700; padding:10px 12px; cursor:pointer; }}
    .quick {{ padding:10px 12px; display:flex; gap:8px; flex-wrap:wrap; border-top:1px solid var(--border); }}
    .qbtn {{ background:transparent; border:1px solid var(--border); color:var(--muted); font-weight:700; padding:6px 10px; border-radius:999px; cursor:pointer; }}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="head">
      <div>Чат-виджет</div>
      <div class="muted" id="sid">session: —</div>
    </div>
    <div class="msgs" id="msgs"></div>
    <div class="quick">
      <button class="qbtn" data-q="Нужно ТО на Kia Rio 2017, пробег 120к">ТО</button>
      <button class="qbtn" data-q="Нужны колодки на Camry 50">Запчасти</button>
      <button class="qbtn" data-q="Стук справа при повороте">Проблема</button>
    </div>
    <div class="bar">
      <input id="txt" placeholder="Напишите сообщение..." />
      <button id="send">Отправить</button>
    </div>
  </div>
  <script>
    const BASE = {base_url!r};
    const msgs = document.getElementById('msgs');
    const txt = document.getElementById('txt');
    const sidEl = document.getElementById('sid');
    let sessionId = localStorage.getItem('autoshop_session_id');

    function add(role, text) {{
      const div = document.createElement('div');
      div.className = 'm ' + (role === 'user' ? 'u' : 'a');
      div.textContent = text;
      msgs.appendChild(div);
      msgs.scrollTop = msgs.scrollHeight;
    }}

    async function ensureSession() {{
      if (sessionId) return sessionId;
      const r = await fetch(BASE + '/api/widget/session', {{ method:'POST' }});
      const d = await r.json();
      sessionId = d.session_id;
      localStorage.setItem('autoshop_session_id', sessionId);
      sidEl.textContent = 'session: ' + sessionId.slice(0,8) + '…';
      return sessionId;
    }}

    async function send(message) {{
      const sid = await ensureSession();
      add('user', message);
      const r = await fetch(BASE + '/api/widget/message', {{
        method:'POST',
        headers:{{'Content-Type':'application/json'}},
        body: JSON.stringify({{ session_id: sid, message }})
      }});
      const d = await r.json();
      add('assistant', d.answer || '—');
    }}

    document.getElementById('send').onclick = () => {{
      const m = txt.value.trim();
      if (!m) return;
      txt.value = '';
      send(m);
    }};
    document.querySelectorAll('[data-q]').forEach(b => b.onclick = () => send(b.getAttribute('data-q')));

    if (sessionId) {{
      sidEl.textContent = 'session: ' + sessionId.slice(0,8) + '…';
      add('assistant', 'Привет! Чем помочь: ТО / Запчасти / Проблема?');
    }} else {{
      add('assistant', 'Привет! Нажмите быстрые кнопки или напишите вопрос.');
    }}
  </script>
</body>
</html>"""

