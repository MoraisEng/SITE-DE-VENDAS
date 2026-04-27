# Mapa de Vendas — RAVENA
**Morais Engenharia e Construção**

Página web interativa do mapa de vendas do setor Ravena, com atualização automática via Notion API.

---

## Estrutura do repositório

```
mapa-vendas-ravena/
├── index.html              ← página principal (auto-suficiente)
├── fetch_notion.py         ← script que busca o Notion e gera data.json
├── data.json               ← gerado automaticamente a cada 15 min
└── .github/
    └── workflows/
        ├── fetch_notion.yml ← roda fetch_notion.py a cada 15 minutos
        └── deploy.yml       ← publica no GitHub Pages a cada push
```

---

## Setup (uma vez só)

### 1. Criar o repositório
- Criar repositório **público** no GitHub (ex: `mapa-vendas-ravena`)
- Subir todos os arquivos desta pasta

### 2. Configurar os Secrets do GitHub
Ir em **Settings → Secrets and variables → Actions → New repository secret** e criar:

| Secret | Valor |
|---|---|
| `NOTION_TOKEN` | `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` |
| `NOTION_DATABASE_ID` | `33cc5ab532d38047ae3aee8b87ac1f4d` |

### 3. Ativar GitHub Pages
- Ir em **Settings → Pages**
- Source: **GitHub Actions**
- Salvar

### 4. Rodar o primeiro fetch manualmente
- Ir em **Actions → Atualizar dados do Notion → Run workflow**
- Isso vai gerar o `data.json` pela primeira vez

### 5. Acessar a página
Após o deploy (≈ 2 min), a página estará em:
```
https://SEU-USUARIO.github.io/mapa-vendas-ravena/
```

---

## Atualização automática
- O `data.json` é atualizado **a cada 15 minutos** automaticamente
- A página recarrega os dados **a cada 5 minutos** sem refresh manual
- Qualquer mudança no Notion aparece na página em no máximo ~20 minutos

---

## Manutenção
- **Adicionar novo lote ao SVG**: editar `index.html`, adicionar `<polygon id="RRxx" .../>` com as coordenadas
- **Mudar tempo de atualização**: editar `cron` no `fetch_notion.yml`
- **Adicionar novo setor**: duplicar a estrutura, trocar `RAVENA` pelo nome do setor
