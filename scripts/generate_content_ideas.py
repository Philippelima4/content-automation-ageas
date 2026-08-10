"""
Gera sugestões de conteúdo semanais (stories, reels, posts estáticos)
para a estratégia de marketing de seguros (profissionais liberais + PMEs),
e publica-as num canal Slack para revisão/aprovação.

Variáveis de ambiente necessárias (definidas como GitHub Secrets):
- GEMINI_API_KEY  (gerada em aistudio.google.com/apikey)
- SLACK_WEBHOOK_URL
"""

import os
import sys
from datetime import date

import requests

GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
SLACK_WEBHOOK_URL = os.environ["SLACK_WEBHOOK_URL"]
GEMINI_MODEL = "gemini-3.6-flash"
GEMINI_ENDPOINT = (
    f"https://generativelanguage.googleapis.com/v1beta/models/"
    f"{GEMINI_MODEL}:generateContent"
)

# Linha visual da marca (usada nos prompts de imagem para o Nano Banana / AI Studio)
BRAND_STYLE = (
    "Minimalist modern insurance social media graphic, square 1:1 format, "
    "off-white background (#F5F5F0), deep petrol blue (#1B3A3A) as primary "
    "color, single lime green accent (#C1FF72) used sparingly, generous "
    "negative space, bold modern geometric sans-serif headline space at top, "
    "no stock photography, no clutter, professional and trustworthy tone"
)

# Produtos reais por público (das monofolhas oficiais Ageas / Ordem dos Médicos
# e Ordem dos Médicos Dentistas). Ajusta aqui se os produtos mudarem.
AUDIENCES = {
    "medicos": {
        "label": "Médicos",
        "products": [
            {
                "name": "Vida Profissionais",
                "details": (
                    "Subsídio diário (0,1% do capital base/dia) e exoneração de "
                    "prémios em Incapacidade Total Temporária; % do capital + "
                    "renda anual em Invalidez Permanente; % do capital + renda "
                    "vitalícia à família em caso de Morte."
                ),
            },
            {
                "name": "Responsabilidade Civil Profissional",
                "details": (
                    "Indemnizações a terceiros por erro médico, prescrição ou "
                    "diagnóstico inadequado; defesa judicial, cauções ao "
                    "tribunal, honorários de advogados."
                ),
            },
            {
                "name": "Saúde Exclusive",
                "details": (
                    "Doenças Graves até 1.000.000€; reembolso até 80% de "
                    "medicamentos; estomatologia/próteses na cobertura base; "
                    "Rede Médis; Médico Online 24h."
                ),
            },
            {
                "name": "Commercialis",
                "details": (
                    "Multirriscos para a clínica/consultório: proteção de "
                    "clientes e colaboradores, acidentes pessoais, roubo, "
                    "avaria de máquinas."
                ),
            },
        ],
    },
    "dentistas": {
        "label": "Médicos Dentistas",
        "products": [
            {
                "name": "Ritmo Vida Profissional",
                "details": (
                    "3 níveis — Base (proteção simples, flexível para crédito), "
                    "Mais (duplicação de capitais por acidente), Top (reforço "
                    "de garantias e subsídio diário)."
                ),
            },
            {
                "name": "Responsabilidade Civil Profissional",
                "details": (
                    "Indemnizações a pacientes por erro médico, prescrição ou "
                    "diagnóstico inadequado; defesa judicial, cauções, "
                    "honorários de advogados."
                ),
            },
            {
                "name": "Saúde Exclusive",
                "details": (
                    "Doenças Graves até 1.000.000€ (opções 2, 3 e 4); Médico "
                    "Online 24h; até 15% de desconto por agregado familiar; "
                    "filhos incluídos desde o nascimento; entrega de "
                    "medicamentos em casa."
                ),
            },
            {
                "name": "Acidentes Pessoais Ordens Profissionais",
                "details": (
                    "Capital entre 100.000€ e 500.000€ em Morte ou Invalidez "
                    "Permanente; proteção 24h/dia, 365 dias/ano, vida "
                    "profissional e pessoal; assistência em viagem."
                ),
            },
            {
                "name": "MR Estabelecimentos de Saúde (Commercialis)",
                "details": (
                    "Multirriscos para a clínica dentária: proteção de "
                    "clientes e colaboradores, roubo, avaria de máquinas."
                ),
            },
        ],
    },
    "pme": {
        "label": "PMEs",
        "products": [
            {
                "name": "Acidentes de Trabalho (Conta de Outrém)",
                "details": (
                    "Seguro obrigatório por lei para qualquer empresa com "
                    "colaboradores — cobre acidentes ocorridos no exercício "
                    "da função. NOTA: confirmar coberturas exatas com a folha "
                    "de produto antes de publicar valores específicos."
                ),
            },
            {
                "name": "Responsabilidade Civil Empresas",
                "details": (
                    "Proteção da empresa por danos causados a terceiros no "
                    "exercício da atividade. NOTA: confirmar coberturas "
                    "exatas com a folha de produto antes de publicar valores "
                    "específicos."
                ),
            },
            {
                "name": "Saúde PME",
                "details": (
                    "Seguro de saúde para colaboradores como benefício de "
                    "retenção de talento. NOTA: confirmar coberturas exatas "
                    "com a folha de produto antes de publicar valores "
                    "específicos."
                ),
            },
            {
                "name": "Vida Grupo Não Contributivo / Empresa Viva",
                "details": (
                    "Proteção de vida em grupo para colaboradores ou "
                    "proteção de sócio-gerente (key person). NOTA: confirmar "
                    "coberturas exatas com a folha de produto antes de "
                    "publicar valores específicos."
                ),
            },
        ],
    },
}

# SPRINT 1 (3 semanas): testa os 3 públicos com o produto mais urgente de cada
# antes de decidires o Sprint 2 com base nos resultados reais (reuniões geradas
# por público). Depois de reveres os números ao fim das 3 semanas, edita esta
# lista para o Sprint 2 — mantém o padrão {pillar, audience, product}.
WEEKLY_ROTATION = [
    {"pillar": "Apresentação de produto", "audience": "medicos", "product": "Vida Profissionais"},
    {"pillar": "PME e empresarial", "audience": "pme", "product": "Acidentes de Trabalho (Conta de Outrém)"},
    {"pillar": "Apresentação de produto", "audience": "dentistas", "product": "Ritmo Vida Profissional"},
]


def get_week_theme() -> dict:
    """Escolhe o tema da semana com base no número da semana ISO."""
    week_number = date.today().isocalendar().week
    index = week_number % len(WEEKLY_ROTATION)
    theme = dict(WEEKLY_ROTATION[index])

    if theme["audience"]:
        audience_data = AUDIENCES[theme["audience"]]
        theme["audience_label"] = audience_data["label"]
        if theme["product"]:
            product = next(
                p for p in audience_data["products"] if p["name"] == theme["product"]
            )
            theme["product_details"] = product["details"]
    return theme


def generate_content_ideas(theme: dict) -> str:
    """Chama a API do Gemini para gerar as sugestões de conteúdo da semana."""
    context_lines = [f'O pilar de conteúdo desta semana é: "{theme["pillar"]}"']

    if theme.get("audience_label"):
        context_lines.append(f'Público-alvo específico: {theme["audience_label"]}')
    if theme.get("product"):
        context_lines.append(
            f'Produto em foco: "{theme["product"]}" — {theme["product_details"]}'
        )

    context = "\n".join(context_lines)

    image_prompt_instruction = ""
    if theme.get("product"):
        image_prompt_instruction = f"""
4. PROMPT DE IMAGEM (para colar diretamente no Nano Banana / Google AI Studio)
   Usa esta base fixa de estilo visual e adapta apenas a descrição do ícone
   central ao produto "{theme['product']}":

   Estilo base: {BRAND_STYLE}

   Escreve o prompt completo em inglês (o Nano Banana responde melhor em
   inglês), pronto a colar sem edições.
"""

    prompt = f"""
És um estratega de conteúdo para um consultor private de seguros em Portugal
(Ageas Seguros), com protocolo assinado com a Ordem dos Médicos e a Ordem dos
Médicos Dentistas. O foco principal são médicos e médicos dentistas, com
extensão a outras ordens profissionais e PMEs.

{context}

Gera sugestões de conteúdo para a semana, no seguinte formato:

1. STORIES DIÁRIOS (Seg a Sex, 1 ideia curta por dia)
2. REELS (1 a 2 ideias, com um guião base de 4-6 frases cada, incluindo
   gancho inicial, desenvolvimento e call-to-action)
3. POSTS ESTÁTICOS (2 a 3 ideias, com legenda pronta a publicar)
{image_prompt_instruction}
Escreve em português de Portugal, tom direto e profissional, sem
linguagem de venda agressiva. Sê específico e prático — cada ideia deve
ser algo que o consultor consiga gravar/publicar sem mais trabalho de
preparação. Não inventes números de capital ou coberturas além dos que
te foram dados.
"""

    response = requests.post(
        GEMINI_ENDPOINT,
        headers={"content-type": "application/json"},
        params={"key": GEMINI_API_KEY},
        json={
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"maxOutputTokens": 1500},
        },
        timeout=60,
    )
    response.raise_for_status()
    data = response.json()

    parts = data["candidates"][0]["content"]["parts"]
    text_blocks = [part["text"] for part in parts if "text" in part]
    return "\n".join(text_blocks).strip()


def post_to_slack(theme: dict, content: str) -> None:
    """Publica as sugestões no canal Slack configurado no webhook."""
    week_number = date.today().isocalendar().week
    title = theme["pillar"]
    if theme.get("audience_label"):
        title += f" — {theme['audience_label']}"
    if theme.get("product"):
        title += f" — {theme['product']}"

    header = f"*📋 Sugestões de conteúdo — Semana {week_number} — {title}*\n\n"

    message = header + content

    # Slack limita blocos de texto a ~3000 caracteres; corta em segurança
    if len(message) > 2900:
        message = message[:2900] + "\n\n_(cortado — ver script para o texto completo)_"

    response = requests.post(
        SLACK_WEBHOOK_URL,
        json={"text": message},
        timeout=30,
    )
    response.raise_for_status()


def main() -> None:
    theme = get_week_theme()
    print(f"Tema desta semana: {theme}")

    try:
        ideas = generate_content_ideas(theme)
    except Exception as exc:  # noqa: BLE001
        print(f"Erro ao gerar conteúdo: {exc}", file=sys.stderr)
        sys.exit(1)

    try:
        post_to_slack(theme, ideas)
    except Exception as exc:  # noqa: BLE001
        print(f"Erro ao publicar no Slack: {exc}", file=sys.stderr)
        sys.exit(1)

    print("Sugestões publicadas no Slack com sucesso.")


if __name__ == "__main__":
    main()
