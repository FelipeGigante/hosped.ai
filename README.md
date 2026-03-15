# hosped.ai

> **Seu concierge de hospedagem no WhatsApp.**
> Encontra a melhor estadia no Brasil e ainda monta um mini-guia da região — tudo em linguagem natural, sem abrir nenhuma aba.

---

## O problema

Escolher hospedagem no Brasil ainda é uma jornada fragmentada: Google, OTAs, Instagram, Maps, avaliações soltas, dúvidas sobre bairro e segurança — e no final, o usuário ainda não sabe com confiança se escolheu bem.

O problema não é falta de informação. É falta de **curadoria conversacional confiável com foco em decisão**.

---

## A solução

O hosped.ai recebe uma intenção como:

> *"Quero ir pra Salvador em abril, casal, até R$ 500 a diária, perto da praia, com café e boa segurança."*

E responde com:

- **Top 3 hospedagens** ranqueadas e explicadas com trade-offs
- **Justificativa clara** para cada recomendação
- **Mini-guia local** com café, bar, restaurante e passeio perto da hospedagem
- **CTA direto**: reservar, refinar ou ver mais opções

Tudo dentro do WhatsApp, em linguagem natural, sem formulário, sem filtros frios.

---

## Demonstração

```
Usuário: quero ir pro Rio, 2 pessoas, de 15 a 17/03, até R$ 400, perto da praia

Hospedaí: Encontrei 3 opções para você no Rio de Janeiro:

1️⃣ Hotel Atlântico Copacabana — melhor custo-benefício
R$ 250–380/noite · Copacabana · café da manhã incluso
A 200m da praia, bem avaliado e dentro do orçamento.

2️⃣ Mango Tree Ipanema — melhor localização
R$ 350–520/noite · Ipanema · piscina + vista para o mar
Um pouco acima do orçamento, mas em frente à praia de Ipanema.

3️⃣ Hotel Santa Teresa — mais charme
R$ 280–420/noite · Santa Teresa · vista panorâmica
Bairro boêmio com experiência única. Perfeito para casais.

📍 Perto da opção 1 — Copacabana:
☕ Padaria Brasileira — café da manhã carioca clássico
🍽 Pergula Restaurant — frutos do mar com vista pro mar
🍺 Devassa Copacabana — happy hour animado
🏖 Praia de Copacabana — 5 min a pé

_Valores estimados — confirme no momento da reserva._

O que prefere?
*1* Reservar opção 1 | *2* Reservar opção 2 | *3* Reservar opção 3 | *4* Ver mais opções
```

---

## Arquitetura

```
WhatsApp (usuário)
       ↓
Evolution API  ──webhook──►  FastAPI
                                ↓
                         Input Guardrail
                                ↓
                      In-memory Session
                                ↓
                     LangChain Agent (Claude)
                         ↓  bind_tools
                    ┌────┴─────────────────────┐
                    │         Tools             │
                    │  extract_trip_intent      │  ← LLM structured output
                    │  search_hotels            │  ← FAISS RAG + budget filter
                    │  rank_hotels              │  ← scoring determinístico
                    │  generate_local_guide     │  ← base curada JSON
                    │  create_booking_handoff   │  ← CTA / link de reserva
                    │  save_lead                │  ← analytics JSONL
                    └───────────────────────────┘
                                ↓
                        Output Guardrail
                                ↓
                    Evolution API  ──send──►  WhatsApp
```

### Princípio de design

> **LLM para entendimento, extração e explicação.**
> **Código determinístico para busca, ranking e regras críticas.**

Isso evita alucinação, garante rastreabilidade e mantém a confiança do usuário na recomendação.

---

## Tecnologias

| Camada | Tecnologia | Por quê |
|---|---|---|
| LLM principal | [Claude claude-sonnet-4-6](https://anthropic.com) via `langchain-anthropic` | Melhor compreensão de linguagem natural em PT-BR |
| LLM extração | Claude Haiku (rápido e barato) | Structured output para `TripIntent` |
| Agent framework | [LangChain](https://langchain.com) — `create_tool_calling_agent` + `AgentExecutor` | Tool calling nativo, prompt engineering, orquestração |
| Busca semântica | [FAISS](https://github.com/facebookresearch/faiss) + `sentence-transformers` | RAG local, sem infra extra, funciona em PT-BR |
| Embeddings | `paraphrase-multilingual-MiniLM-L12-v2` | Multilingual, ~120MB, gratuito, roda in-process |
| API | [FastAPI](https://fastapi.tiangolo.com) | Async, rápido, webhook background tasks |
| WhatsApp | [Evolution API](https://github.com/EvolutionAPI/evolution-api) | Self-hosted, gratuito, QR code sem aprovação |
| Sessão | Dict in-memory com TTL | Zero dependência externa para MVP |
| Observabilidade | [LangSmith](https://smith.langchain.com) | Tracing de tool calls e prompts |
| Infra | Docker + Docker Compose | 2 serviços: `app` + `evolution` |

---

## Estrutura do projeto

```
hosped.ai/
├── app/
│   ├── main.py           # FastAPI + webhook endpoint
│   ├── agent.py          # LangChain agent, system prompt, few-shot examples
│   ├── tools.py          # 6 tools: intent, search, rank, guide, handoff, lead
│   ├── vector_store.py   # FAISS index construído a partir de hotels.json
│   ├── session.py        # Histórico de conversa in-memory
│   ├── guardrails.py     # Validação de input e output
│   ├── whatsapp.py       # Cliente Evolution API (send, typing, parse)
│   └── data/
│       ├── hotels.json       # 25 hotéis curados (5 cidades)
│       └── local_guide.json  # ~35 lugares por cidade/bairro
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── .env.example
├── SETUP.md
└── PRD.md
```

---

## Tools do agente

| Tool | Tipo | O que faz |
|---|---|---|
| `extract_trip_intent` | LLM + structured output | Extrai destino, datas, hóspedes, orçamento e preferências da mensagem livre |
| `search_hotels` | RAG (FAISS) + filtro | Busca semântica por preferências + filtro de orçamento e cidade |
| `rank_hotels` | Determinístico | Score ponderado: orçamento (30%), preferências (25%), avaliação (20%), perfil da viagem (15%), segurança (10%) |
| `generate_local_guide` | Base curada | Retorna 3–5 sugestões por categoria (café, bar, restaurante, praia, passeio) perto da hospedagem |
| `create_booking_handoff` | Lookup | Gera CTA com link de reserva e contato do hotel |
| `save_lead` | I/O | Persiste sessão + recomendações em `leads.jsonl` para analytics |

---

## Cidades disponíveis

| Cidade | Hotéis | Guia local |
|---|---|---|
| Salvador | 5 | Pelourinho, Barra, Rio Vermelho |
| Rio de Janeiro | 5 | Copacabana, Ipanema, Santa Teresa, Lapa |
| São Paulo | 5 | Jardins, Centro, Morumbi, Vila Olímpia |
| Florianópolis | 5 | Lagoa da Conceição, Jurerê, Campeche, Centro |
| Gramado | 5 | Centro, Planalto, Zona Rural |

---

## Guardrails

### Input
- Mensagens vazias ou acima de 1.000 caracteres são rejeitadas com mensagem amigável
- Padrões de spam (caracteres repetidos, flood de links) são bloqueados

### Output
- Disclaimer de preço injetado automaticamente quando valores são mencionados
- Resposta truncada em 4.000 chars (limite WhatsApp)
- LLM instruído via system prompt a nunca inventar hotel, preço ou localização fora da base

---

## Como rodar

Veja [SETUP.md](./SETUP.md) para instruções completas.

**TL;DR:**
```bash
cp .env.example .env   # adicione sua ANTHROPIC_API_KEY
docker compose up --build
```

---

## Melhorias futuras

### Produto
- [ ] Suporte a mais cidades (integrar APIs reais: Booking, Airbnb, OTAs)
- [ ] Salvar shortlist e reenviar por link (`/minhas-opcoes`)
- [ ] Compartilhamento de recomendação entre usuários
- [ ] Reengajamento pós-conversa ("Sua viagem é amanhã! Precisa de algo?")
- [ ] Concierge da estadia: checklist de chegada, dicas do bairro, suporte durante a viagem

### Técnico
- [ ] Persistir FAISS index em disco (evitar reindexar no restart)
- [ ] Substituir histórico in-memory por Redis ou SQLite para múltiplas instâncias
- [ ] Streaming de resposta (digitar enquanto o agente pensa)
- [ ] Testes automatizados de fluxo (happy path + slot filling + refinamento)
- [ ] Painel admin: visualizar conversas, leads e taxa de conversão
- [ ] Integração com PMS/OTAs via adapters plugáveis

### Negócio
- [ ] Afiliação com Booking.com / Decolar para comissão por reserva
- [ ] SaaS B2B: hotéis e pousadas respondem e convertem via WhatsApp próprio
- [ ] Destaque patrocinado com transparência explícita ("parceiro")
- [ ] Upsell de experiências locais (passeios, restaurantes, transfers)

---

## Contribuindo

1. Fork o repositório
2. Crie uma branch: `git checkout -b feat/nova-cidade`
3. Adicione hotéis em `app/data/hotels.json` e lugares em `app/data/local_guide.json`
4. Abra um PR

---
