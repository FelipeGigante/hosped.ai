# hosped.ai — PRD técnico

> Concierge de hospedagem no WhatsApp: encontra a melhor estadia no Brasil e monta um mini-guia da região.

---

## Stack

| Camada | Tecnologia |
|---|---|
| Agent & Tools | LangChain (tool calling + structured output) |
| API | FastAPI |
| Sessão | Redis |
| Persistência | PostgreSQL |
| Schema/Contratos | Pydantic |
| WhatsApp | evolution-api (self-hosted) |
| Tracing | LangSmith |
| Infra | Docker |

### WhatsApp — evolution-api

Self-hosted, gratuito, sem aprovação de conta business. Conecta via QR code.

**Setup (Docker):**
```yaml
# docker-compose.yml
evolution-api:
  image: atendai/evolution-api:latest
  ports:
    - "8080:8080"
  environment:
    - AUTHENTICATION_API_KEY=your_key
    - WEBHOOK_GLOBAL_URL=http://your-fastapi:8000/webhook
    - WEBHOOK_GLOBAL_ENABLED=true
```

**Fluxo:**
1. Sobe o container
2. Cria instância via `POST /instance/create`
3. Escaneia QR code com número do WhatsApp
4. Recebe mensagens via webhook no FastAPI
5. Envia resposta via `POST /message/sendText/{instance}`

**Payload inbound (webhook):**
```json
{
  "event": "messages.upsert",
  "data": {
    "key": { "remoteJid": "5511999999999@s.whatsapp.net" },
    "message": { "conversation": "texto da mensagem" }
  }
}
```

---

## Arquitetura

```
WhatsApp → Webhook (FastAPI) → Session (Redis) → Agent (LangChain) → Tools → Response
```

### Estado da sessão

```python
class TripSession(BaseModel):
    user_id: str
    destination: str | None = None
    checkin_date: str | None = None
    checkout_date: str | None = None
    guests: int | None = None
    budget_per_night: float | None = None
    preferences: list[str] = []
    trip_type: str | None = None
    shortlisted_hotels: list[dict] = []
    stage: Literal[
        "intent_capture", "slot_filling", "searching", "presenting", "refining", "handoff"
    ] = "intent_capture"
```

---

## Features

### F1 — Webhook WhatsApp

- Recebe mensagem inbound via POST
- Carrega/cria sessão no Redis
- Envia para o agent
- Retorna resposta outbound

---

### F2 — Agent principal

Um único LangChain agent com tool calling. Sem multi-agent no MVP.

**System prompt central:**
- Você é um concierge de hospedagem
- Use apenas dados das tools, nunca invente hotel, preço ou avaliação
- Respostas curtas e escaneáveis (padrão WhatsApp)
- Sempre encerre com um próximo passo claro

**Fluxo:**
1. `extract_trip_intent` → extrai o que o usuário disse
2. `identify_missing_fields` → verifica o que falta
3. se faltar → pergunta (máx. 1 campo por mensagem)
4. se completo → `search_hotels` → `rank_hotels` → `generate_summary`
5. `generate_local_guide` → mini-guia da região
6. CTA final

---

### F3 — Tools

#### `extract_trip_intent`
Extrai intenção estruturada da mensagem livre.

```python
class TripIntent(BaseModel):
    destination: str | None
    date_range: str | None
    guests: int | None
    budget_per_night: float | None
    preferences: list[str]
    trip_type: str | None
```
> Implementação: LLM + structured output (Pydantic)

---

#### `identify_missing_fields`
Retorna campos obrigatórios ausentes.

Campos mínimos para recomendar: `destination`, `checkin_date`, `checkout_date`, `guests`, `budget_per_night`

```python
class MissingFields(BaseModel):
    missing: list[str]
    next_question: str  # pergunta natural para o usuário
```

---

#### `search_hotels`
Busca hotéis na base local compatíveis com os critérios.

```python
class HotelSearchInput(BaseModel):
    destination: str
    budget_per_night: float
    guests: int
    preferences: list[str]
```

> Fonte: JSON/CSV curado (20–50 propriedades por cidade). Cidades iniciais: Salvador, Rio de Janeiro, São Paulo.

---

#### `rank_hotels`
Ranking determinístico — o LLM não decide o score, apenas explica.

```python
score = (
    0.30 * budget_fit +
    0.25 * location_fit +
    0.15 * amenities_fit +
    0.15 * rating +
    0.10 * profile_fit +
    0.05 * safety_score
)
```

Retorna top 3 com `score` e `reason_tags`.

---

#### `generate_summary`
Transforma top 3 em texto curto para WhatsApp.

- usa apenas dados da base
- explica trade-off de cada opção
- máx. 3 opções

---

#### `generate_local_guide`
Micro-roteiro da região da hospedagem recomendada.

- 3–5 sugestões categorizadas (café, bar, praia, passeio)
- base curada por cidade/bairro
- não usa internet em tempo real no MVP

---

#### `save_lead`
Persiste sessão + opções entregues no PostgreSQL para analytics.

---

#### `create_booking_handoff`
Gera CTA transacional: link de reserva, contato do hotel ou mensagem de handoff.

---

### F4 — Base de dados curada

#### Hotels (JSON/CSV)

| Campo | Tipo |
|---|---|
| id | str |
| nome | str |
| cidade | str |
| bairro | str |
| preco_min / preco_max | float |
| amenities | list[str] |
| nota | float |
| tags | list[str] (praia, família, seguro, luxo...) |
| descricao | str |
| link_reserva | str |

#### Local Guide (JSON)

| Campo | Tipo |
|---|---|
| cidade | str |
| bairro | str |
| nome | str |
| categoria | str (cafe, bar, restaurante, praia, passeio) |
| descricao | str |

---

### F5 — Logging / Observabilidade

- LangSmith para tracing de tool calls
- Salvar no PostgreSQL: `user_id`, `session`, `tools_called`, `hotels_returned`, `stage_final`

---

## Guardrails

- Nunca afirmar preço em tempo real se a base não for live
- Nunca inventar atrativo que não está na base
- Deixar claro quando valor é "estimativa" ou "faixa"
- Não prometer reserva concluída se for handoff

---

## Critérios de aceite do MVP

- [ ] Usuário envia mensagem no WhatsApp e recebe resposta
- [ ] Sistema entende intenção em linguagem natural
- [ ] Sistema pede dados faltantes (1 campo por vez)
- [ ] Retorna 3 opções com justificativa
- [ ] Inclui mini-guia local
- [ ] CTA final presente
- [ ] Fluxo de ponta a ponta sem intervenção manual
