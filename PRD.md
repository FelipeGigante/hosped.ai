PRD — WhatsApp Hospitality-First Travel Agent
1. Visão do produto

Nome provisório: StayZap / Hospedaí / Check-in AI
Categoria: AI travel assistant via WhatsApp
Tese: ajudar brasileiros a escolher melhor onde ficar em viagens domésticas, reduzindo a fricção entre intenção, pesquisa, comparação e decisão, tudo dentro do canal que já usam diariamente: o WhatsApp.

One-liner

“Seu concierge de hospedagem no WhatsApp: encontra a melhor estadia no Brasil e já monta um mini-plano da região.”

Pitch

O produto recebe uma intenção conversacional como:

“Quero viajar para Salvador em abril, casal, até R$ 500 a diária, perto da praia, com café e boa segurança.”

E devolve:

3 opções de hospedagem

explicação dos trade-offs

recomendação personalizada

mini-roteiro de 24h perto da hospedagem

CTA final para reservar, salvar ou refinar a busca

2. Problema

Hoje, a jornada para escolher hospedagem no Brasil é fragmentada:

o usuário pesquisa no Google

compara OTA

olha Instagram e Maps

lê avaliações soltas

tenta entender bairro/localização

depois ainda precisa descobrir o que fazer perto

Isso gera:

excesso de opções

comparação cansativa

pouca clareza sobre trade-offs

dificuldade de confiar na escolha

abandono antes da reserva

O problema não é “falta de informação”.
É falta de curadoria conversacional confiável com foco em decisão.

3. Oportunidade

Em vez de construir mais um “planejador geral de viagem com IA”, o produto entra por um wedge mais forte:

wedge principal

Escolha de hospedagem com intenção transacional alta

wedge secundário

Mini-guia local baseado na estadia escolhida

Isso posiciona o produto como:

menos amplo

mais útil

mais demonstrável

mais monetizável

mais memorável para jurados

4. Objetivo do MVP

Entregar um assistente no WhatsApp que:

entenda a intenção de viagem do usuário

busque hospedagens compatíveis

ranqueie opções com justificativa clara

apresente shortlist personalizada

ofereça um mini-guia local da região

gere um próximo passo claro: reservar, salvar ou pedir novas opções

Objetivo de negócio no hackathon

Demonstrar que o WhatsApp pode ser a interface de entrada para conversão em turismo doméstico, começando por hospedagem.

Objetivo de produto no hackathon

Criar um MVP que pareça um produto real, não apenas um chatbot bonito.

5. Público-alvo
ICP primário

Brasileiro viajando dentro do Brasil a lazer, usando WhatsApp como canal principal de comunicação.

Perfil

casal, família pequena ou grupo de amigos

viagens domésticas de fim de semana, feriados ou férias

orçamento moderado

quer praticidade

não quer abrir 10 abas

valoriza localização, segurança, café da manhã, custo-benefício e proximidade de pontos de interesse

Exemplos de segmentos iniciais

casal indo para Salvador

grupo indo para Rio ou Florianópolis

pessoa viajando para SP para lazer + gastronomia

casal indo para Campos do Jordão ou Gramado

6. Jobs to be done
Job funcional

“Me ajude a encontrar uma boa hospedagem dentro do meu orçamento e perfil.”

Job emocional

“Quero sentir que escolhi bem, sem medo de cair em cilada.”

Job contextual

“Já que vou ficar nessa região, me diga rapidamente o que vale fazer por perto.”

7. Proposta de valor
Valor principal

O usuário descreve sua viagem em linguagem natural e recebe uma shortlist explicada, com contexto local e próximo passo acionável.

Diferenciais

canal natural: WhatsApp

linguagem conversacional

recomendação com justificativa

foco em hospedagem, não em roteiro genérico

camada local como complemento, não como produto principal

experiência de concierge, não de busca fria

8. Escopo do MVP
In scope

receber mensagem via WhatsApp

extrair intenção da viagem

coletar dados faltantes de forma conversacional

buscar hospedagens em uma base limitada

aplicar ranking

retornar top 3 opções

explicar por que cada opção apareceu

gerar mini-roteiro/guia local perto da hospedagem

permitir refinamento (“mais barato”, “mais perto da praia”, “com piscina”)

registrar lead/sessão

gerar link de reserva ou handoff

Out of scope

reserva completa com pagamento no próprio WhatsApp

inventário nacional em tempo real de todas as OTAs

suporte multilíngue amplo

planejamento completo de viagem ponta a ponta

voos, aluguel de carro, seguro, eventos em tempo real

recomendação aberta de bares/restaurantes em qualquer cidade do Brasil sem base validada

9. Hipóteses do produto

Usuários preferem explicar a viagem em linguagem natural em vez de preencher filtros frios.

Uma shortlist pequena com justificativa converte melhor do que muitas opções.

O WhatsApp reduz atrito em comparação com sites ou apps dedicados.

Um mini-guia local aumenta percepção de valor e diferenciação.

Mesmo com base limitada de inventário, a experiência já é forte o suficiente para demo e validação inicial.

10. Fluxo principal do usuário
Fluxo feliz

Usuário inicia conversa no WhatsApp.

Informa destino, datas, perfil e orçamento.

O sistema identifica slots faltantes.

Faz perguntas curtas para completar o contexto.

Busca hospedagens elegíveis.

Ranqueia opções segundo preferências declaradas e inferidas.

Retorna 3 recomendações com:

nome

faixa de preço

bairro/localização

principais atributos

trade-offs

Gera mini-guia da região.

Oferece CTA:

reservar

salvar opções

pedir mais alternativas

refinar busca

11. Exemplo de experiência
Input

“Quero viajar para Salvador em abril, casal, até R$ 500 a diária, perto da praia, com café e boa segurança.”

Output esperado

Encontrei 3 opções que fazem sentido para o seu perfil:

1. Hotel X — melhor custo-benefício
R$ 460/noite · perto da praia · café incluso
Bom equilíbrio entre preço, localização e avaliações.

2. Pousada Y — melhor localização
R$ 510/noite · região mais turística · acesso fácil
Um pouco acima do orçamento, mas melhor para mobilidade e passeio.

3. Hotel Z — melhor avaliação
R$ 490/noite · bairro mais tranquilo
Mais forte em conforto e segurança, com menos vida noturna ao redor.

Mini-plano perto da opção 1:

café da manhã local

bar à noite

passeio curto

praia acessível

Próximo passo:

Quero reservar a opção 1

Me mostra mais opções

Quero algo mais barato

Quero focar mais em segurança

12. Requisitos funcionais
FR1 — Captura de intenção

O sistema deve interpretar mensagens livres com informações como:

destino

datas ou período

número de pessoas

tipo de viagem

orçamento

preferências

restrições

FR2 — Slot filling

O sistema deve identificar campos faltantes e pedir apenas o necessário para seguir.

Campos mínimos para recomendar:

destino

período

quantidade de hóspedes

orçamento aproximado

FR3 — Busca de hospedagem

O sistema deve consultar uma fonte estruturada de hospedagens com metadados mínimos:

nome

cidade

bairro

faixa de preço

amenities

proximidade de pontos relevantes

nota/avaliação

link de reserva

descrição curta

FR4 — Ranking

O sistema deve ranquear hospedagens com base em:

aderência ao orçamento

localização

amenities desejadas

segurança percebida

perfil da viagem

qualidade/avaliação

intenção prioritária declarada

FR5 — Explicabilidade

Toda recomendação deve vir com justificativa breve e compreensível.

FR6 — Mini-guia local

Após recomendar hospedagem, o sistema deve sugerir um micro-roteiro da região:

3 a 5 sugestões

categorizadas

compatíveis com o perfil do usuário

FR7 — Refinamento

O sistema deve permitir comandos de refinamento como:

“mais barato”

“mais perto da praia”

“com piscina”

“mais seguro”

“com estacionamento”

FR8 — CTA transacional

O sistema deve oferecer um próximo passo claro:

reservar

salvar

receber mais opções

falar com atendente/parceiro

FR9 — Persistência de sessão

O sistema deve manter contexto da conversa por sessão.

FR10 — Logging e observabilidade

O sistema deve armazenar:

mensagens

tool calls

critérios usados no ranking

recomendação final entregue

13. Requisitos não funcionais
NFR1 — Tempo de resposta

Primeira shortlist em até 15 segundos em cenário de hackathon.

NFR2 — Clareza

Respostas devem ser curtas, escaneáveis e úteis dentro do padrão WhatsApp.

NFR3 — Confiabilidade

O sistema não deve inventar hospedagens ou preços fora da base.

NFR4 — Segurança

Dados do usuário devem ser armazenados minimamente e com cuidado.

NFR5 — Auditabilidade

Deve ser possível entender por quais critérios uma opção foi recomendada.

NFR6 — Escalabilidade futura

Arquitetura deve permitir trocar fonte mockada por APIs reais depois.

14. Estratégia de IA

Aqui está o ponto mais importante: para hackathon, não vale a pena criar um sistema altamente autônomo e caótico.
O ideal é usar IA onde ela gera valor e usar pipeline determinístico onde confiança importa.

Princípio

LLM para entendimento, tool routing e explicação.
Código determinístico para busca, filtros, ranking e regras críticas.

Isso evita:

hallucination

respostas inconsistentes

dificuldade de debug

perda de confiança

15. Arquitetura proposta
Stack principal

Python

FastAPI para webhooks e APIs

LangChain para agent, tool calling e orchestration

LangGraph opcional para fluxo com estado

Pydantic para schemas estruturados

Redis para sessão/memória curta

PostgreSQL para persistência

Twilio WhatsApp API ou Meta WhatsApp Cloud API

LangSmith para tracing/observabilidade

Docker para entrega

16. Arquitetura lógica
WhatsApp User
   ↓
WhatsApp Provider (Twilio / Meta)
   ↓
FastAPI Webhook
   ↓
Session Manager (Redis)
   ↓
Conversation Orchestrator (LangChain Agent / LangGraph)
   ↓
Tools Layer
   ├── extract_trip_intent
   ├── ask_missing_fields
   ├── search_hotels
   ├── rank_hotels
   ├── explain_recommendations
   ├── generate_local_mini_guide
   ├── save_lead
   └── create_booking_handoff
   ↓
Response Composer
   ↓
WhatsApp outbound message
17. Abordagem de agent
Recomendação

Para o MVP, usar um agente principal com tools e um fluxo bem controlado.

Não recomendo começar com vários agentes especializados no hackathon, porque:

aumenta complexidade

dificulta previsibilidade

não melhora tanto a demo

aumenta risco de falha

Melhor desenho para o hackathon

1 orchestrator agent + tools especializadas + ranking determinístico

Evolução futura

Depois, sim, pode evoluir para:

agent de hospedagem

agent de experiência local

agent de pós-reserva

agent comercial B2B para hotéis/parceiros

18. Tools propostas

Essas são as tools centrais do sistema.

18.1 extract_trip_intent

Objetivo: extrair intenção estruturada da mensagem do usuário.

Input

Mensagem livre do usuário

Output
{
  "destination": "Salvador",
  "date_range": "abril",
  "guests": 2,
  "budget_per_night": 500,
  "preferences": ["perto da praia", "café da manhã", "segurança"],
  "trip_type": "lazer"
}
Implementação

LLM + structured output com Pydantic

18.2 identify_missing_fields

Objetivo: descobrir o que falta para recomendar.

Output
{
  "missing_fields": ["checkin_date", "checkout_date"]
}
18.3 search_hotels

Objetivo: buscar hotéis elegíveis em base estruturada.

Input

Critérios mínimos de busca

Output

Lista bruta de opções

Fonte

No MVP, pode ser:

CSV/JSON mockado

base curada de 3 a 5 cidades

adapters futuros para OTAs, PMS ou parceiros

18.4 rank_hotels

Objetivo: ordenar as opções com score determinístico.

Critérios sugeridos

preço dentro do orçamento

distância da praia/centro

amenities desejadas

avaliação

segurança da região

aderência ao perfil da viagem

Output
{
  "ranked_hotels": [
    {
      "hotel_id": "h_123",
      "score": 0.89,
      "reason_tags": ["bom custo-benefício", "perto da praia", "café incluso"]
    }
  ]
}
18.5 generate_recommendation_summary

Objetivo: transformar ranking em texto curto e confiável.

Regras

não inventar atributos

usar apenas dados vindos da base

explicar trade-offs

no máximo 3 opções principais

18.6 generate_local_mini_guide

Objetivo: sugerir lugares/experiências perto da hospedagem recomendada.

Exemplos

café

bar

restaurante

praia/ponto turístico

rolê noturno

Observação importante

No MVP, isso deve usar base curada, não recomendação aberta na internet em tempo real.

18.7 save_lead

Objetivo: registrar intenção e opções entregues para analytics e follow-up.

18.8 create_booking_handoff

Objetivo: gerar próximo passo transacional.

Pode retornar

link de reserva

mensagem para parceiro

contato do hotel

CTA interno

19. Desenho técnico do fluxo com LangChain
Estado da conversa

O sistema deve manter um objeto de estado parecido com:

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
    selected_hotel_id: str | None = None
    conversation_stage: str = "intent_capture"
Estágios sugeridos

intent_capture

slot_filling

searching

ranking

presenting_options

refining

handoff

Fluxo sugerido

webhook recebe mensagem

carrega sessão

agent chama extract_trip_intent

agent chama identify_missing_fields

se faltar algo, pergunta

se já tiver contexto mínimo, chama search_hotels

chama rank_hotels

chama generate_recommendation_summary

chama generate_local_mini_guide

monta resposta final

persiste sessão e logs

20. Estratégia de dados
Para hackathon

O melhor caminho é uma estratégia híbrida:

Base de hospedagem

dataset curado com 20–50 propriedades por cidade

3 cidades iniciais, por exemplo:

Salvador

Rio de Janeiro

São Paulo

Campos mínimos por hotel

id

nome

cidade

bairro

faixa de preço

amenities

nota

tags de perfil

descrição curta

link de reserva

distância relativa de pontos

tags como:

praia

vida noturna

família

seguro

luxo

custo-benefício

Base local

10–20 lugares por cidade/região

categorias:

café

bar

restaurante

atração

passeio

associar bairros/regiões

Por que isso é melhor?

Porque o MVP precisa parecer confiável.
Dados curados vencem dados “meio vivos, meio errados” em hackathon.

21. Algoritmo de ranking

O ranking não deve ficar 100% na mão do LLM.

Fórmula sugerida
score_final =
  0.30 * aderencia_orcamento +
  0.25 * aderencia_localizacao +
  0.15 * aderencia_amenities +
  0.15 * avaliacao +
  0.10 * aderencia_perfil_viagem +
  0.05 * score_segurança
Regras

penalizar opções muito acima do orçamento

premiar matching exato de preferências explícitas

permitir ajuste por intenção dominante:

praia

custo

segurança

gastronomia

família

conforto

Papel do LLM

O LLM explica o ranking.
O código calcula o ranking.

22. Prompts e comportamento do agente

O sistema prompt do agente deve reforçar:

você é um concierge de hospedagem

seu foco principal é recomendar estadias

você só usa dados disponíveis nas tools

você não inventa hotel, preço, avaliação ou localização

você deve pedir apenas dados faltantes essenciais

suas respostas devem ser curtas, claras e úteis para WhatsApp

depois da shortlist, ofereça micro-guia local como complemento

sempre encerre com um próximo passo objetivo

23. Guardrails
Regras críticas

nunca afirmar preço em tempo real se a base não for live

nunca afirmar disponibilidade garantida sem fonte

deixar claro quando algo é “estimativa”, “faixa” ou “recomendação”

nunca inventar atrativos/bares que não estejam na base

não prometer reserva concluída se for apenas handoff

Exemplo de transparência

“Esses valores são estimativas com base na nossa base atual e podem variar no momento da reserva.”

24. Métricas de sucesso
Métricas de produto

taxa de conversas que chegam à shortlist

tempo médio até primeira recomendação

taxa de refinamento

taxa de clique em reservar/salvar

satisfação percebida da resposta

Métricas de hackathon

wow factor na demo

clareza do problema

percepção de produto real

confiança na recomendação

fluidez do fluxo no WhatsApp

Metas iniciais para demo

primeira recomendação em menos de 15s

90%+ das conversas de demo com shortlist válida

100% das recomendações explicadas com trade-offs

25. Diferenciais competitivos do MVP

Em vez de competir como “IA que planeja viagem inteira”, o produto compete como:

posicionamento

“Hospitality-first travel agent via WhatsApp.”

diferenciais

entra na parte mais decisiva da jornada

conversa em linguagem natural

entrega shortlist, não overload

adiciona camada local com contexto

tem CTA transacional real

26. Estratégia de monetização futura
Fase 1

afiliado / comissão de reserva

lead qualificado para parceiros

Fase 2

destaque patrocinado com transparência explícita

SaaS B2B para hotéis/pousadas responderem e converterem via WhatsApp

white-label para redes ou destinos

Fase 3

upsell de experiências locais

pacotes de bairro/região

inteligência para hotelaria e turismo local

Observação

Evitar no pitch inicial qualquer monetização que pareça destruir confiança da recomendação.

27. Riscos
Risco 1 — inventário limitado

Sem boa base de hospedagem, a recomendação perde força.

Mitigação

Curar poucas cidades e garantir qualidade.

Risco 2 — parecer só interface sobre OTA

Pode soar como camada superficial.

Mitigação

Focar na inteligência conversacional + trade-offs + contexto local.

Risco 3 — confiança

Recomendação ruim destrói valor rápido.

Mitigação

Explicabilidade + ranking determinístico + escopo controlado.

Risco 4 — querer abraçar viagem inteira

Produto vira planner genérico.

Mitigação

Manter narrativa hospitality-first.

28. Roadmap
Fase hackathon

WhatsApp inbound/outbound

captura de intenção

slot filling

busca em base curada

ranking

shortlist top 3

mini-guia local

CTA final

Fase 2

mais cidades

integração com APIs reais

salvar preferências

compartilhamento de shortlist

painel admin

Fase 3

pós-reserva

concierge da estadia

parceiro/hotel dashboard

experiências locais patrocinadas

reengajamento

29. Critérios de aceitação do MVP

O MVP será considerado pronto se:

o usuário conseguir iniciar pelo WhatsApp

o sistema conseguir entender intenção em linguagem natural

o sistema pedir dados faltantes de forma objetiva

o sistema retornar 3 opções coerentes

cada opção tiver explicação clara

houver um mini-guia local compatível

houver CTA final

o fluxo rodar de ponta a ponta em demo sem intervenção manual

30. Demo script para apresentação
Cena 1 — problema

“Escolher hospedagem ainda é uma jornada fragmentada e cansativa.”

Cena 2 — solução

“Criamos um concierge de hospedagem no WhatsApp para o turismo doméstico brasileiro.”

Cena 3 — uso real

Mensagem:

“Quero viajar para Salvador em abril, casal, até R$ 500 a diária, perto da praia, com café e boa segurança.”

Cena 4 — inteligência

Mostrar que o sistema:

extrai intenção

busca opções

ranqueia

explica

Cena 5 — resultado

Mostrar top 3 + mini-guia + CTA

Cena 6 — visão futura

“Começamos pela hospedagem, que é o ponto de maior intenção, e expandimos para a experiência local.”

31. Recomendação final de arquitetura

Para o que você quer, eu seguiria assim:

escolha técnica

Python + FastAPI

LangChain para tool-calling

LangGraph apenas se quiser estado visual/orquestração mais clara

Pydantic para contratos

Redis para sessão

Postgres para persistência

Twilio/Meta para WhatsApp

LangSmith para tracing

dataset curado para demo

escolha de produto

um agente principal

tools bem separadas

ranking determinístico

respostas curtas no estilo concierge

camada local apenas depois da shortlist

32. Tese final do PRD

Este produto não tenta ser o melhor “planejador de viagem com IA” do mundo.
Ele tenta resolver, muito bem, o momento mais crítico da jornada: escolher onde ficar.

E faz isso no canal mais natural para o brasileiro.

frase final

“Transformamos a escolha da hospedagem na porta de entrada para uma experiência de viagem personalizada no WhatsApp.”