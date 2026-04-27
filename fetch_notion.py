"""
fetch_notion.py
Busca todos os registros do banco Notion (com paginação)
e salva data.json na raiz do repositório.
Executado pelo GitHub Actions a cada 15 minutos.
"""

import json
import os
import urllib.request
import urllib.error

# ── CONFIG ────────────────────────────────────────────────────────────────────
TOKEN       = os.environ.get("NOTION_TOKEN", "")
DATABASE_ID = os.environ.get("NOTION_DATABASE_ID", "")
OUTPUT      = "data.json"

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}

URL = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"

# ── HELPERS ───────────────────────────────────────────────────────────────────
def get_prop(page, *names):
    """Tenta vários nomes de propriedade (case variations)."""
    props = page.get("properties", {})
    for name in names:
        p = props.get(name)
        if p is None:
            continue
        t = p.get("type")
        if t == "title":
            return "".join(x["plain_text"] for x in p.get("title", []))
        if t == "rich_text":
            return "".join(x["plain_text"] for x in p.get("rich_text", []))
        if t == "number":
            return p.get("number")
        if t == "select":
            return p.get("select", {}).get("name")
        if t == "multi_select":
            return ", ".join(s["name"] for s in p.get("multi_select", []))
        if t == "date":
            return (p.get("date") or {}).get("start")
        if t == "checkbox":
            return p.get("checkbox")
        if t == "url":
            return p.get("url")
        if t == "formula":
            f = p.get("formula", {})
            return f.get("string") or f.get("number")
        if t == "rollup":
            arr = (p.get("rollup") or {}).get("array", [])
            return arr[0].get("number") if arr else None
    return None

# ── FETCH ALL PAGES ───────────────────────────────────────────────────────────
def fetch_all():
    results = []
    cursor  = None

    while True:
        body = {}
        if cursor:
            body["start_cursor"] = cursor

        req = urllib.request.Request(
            URL,
            data=json.dumps(body).encode(),
            headers=HEADERS,
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"Notion API error {e.code}: {e.read().decode()}")

        results.extend(data.get("results", []))
        if data.get("has_more"):
            cursor = data["next_cursor"]
        else:
            break

    return results

# ── NORMALIZE ─────────────────────────────────────────────────────────────────
def normalize(page):
    return {
        "id":       page["id"],
        "endereco": get_prop(page, "ENDEREÇO", "Endereço", "ENDEREDEÇO") or "",
        "casa":     get_prop(page, "CASA", "Casa") or "",
        "ref":      get_prop(page, "REF", "Ref", "REF.") or "",
        "setor":    get_prop(page, "SETOR", "Setor") or "",
        "tipo":     get_prop(page, "TIPO", "Tipo"),
        "modelo":   get_prop(page, "MODELO?", "Modelo?", "MODELO") or "",
        "cliente":  get_prop(page, "CLIENTES", "Clientes", "CLIENTE") or "",
        "avaliacao":get_prop(page, "AVALIAÇÃO", "Avaliação", "AVALIACAO"),
        "valorMao": get_prop(page, "VALOR NA MÃO", "Valor na Mão", "VALOR NA MAO"),
        "entregou": get_prop(page, "ENTEGOU A CASA E PEGOU TERMO DE ENTREGA?",
                                   "Entregou a Casa?", "ENTREGOU") or "",
        "fotos":    get_prop(page, "FOTOS", "Fotos") or "",
        "layout":   get_prop(page, "LAYOUT", "Layout") or "",
    }

# ── MAIN ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if not TOKEN or not DATABASE_ID:
        raise SystemExit("ERROR: NOTION_TOKEN e NOTION_DATABASE_ID devem estar definidos.")

    print(f"Buscando banco {DATABASE_ID}…")
    pages = fetch_all()
    print(f"  {len(pages)} páginas encontradas.")

    rows = [normalize(p) for p in pages]

    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)

    print(f"  Salvo em {OUTPUT} ({len(rows)} registros).")
