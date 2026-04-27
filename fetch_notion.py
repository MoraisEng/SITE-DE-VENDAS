"""
fetch_notion.py
Busca registros dos dois bancos Notion (vendas + disponibilidades)
e salva data.json na raiz do repositório.
Executado pelo GitHub Actions automaticamente.
"""
import json
import os
import urllib.request
import urllib.error
from datetime import datetime, timezone

TOKEN_VENDAS  = os.environ.get("NOTION_TOKEN", "")
TOKEN_DISP    = os.environ.get("NOTION_TOKEN_DISP", "") or TOKEN_VENDAS
DB_VENDAS     = os.environ.get("NOTION_DATABASE_ID", "")
DB_DISP       = os.environ.get("NOTION_DATABASE_ID_DISP", "33dc5ab532d38091b927d7659f98612c")
OUTPUT        = "data.json"

def make_headers(token):
    return {
        "Authorization": "Bearer " + token,
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }

def fetch_all(db_id, token):
    url = "https://api.notion.com/v1/databases/" + db_id + "/query"
    headers = make_headers(token)
    results, cursor = [], None
    while True:
        body = {}
        if cursor:
            body["start_cursor"] = cursor
        req = urllib.request.Request(
            url, data=json.dumps(body).encode(), headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            raise RuntimeError("Notion API error " + str(e.code) + ": " + e.read().decode())
        results.extend(data.get("results", []))
        if data.get("has_more"):
            cursor = data["next_cursor"]
        else:
            break
    return results

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

def normalize_venda(page):
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

def normalize_disp(page):
    # Tenta variações de nome de propriedade
    def gp(*names):
        for n in names:
            v = get_prop(page, n)
            if v is not None:
                return v
        return ""

    return {
        "id":     page["id"],
        "setor":  gp("SETOR", "Setor", "setor"),
        "setorPBI": gp("SETOR PBI", "Setor PBI", "SETOR"),
        "cidade": gp("CIDADE", "Cidade", "cidade"),
        "link":   gp("LINK", "Link", "link"),
        "obs":    gp("OBSERVAÇÕES", "Observações", "OBSERVACOES", "observacoes"),
    }

if __name__ == "__main__":
    if not TOKEN_VENDAS or not DB_VENDAS:
        raise SystemExit("ERROR: NOTION_TOKEN e NOTION_DATABASE_ID devem estar definidos.")

    # 1. Banco de vendas
    print("Buscando banco de vendas...")
    pages_vendas = fetch_all(DB_VENDAS, TOKEN_VENDAS)
    print(f"  {len(pages_vendas)} registros encontrados.")
    rows_vendas = [normalize_venda(p) for p in pages_vendas]

    # 2. Banco de disponibilidades
    print("Buscando banco de disponibilidades...")
    try:
        pages_disp = fetch_all(DB_DISP, TOKEN_DISP)
        print(f"  {len(pages_disp)} registros encontrados.")
        rows_disp = [normalize_disp(p) for p in pages_disp]
    except Exception as e:
        print(f"  AVISO: falha ao buscar disponibilidades: {e}")
        rows_disp = []

    # 3. Calcula contagem de disponíveis por setor
    # Regra: valorMao preenchido E cliente vazio
    contagem = {}
    for r in rows_vendas:
        setor = r.get("setor", "")
        if not setor:
            continue
        tem_valor  = bool(r.get("valorMao"))
        sem_cliente = not bool(r.get("cliente", "").strip())
        if tem_valor and sem_cliente:
            contagem[setor] = contagem.get(setor, 0) + 1

    # 4. Enriquece disponibilidades com contagem
    for d in rows_disp:
        setor_pbi = d.get("setorPBI") or d.get("setor", "")
        setor     = d.get("setor", "")
        d["qtd"]  = contagem.get(setor_pbi, contagem.get(setor, 0))

    # 5. Salva JSON
    output = {
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "rows": rows_vendas,
        "disponibilidades": rows_disp,
    }
    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"  Salvo em {OUTPUT}.")
    print(f"  Vendas: {len(rows_vendas)} | Disponibilidades: {len(rows_disp)}")
    print(f"  Timestamp: {output['updated_at']}")
