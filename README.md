# Automação de Sugestões de Conteúdo

Gera sugestões de conteúdo semanais (stories, reels, posts estáticos) e publica-as
num canal Slack para revisão, com rotação automática pelos 5 pilares de conteúdo.

## Passo 1 — Criar o webhook no Slack

1. Vai a https://api.slack.com/apps e clica em **Create New App** → **From scratch**
2. Dá um nome (ex: "Conteúdo Seguros") e escolhe o teu workspace
3. No menu lateral, vai a **Incoming Webhooks** e ativa (**Activate Incoming Webhooks**)
4. Clica em **Add New Webhook to Workspace**, escolhe o canal (ex: `#conteudo-ageas`) e autoriza
5. Copia o URL do webhook gerado (algo como `https://hooks.slack.com/services/...`)

## Passo 2 — Obter a chave da API do Gemini

1. Vai a https://aistudio.google.com/apikey (a mesma conta Google que usas no AI Studio)
2. Clica em **Create API key** → escolhe ou cria um projeto Google Cloud
3. Copia a chave gerada — é a mesma família de créditos que já usas no AI Studio para o Nano Banana

## Passo 3 — Criar o repositório no GitHub

1. Cria um novo repositório (privado, já que tem a tua chave de API associada indiretamente)
2. Faz upload/push desta pasta (`.github/workflows/content-ideas.yml`, `scripts/generate_content_ideas.py`)

## Passo 4 — Configurar os secrets no GitHub

No repositório: **Settings → Secrets and variables → Actions → New repository secret**

Adiciona dois secrets:
- `GEMINI_API_KEY` — a chave copiada no Passo 2
- `SLACK_WEBHOOK_URL` — o URL copiado no Passo 1

## Passo 5 — Testar manualmente

No repositório: separador **Actions** → seleciona o workflow **"Sugestões de Conteúdo Semanal"**
→ botão **Run workflow** (isto usa o `workflow_dispatch`, não precisas de esperar pela segunda-feira)

Se tudo estiver bem configurado, a mensagem aparece no canal Slack escolhido em segundos.

## Como funciona a rotação de pilares

O script escolhe o pilar da semana com base no número da semana do ano (semana ISO),
por isso a rotação é automática e não repete o mesmo pilar em semanas consecutivas
(a menos que o número de semanas não seja múltiplo de 5, o que é normal e sem problema).

Os 5 pilares estão definidos no topo do ficheiro `scripts/generate_content_ideas.py`
na lista `PILLARS` — podes editar o texto de cada um livremente para ajustar o tom,
os produtos em foco, ou adicionar/remover pilares.

## Ajustar a frequência

Atualmente corre 1x por semana (segunda-feira). Se quiseres, por exemplo, uma sugestão
por pilar mais vezes por semana, basta duplicar a linha `cron` no workflow com outro
dia/hora, ou mudar para `'0 8 * * 1,4'` (segunda e quinta).
