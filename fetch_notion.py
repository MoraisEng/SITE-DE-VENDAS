"""
fetch_notion.py - DEBUG VERSION
Imprime raw de todas as propriedades das primeiras páginas RAVENA
para identificar nomes e tipos corretos.
"""

import json
import os
import urllib.request
import urllib.error

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
            item = arr[0]
            return item.get("number") or item.get("string") or str(item)
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
        raise SystemExit("ERROR: variáveis não definidas.")

    print(f"Buscando banco...")
    pages = fetch_all()
    print(f"{len(pages)} páginas encontradas.")

    # Encontrar primeiras 3 páginas do RAVENA com cliente preenchido
    ravena_com_cliente = []
    for p in pages:
        props = p.get("properties", {})
        setor_prop = props.get("SETOR", {})
        setor_val = ""
        if setor_prop.get("type") == "select":
            sel = setor_prop.get("select")
            setor_val = sel.get("name", "") if sel else ""
        
        if setor_val.strip().upper() != "RAVENA":
            continue
            
        # Checar se tem cliente em QUALQUER campo rich_text
        for nome, prop in props.items():
            if prop.get("type") == "rich_text":
                val = "".join(x["plain_text"] for x in prop.get("rich_text", []))
                if val.strip():
                    ravena_com_cliente.append((p, nome, val))
                    break
        
        if len(ravena_com_cliente) >= 3:
            break

    print("\n=== DEBUG: RAVENA com rich_text preenchido ===")
    for page, campo, valor in ravena_com_cliente:
        end = get_prop(page, "ENDEREÇO") or "?"
        print(f"\nEndereço: {end}")
        print(f"  Campo rich_text com valor: '{campo}' = '{valor}'")
        # Mostrar também VALOR NA MÃO raw
        props = page.get("properties", {})
        for nome, prop in props.items():
            if "VALOR" in nome.upper() and "MÃO" in nome.upper():
                print(f"  Campo valor: repr='{repr(nome)}' tipo={prop.get('type')} val={prop.get('number')}")
            if "CLIENTE" in nome.upper():
                print(f"  Campo cliente: repr='{repr(nome)}' tipo={prop.get('type')} raw={prop.get('rich_text','')[:1]}")
    print("==============================================\n")

    rows = [normalize(p) for p in pages]
    
    # Estatísticas
    ravena = [r for r in rows if r.get("setor","").strip().upper() == "RAVENA"]
    com_cliente = [r for r in ravena if r.get("cliente","").strip()]
    com_valor = [r for r in ravena if r.get("valorMao") is not None]
    print(f"RAVENA total: {len(ravena)}")
    print(f"RAVENA com cliente: {len(com_cliente)}")
    print(f"RAVENA com valorMao: {len(com_valor)}")

    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)
    print(f"Salvo: {len(rows)} registros.")
