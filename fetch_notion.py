"""
fetch_notion.py
Busca todos os registros do banco Notion (com paginação)
e salva data.json na raiz do repositório.
Executado pelo GitHub Actions a cada 5 minutos.
"""

import json
import os
import urllib.request
import urllib.error
from datetime import datetime, timezone

TOKEN       = os.environ.get("NOTION_TOKEN", "")
DATABASE_ID = os.environ.get("NOTION_DATABASE_ID", "")
OUTPUT      = "data.json"

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}
URL = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"

def get_prop(page, name):
    p = page.get("properties", {}).get(name)
    if p is None:
        return None
    t = p.get("type")
    if t == "title":
        return "".join(x["plain_text"] for x in p.get("title", []))
    if t == "rich_text":
        return "".join(x["plain_text"] for x in p.get("rich_text", []))
    if t == "number":
        return p.get("number")
    if t == "select":
        sel = p.get("select")
        return sel.get("name") if sel else None
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
        if arr:
            return arr[0].get("number") or arr[0].get("string")
        return None
    return None

def fetch_all():
    results, cursor = [], None
    while True:
        body = {}
        if cursor:
            body["start_cursor"] = cursor
        req = urllib.request.Request(
            URL, data=json.dumps(body).encode(), headers=HEADERS, method="POST")
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

def normalize(page):
    return {
        "id":       page["id"],
        "endereco": get_prop(page, "ENDEREÇO") or "",
        "casa":     get_prop(page, "CASA") or "",
        "ref":      get_prop(page, "REF") or "",
        "setor":    get_prop(page, "SETOR") or "",
        "tipo":     get_prop(page, "TIPO"),
        "modelo":   get_prop(page, "MODELO?") or "",
        "cliente":  get_prop(page, "CLIENTES ") or "",
        "avaliacao":get_prop(page, "AVALIAÇÃO"),
        "valorMao": get_prop(page, " VALOR NA MÃO "),
        "entregou": get_prop(page, "ENTEGOU A CASA E PEGOU TERMO DE ENTREGA?") or "",
        "fotos":    get_prop(page, "FOTOS") or "",
        "layout":   get_prop(page, "LAYOUT") or "",
    }

if __name__ == "__main__":
    if not TOKEN or not DATABASE_ID:
        raise SystemExit("ERROR: NOTION_TOKEN e NOTION_DATABASE_ID devem estar definidos.")

    print("Buscando dados do Notion...")
    pages = fetch_all()
    print(f"  {len(pages)} páginas encontradas.")

    rows = [normalize(p) for p in pages]

    output = {
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "rows": rows
    }

    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"  Salvo em {OUTPUT} ({len(rows)} registros).")
    print(f"  Timestamp: {output['updated_at']}")
