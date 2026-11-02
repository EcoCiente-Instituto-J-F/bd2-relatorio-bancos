# Documentação dos bancos de dados — EcoCiente

**Projeto de IA consultado:** `C:\Users\dominicvitorino-ieg\OneDrive - Instituto J&F\Área de Trabalho\Escola\2 ano\IA (Grilo)\Inter\ia-eko`

**Método desta análise:** leitura dos arquivos locais do projeto, sem conexão com os bancos. A existência de código de acesso não comprova que o serviço esteja ativo nem que haja dados persistidos.

## MongoDB

### Finalidade no sistema

O MongoDB guarda a memória das conversas com a Eko em `sessoes`: a aplicação registra mensagens, recupera o histórico e pode condensar mensagens antigas em um resumo da sessão. O código atual também usa `memoria_usuarios` para guardar um resumo por usuário entre conversas. Fontes: `src/database/mongodb.py:27-32` e `src/services/session_service.py:115-129,350-419`.

### Banco, coleção e estrutura

O nome padrão do banco na configuração é `ecociente`; ele pode ser alterado por `MONGODB_DATABASE`. As estruturas abaixo são montadas pelo serviço da aplicação, não por uma declaração de esquema obrigatório do MongoDB. Fonte: `src/core/config.py:57-59`.

**Coleção `sessoes`**

| Campo | Tipo no código | Finalidade |
| --- | --- | --- |
| `_id` | Identificador gerado pelo MongoDB | Identificação interna do documento; a consulta do serviço o omite da resposta. |
| `session_id` | Texto UUID | Identificador público da sessão de conversa. |
| `usuario_id` | Inteiro | Usuário ao qual a sessão pertence. |
| `status` | Texto | Criado com o valor `active`. |
| `created_at` | Data e hora UTC | Criação da sessão. |
| `updated_at` | Data e hora UTC | Última atualização da sessão. |
| `expira_em` | Data e hora UTC | Referência para a expiração da sessão. |
| `ultima_rota` | Texto ou `null` | Última rota definida pelo fluxo da Eko. |
| `memory_summary` | Texto | Resumo das mensagens antigas. |
| `memory_revision` | Inteiro | Versão usada no controle de gravações concorrentes do resumo. |
| `messages` | Lista de documentos | Mensagens da conversa. |
| `memoria_longa_ate` | Data e hora UTC, opcional | Última mensagem da sessão já consolidada na memória do usuário. |

Cada item de `messages` contém `id`, `role` (`user` ou `assistant`), `content` e `created_at`. O campo opcional `bloqueada` marca uma mensagem rejeitada pelo guardrail para que ela não entre na memória de longo prazo. O serviço aceita somente esses dois papéis e adiciona mensagens ao array com `$push`. Fontes: `src/services/session_service.py:174-197,421-445`.

**Coleção `memoria_usuarios`**

| Campo | Tipo no código | Finalidade |
| --- | --- | --- |
| `_id` | Identificador gerado pelo MongoDB | Identificação interna, omitida na leitura do serviço. |
| `usuario_id` | Inteiro | Identifica o dono da memória; índice único. |
| `texto` | Texto | Resumo consolidado de informações do usuário entre conversas. |
| `revision` | Inteiro | Controle de concorrência na atualização do resumo. |
| `updated_at` | Data e hora UTC | Última alteração. |

O serviço cria um documento quando grava a primeira memória do usuário, lê por `usuario_id` e atualiza `texto` somente quando a revisão esperada ainda corresponde à armazenada. A remoção lógica esvazia `texto` e incrementa `revision`; não apaga o documento. Fontes: `src/services/session_service.py:350-419`.

### Índices e duração

- `session_id`: índice único.
- `expira_em`: índice TTL com `expireAfterSeconds=0`.
- `memoria_usuarios.usuario_id`: índice único; o código não define TTL para essa coleção.
- A configuração de exemplo usa `SESSION_TTL_SECONDS=1800` (30 minutos). O prazo é renovado quando mensagens são adicionadas e quando ocorre a compactação da memória.
- O encerramento solicitado pela API remove o documento da coleção; o valor `closed` é retornado pela operação, não gravado como novo estado do documento.

Fonte dos índices: `src/database/mongodb.py:27-32`. Os valores de duração são definidos em `src/core/config.py:68-73`.

### Exemplo fictício da estrutura

As datas estão representadas como texto para facilitar a leitura. No MongoDB, o código grava valores de data.

```json
{
  "session_id": "d45e5e29-0453-4c3a-8ed4-2bd45f1525d9",
  "usuario_id": 42,
  "status": "active",
  "created_at": "2026-10-29T15:00:00Z",
  "updated_at": "2026-10-29T15:01:00Z",
  "expira_em": "2026-10-29T15:31:00Z",
  "ultima_rota": "rota_definida_pelo_fluxo",
  "memory_summary": "",
  "memory_revision": 0,
  "messages": [
    {
      "id": "a1b2c3d4e5f6",
      "role": "user",
      "content": "Como devo descartar vidro?",
      "created_at": "2026-10-29T15:00:30Z"
    },
    {
      "id": "f6e5d4c3b2a1",
      "role": "assistant",
      "content": "Resposta ilustrativa da Eko.",
      "created_at": "2026-10-29T15:01:00Z"
    }
  ]
}
```

O campo `_id` foi omitido do exemplo para manter o foco nos dados montados pela aplicação. O exemplo mostra uma sessão antes de qualquer consolidação de memória longa; por isso não inclui `memoria_longa_ate`.

Exemplo fictício da segunda coleção:

```json
{
  "usuario_id": 42,
  "texto": "- prefere respostas curtas\n- tem uma composteira em casa",
  "revision": 1,
  "updated_at": "2026-10-29T15:31:00Z"
}
```

### Exemplo de uso no EcoCiente

1. Uma pessoa autenticada envia uma pergunta para `POST /api/v1/chat` sem `session_id`.
2. O serviço cria um documento em `sessoes` com `insert_one` e retorna o identificador da sessão.
3. A mensagem do usuário é acrescentada a `messages` com `$push`.
4. O fluxo da Eko produz a resposta; o serviço a acrescenta a `messages` e atualiza `ultima_rota`.
5. Na próxima pergunta com o mesmo `session_id`, o serviço recupera o documento com `find_one` e fornece o histórico à Eko.

Quando a conversa ultrapassa o limite configurado de 20 mensagens, o fluxo normal pode resumir as antigas em `memory_summary` e manter as 6 mais recentes em `messages`. A compactação usa `memory_revision` para controlar atualizações concorrentes. Em `FAST_LOCAL_MODE`, o fluxo não aciona essa compactação.

Com a memória de longo prazo habilitada, `get_memory_context()` lê `memoria_usuarios` e inclui `texto` no contexto da Eko. A rota de encerramento chama a consolidação das mensagens ainda não processadas antes de remover a sessão. O método de consolidação existe, mas a busca nas chamadas Python deste repositório encontrou seu uso somente no encerramento; a configuração que sugere atualização a cada N turnos não prova que ela ocorra após cada resposta. Fontes: `src/services/session_service.py:213-226`, `src/services/chat_service.py:183-225`, `src/api/routes/sessions.py:47-58`.

### Estado identificado e limites da verificação

- A criação, leitura, atualização e remoção de sessões estão implementadas no código.
- A configuração de exemplo permite fallback para memória local quando MongoDB ou Redis falha na inicialização. Nesse modo, a conversa funciona sem persistência no MongoDB. O endpoint `/health` pode indicar `memory_fallback` para esses serviços.
- Existe um teste de integração que cria sessões e verifica resumo e mensagens recentes em um MongoDB real, mas ele depende de `TEST_MONGODB_URI`; a presença do teste não comprova que tenha sido executado neste ambiente.
- Um texto de prompt ainda menciona `MongoDB.memoria_longo_prazo.resumo_consolidado`, mas a implementação Python usa a coleção `memoria_usuarios` e o campo `texto`. O nome do prompt não foi tratado como esquema implementado. Fontes: `src/prompts/shared/orchestrator.py:66`, `src/services/session_service.py:361-419`.
- Nenhuma conexão ao MongoDB foi realizada nesta análise. O estado do servidor e os dados existentes continuam não verificados.

### Fontes no projeto de IA

- `src/database/mongodb.py` — conexão e índices.
- `src/services/session_service.py` — estrutura, operações e fallback.
- `src/services/chat_service.py` — gravação das mensagens no fluxo de conversa.
- `src/services/chat_service.py` e `src/api/routes/sessions.py` — consolidação de memória longa e encerramento da sessão.
- `src/agents/graph.py` — leitura do contexto e decisão de compactação.
- `src/api/routes/chat.py` e `src/api/routes/sessions.py` — rotas da API.
- `src/core/config.py` e `.env.example` — valores padrão de configuração.
- `tests/integration/test_memory_mongodb_real.py` — teste de integração condicionado à configuração de teste.
- `src/prompts/shared/orchestrator.py` — referência textual a uma coleção diferente da implementação atual.

## Qdrant

### Finalidade e estado verificado

O projeto de IA agora contém o carregador `src/etl/populate_qdrant.py` e um caminho de consulta integrado ao agente FAQ. Quando `FAQ_BACKEND=qdrant`, a pergunta é transformada em vetor, comparada às FAQs da coleção e a resposta canônica do melhor resultado válido é devolvida sem LLM. O padrão configurado continua `FAQ_BACKEND=rag`; portanto, a existência desse caminho no código não comprova que esteja ativado no ambiente. Fontes: `src/etl/populate_qdrant.py:1-27`, `src/core/config.py:89-101`, `src/api/main.py:62-67` e `src/agents/graph.py:247-294`.

Em 29/10/2026, o usuário informou que não havia coleção no painel consultado. Não houve nova inspeção do servidor nesta revisão de código; o estado atual da coleção e a configuração efetivamente implantada continuam sem confirmação.

### Fonte dos dados e estrutura da coleção

O carregador lê a seção de perguntas frequentes canônicas de `data/FAQ_KNOWLEDGE_BASE.md`. Cada item precisa ter `FAQ-NNN`, título, intenção, perfis relacionados e resposta canônica; palavras-chave são opcionais. A validação interrompe a carga diante de itens malformados ou IDs duplicados. Fontes: `src/etl/populate_qdrant.py:59-79,165-235`.

| Elemento | Estrutura definida no código atual | Fonte |
| --- | --- | --- |
| Coleção | Nome configurável; padrão `faq`. Um vetor sem nome por ponto. | `src/core/config.py:94`; `src/etl/populate_qdrant.py:289-299,368-376` |
| ID do ponto | UUID versão 5 gerado de um namespace fixo e do `faq_id`; cargas repetidas reutilizam o mesmo ID. | `src/etl/populate_qdrant.py:59-62,126-128` |
| Texto convertido em vetor | Título, resposta canônica e, se existirem, palavras-chave. O modelo padrão é `intfloat/multilingual-e5-large`; para a família E5, o texto de documento recebe `passage: ` e a pergunta recebe `query: `. | `src/etl/populate_qdrant.py:130-136`; `src/services/embedding_service.py:24-50`; `src/core/config.py:95` |
| Dimensão e distância | A dimensão é o tamanho do primeiro vetor gerado; não há número fixo no código. A coleção é criada com distância cosseno (`COSINE`). | `src/etl/populate_qdrant.py:361-376` |
| Payload | `faq_id`, `titulo`, `intencao`, `perfis_relacionados` (lista normalizada), `resposta_canonica`, `palavras_chave` (lista), `tipo` = `faq_canonica`, `categoria`, `perfis_texto`, `embedding_model` e `content_hash`. Há índice `KEYWORD` em `tipo`. | `src/etl/populate_qdrant.py:96-114,138-158,374-377` |

`score` é a pontuação retornada pela busca, não um campo gravado no payload. Fonte: `src/services/qdrant_service.py:62-96`.

### Exemplo fictício de um ponto

O exemplo ilustra os campos montados pelo carregador; não representa um registro consultado. O UUID, o hash e a dimensão do vetor dependem da execução e foram omitidos.

```text
id: <UUID v5 derivado de FAQ-001>
vector: <vetor numérico gerado do título, resposta e palavras-chave>
payload:
  faq_id: "FAQ-001"
  titulo: "O que é o EcoCiente?"
  intencao: "visão_geral"
  perfis_relacionados: []
  resposta_canonica: "Resposta ilustrativa da FAQ."
  palavras_chave: ["EcoCiente", "aplicativo"]
  tipo: "faq_canonica"
  categoria: "Exemplo"
  perfis_texto: "Todos"
  embedding_model: "intfloat/multilingual-e5-large"
  content_hash: <hash calculado do payload>
```

### Carga e consulta previstas pelo código

1. `python -m src.etl.populate_qdrant --dry-run` valida o arquivo e mostra um resumo sem criar o cliente Qdrant nem gerar embeddings. A execução normal pode criar a coleção e fazer `upsert` de FAQs novos ou alterados. Fonte: `src/etl/populate_qdrant.py:433-474`.
2. O `content_hash` evita recalcular embeddings de itens inalterados. O `upsert` usa o ID determinístico; por padrão, FAQs canônicas removidas do arquivo são apagadas da coleção. `--manter-ausentes` desativa essa remoção. Fontes: `src/etl/populate_qdrant.py:301-319,326-405,433-439`.
3. `--recriar` apaga e recria a coleção quando é necessário mudar o modelo ou a dimensão. O código gera os novos vetores antes de apagar a coleção anterior. Fontes: `src/etl/populate_qdrant.py:336-383,436`.
4. Com `FAQ_BACKEND=qdrant`, o serviço consulta até três resultados por padrão (`query_points` com payload), aplica o limite de similaridade padrão de `0,80` e verifica a compatibilidade de perfil. O agente devolve a `resposta_canonica` selecionada. Há fallback para RAG+LLM apenas se `FAQ_LLM_FALLBACK=true`. Fontes: `src/core/config.py:91-101`, `src/services/qdrant_service.py:62-110` e `src/agents/graph.py:247-294`.

### Limites da verificação

- O código define a estrutura, mas não comprova a existência da coleção, a quantidade de pontos, a dimensão efetiva, a qualidade dos resultados ou a ativação de `FAQ_BACKEND=qdrant` no ambiente.
- `qdrant-client` e `fastembed` estão declarados em `requirements-optional.txt:11-12`; a declaração não confirma instalação ou execução.
- O script antigo do ZIP continua sendo histórico. Seu ID inteiro, `tipo=faq` e perfis em texto não representam o formato do carregador atual.
- Nenhuma conexão, carga, busca real ou teste com Qdrant foi executado nesta revisão.

### Fontes no projeto de IA

- `src/etl/populate_qdrant.py` — parser, payload, carregamento incremental e opções da linha de comando.
- `src/services/embedding_service.py` e `src/services/qdrant_service.py` — geração dos vetores e busca.
- `src/agents/graph.py`, `src/api/main.py` e `src/core/config.py` — integração condicional ao chat e configuração.
- `data/FAQ_KNOWLEDGE_BASE.md` — fonte documental das FAQs.
- `requirements-optional.txt` — dependências opcionais.

## Redis

### Finalidade identificada no código

No repositório de IA, o Redis tem três usos identificados: guardar um ponteiro temporário da sessão de cada usuário, coordenar o processamento de mensagens da mesma sessão entre réplicas e consultar rankings de moradores e torres. O serviço de ranking descreve o Redis como uma projeção de leitura e o PostgreSQL como fonte oficial dos pontos. Fontes: `src/services/session_service.py:75-89,135-143,177-179`, `src/services/session_lock.py:1-29,43-58,108-164` e `src/services/ranking_service.py:17-18,23-62`.

### Configuração e estruturas encontradas

O cliente assíncrono é criado a partir de `REDIS_URL`, com `decode_responses=True` e tempo limite de conexão configurável. O valor padrão de desenvolvimento é `redis://localhost:6379/0`; o prazo padrão do ponteiro de sessão é de 1.800 segundos (30 minutos). Esses valores vêm da configuração do aplicativo e não demonstram que exista uma instância ativa. Fontes: `src/database/redis.py:12-21` e `src/core/config.py:69-74,155`.

| Padrão da chave | Estrutura Redis | Conteúdo e uso | Expiração observada no código |
| --- | --- | --- | --- |
| `session:ptr:<usuario_id>` | String | Guarda o `session_id` da sessão criada para o usuário. É regravada quando uma mensagem é adicionada e consultada ao fechar a sessão para apagar apenas o ponteiro correspondente. | `SET ... EX` com `SESSION_TTL_SECONDS`; padrão de 1.800 segundos. |
| `session:lock:<session_id>` | String | Guarda um token aleatório enquanto uma mensagem da sessão é processada; impede que duas réplicas processem a mesma sessão ao mesmo tempo. | `SET ... NX PX` com prazo padrão de 30 segundos, renovado durante o processamento; liberação por comparação do token em script Lua. |
| `ranking:moradores:condominio:<condominio_id>:ciclo:<ciclo_id>` | Sorted Set esperado pelas leituras | Membros identificados por string; pontuações lidas como números. A posição de um morador é consultada pelo seu `usuario_id`. | Não foi encontrada definição de expiração neste repositório. |
| `ranking:torres:condominio:<condominio_id>:ciclo:<ciclo_id>` | Sorted Set esperado pelas leituras | Membros e pontuações usados na listagem das torres; o serviço devolve o identificador do membro como string. | Não foi encontrada definição de expiração neste repositório. |

Fontes da tabela: `src/services/session_service.py:135-143,197,343-345`, `src/services/session_lock.py:34-58,108-164`, `src/core/config.py:68-73,159-162` e `src/services/ranking_service.py:23-38,50-62`. O tipo *Sorted Set* é inferido dos comandos `ZREVRANGE`, `ZSCORE` e `ZREVRANK`; nenhuma chave foi inspecionada no servidor.

### Exemplo fictício da estrutura e do uso

```text
session:ptr:42  →  "e1a2b3c4-..."          (String; expira após 1.800 s, no padrão)

ranking:moradores:condominio:7:ciclo:3     (Sorted Set esperado)
  membro "18"  →  1.380 pontos
  membro "42"  →  1.250 pontos
```

Ao consultar `/api/v1/rankings/moradores?ciclo_id=3&condominio_id=7`, o serviço leria os maiores escores com `ZREVRANGE` e devolveria posição, identificador e pontuação. `/api/v1/rankings/me` usaria `ZSCORE` e `ZREVRANK` para encontrar os pontos e a posição do usuário autenticado. O exemplo usa dados inventados e mostra o comportamento previsto pelo código; não representa dados existentes no Redis. Fontes: `src/api/routes/ranking.py:26-38,56-67` e `src/services/ranking_service.py:27-40,50-62`.

### Limites da verificação

- A busca no código Python deste repositório não encontrou rotina que grave ou atualize os *Sorted Sets* do ranking (`ZADD` ou `ZINCRBY`). Assim, não foi possível confirmar a origem dos pontos, a frequência de atualização nem a expiração dos rankings. Isso não exclui uma rotina em outro serviço. Fonte da leitura: `src/services/ranking_service.py:23-62`.
- O ponteiro `session:ptr` é escrito e removido, mas `resolve_session()` não o consulta para retomar automaticamente uma conversa: sem `session_id`, cria outra sessão. Fontes: `src/services/session_service.py:149,170-171,204,346-348`.
- Se o cliente Redis estiver indisponível, as rotas de ranking retornam HTTP 503. O serviço de sessões pode mudar para armazenamento em memória quando a inicialização do MongoDB ou Redis falha e a configuração permite o fallback. Fontes: `src/services/ranking_service.py:27-40`, `src/api/routes/ranking.py:26-38` e `src/services/session_service.py:102-117`.
- O teste de integração real do Redis cobre conexão e operações simples de `SET`, `GET` e remoção quando `TEST_REDIS_URL` está definido; ele não comprova a carga dos rankings. Nenhum teste ou conexão ao Redis foi executado nesta revisão. Fonte: `tests/integration/test_redis_real.py:14-25`.
- O esquema do populador PostgreSQL define `tb_movimentacoes_pontos` como histórico oficial de créditos, estornos e restaurações e inclui campos de controle da sincronização com Redis. O populador insere eventos fictícios e simula o estado dessas colunas, mas não escreve os rankings no Redis. A rotina real de projeção do ledger para as chaves `ranking:*` continua não localizada. Fontes: `sql/ecociente_schema.sql:529-601` e `src/utils/database.py:808-891` do projeto `md-populador-pgsql`; `src/services/ranking_service.py:23-62` do projeto de IA.

### Fontes consultadas

- `src/database/redis.py` e `src/core/config.py` — cliente, URL, tempo limite e prazo padrão.
- `src/services/session_service.py` — criação, atualização e encerramento da sessão.
- `src/services/session_lock.py` — lock distribuído das sessões.
- `src/services/ranking_service.py`, `src/api/routes/ranking.py` e `src/api/schemas/ranking.py` — formato das chaves, comandos de leitura e respostas da API.
- `tests/integration/test_redis_real.py` — alcance do teste de integração disponível.
- `sql/ecociente_schema.sql` e `src/utils/database.py` do projeto `md-populador-pgsql` — ledger de pontos e simulação da sincronização.

## Neo4j

### Finalidade no sistema

O Neo4j guarda uma projeção em grafo de entidades e vínculos extraídos do PostgreSQL. O ETL lê tabelas relacionais e cria ou atualiza nós e relações com `MERGE`. O agente `grafo` dispõe de ferramentas para percorrer esses vínculos, encontrar caminhos entre entidades e listar usuários mais conectados em um condomínio. Essa finalidade está implementada no código; a existência de dados no servidor não foi verificada. Fontes: `src/etl/populate_graph.py:1-40,459-534` e `src/agents/graph_traversal/tools.py:9-20,67-136,205-230`.

### Modelagem encontrada

O vocabulário compartilhado pelo ETL e pelas ferramentas do agente contém sete rótulos de domínio: `Usuario`, `Condominio`, `Torre`, `Cooperativa`, `CategoriaResiduo`, `Curso` e `Postagem`. Cada nó usa `id` como chave de identidade; o ETL prevê restrição de unicidade de `id` por rótulo. Há também o nó técnico `EtlCheckpoint`, que guarda o último sucesso da carga e não integra a lista das entidades de domínio. Fontes: `src/etl/graph_model.py:7-17`, `src/etl/populate_graph.py:221-278,543-568`.

| Relação no grafo | O que representa | Fonte |
| --- | --- | --- |
| `(Usuario)-[:MORA_EM]->(Condominio)` e `(Usuario)-[:PERTENCE_A]->(Condominio)` | Moradia e vínculo aprovado/ativo do usuário com o condomínio. | `src/etl/populate_graph.py:281-331` |
| `(Torre)-[:PERTENCE_A]->(Condominio)` | Torre do condomínio. | `src/etl/populate_graph.py:333-336` |
| `(Cooperativa)-[:REPRESENTADA_POR]->(Usuario)` | Usuário representante da cooperativa. | `src/etl/populate_graph.py:338-345` |
| `(Usuario)-[:CRIOU]->(Postagem)`; `(Postagem)-[:NO_CONDOMINIO]->(Condominio)`, `[:NA_TORRE]->(Torre)` e `[:DA_CATEGORIA]->(CategoriaResiduo)` | Autoria e contexto de uma postagem. | `src/etl/populate_graph.py:348-377` |
| `(Usuario)-[:VALIDOU]->(Postagem)` e `(Usuario)-[:DENUNCIOU]->(Postagem)` | Validação ou denúncia de uma postagem, com propriedades da interação. | `src/etl/populate_graph.py:381-412` |
| `(Usuario)-[:APROVADO_EM]->(Curso)` e `(Usuario)-[:TEM_DIFICULDADE_EM]->(Curso)` | Resultado agregado das tentativas de quiz de um curso. | `src/etl/populate_graph.py:415-427` |
| `(Curso)-[:RECOMENDADO_PARA]->(Usuario)` | Recomendação derivada de dificuldade no curso ou de aprovações de pessoas do mesmo condomínio. | `src/etl/populate_graph.py:430-456` |

O arquivo `src/etl/graph_model.py:19-32` define os tipos de relação aceitos pelas ferramentas. A tabela acima mostra os vínculos com os sentidos usados pelo ETL; não é uma contagem de relações existentes no banco.

### Exemplo fictício de estrutura e travessia

```text
(Usuario {id: 42, nome: "Ana"})-[:PERTENCE_A]->(Condominio {id: 7, nome: "Jardim"})
(Usuario {id: 42})-[:CRIOU]->(Postagem {id: 91})
(Postagem {id: 91})-[:DA_CATEGORIA]->(CategoriaResiduo {id: 3, nome: "Vidro"})
```

Nesse exemplo inventado, uma travessia pode responder quais postagens sobre vidro foram criadas por usuários vinculados ao condomínio. A ferramenta `caminho_relacionamento` consulta o menor caminho entre duas entidades já identificadas; `conexoes_diretas` lista vizinhos até uma profundidade limitada. As ferramentas restringem rótulos e tipos de relação ao vocabulário do ETL e aplicam o escopo do condomínio e do usuário. Fontes: `src/agents/graph_traversal/tools.py:14-20,27-40,67-189`.

### Carga, validação e agendamento definidos

- O modo `full` relê as tabelas; o `incremental` parte do último checkpoint bem-sucedido com uma sobreposição de dez minutos. Sem checkpoint, o incremental executa uma carga completa. O ETL grava o checkpoint apenas depois de concluir os passos. Fonte: `src/etl/populate_graph.py:8-18,471-510,552-575`.
- O modo `full` atualiza também as recomendações derivadas. Com `--prune`, reconcilia nós de postagem e alguns vínculos removidos da origem; a opção é prevista apenas para carga completa. Fontes: `src/etl/populate_graph.py:494-506,591-629`.
- `--validar` compara contagens entre PostgreSQL e Neo4j, executa uma segunda carga completa para verificar idempotência e mede uma carga incremental. É uma rotina disponível, não um resultado de validação obtido nesta revisão. Fontes: `src/etl/validate_graph.py:29-79,87-138` e `src/etl/populate_graph.py:751-776`.
- O manifesto Kubernetes prevê carga incremental a cada 15 minutos e carga completa diária às 03:00 no horário de São Paulo. O serviço opcional `graph-etl` do Docker Compose prevê um loop com incremental a cada 900 segundos e carga completa a cada 24 horas. Arquivos de configuração não comprovam que essas tarefas foram implantadas ou executadas. Fontes: `k8s/graph-etl-cronjobs.yaml:1-90` e `docker-compose.yml:71-85`.

### Conexão e limites da verificação

`src/database/neo4j.py:10-79` cria um driver assíncrono, verifica conectividade quando o serviço é iniciado e executa consultas Cypher. Nesta revisão, não iniciamos esse driver. Assim, não foram confirmados nós, relações, contagens, checkpoint, agendamentos ativos nem respostas reais das ferramentas. As tabelas de origem do PostgreSQL são identificadas no ETL e em `src/etl/validate_graph.py`; a modelagem relacional está resumida na seção PostgreSQL abaixo.

### Fontes no projeto de IA

- `src/etl/graph_model.py` e `src/etl/populate_graph.py` — vocabulário, extração e regras de carga.
- `src/etl/validate_graph.py` — contagens e verificação de idempotência previstas.
- `src/database/neo4j.py` e `src/agents/graph_traversal/tools.py` — conexão e consultas do agente.
- `k8s/graph-etl-cronjobs.yaml` e `docker-compose.yml` — agendamentos declarados.

## PostgreSQL

### Finalidade e alcance da modelagem encontrada

O PostgreSQL reúne os dados relacionais de usuários, condomínios, cooperativas, descartes, coletas, educação, auditoria e pontuação do EcoCiente. Ele também fornece os dados que o ETL do Neo4j transforma em grafo; a tabela `tb_movimentacoes_pontos` é definida como o histórico oficial dos pontos, a partir do qual o ranking em Redis deveria poder ser reconstruído. Fontes: `sql/ecociente_schema.sql:1-15,529-601` do projeto `md-populador-pgsql` e `src/etl/populate_graph.py:1-40` do projeto de IA.

O CSV enviado pelo usuário (`data-1793370859203.csv`) lista **59 tabelas base no esquema `public`**: 50 com prefixo `tb_`, sete `dim_` e duas `fato_`. As 50 `tb_` aparecem como `CREATE TABLE` em `sql/ecociente_schema.sql` do populador. As nove `dim_`/`fato_` correspondem exatamente aos nomes definidos em `EcoCiente_DataMart (3).sql`. O CSV informa nomes e total de tabelas, mas não contém colunas, chaves ou linhas armazenadas: a correspondência de nomes não confirma que a estrutura do servidor seja idêntica à desses arquivos. A comparação foi feita entre arquivos locais, sem conexão ao servidor.

### Estrutura das 50 tabelas `tb_` no esquema do populador

| Área | Tabelas definidas | Finalidade principal | Fonte no SQL |
| --- | --- | --- | --- |
| Tipos e referências (11) | `tb_lkp_tipos_usuarios`, `tb_lkp_tipos_condominios`, `tb_lkp_status_agendamentos`, `tb_lkp_dias_semanas`, `tb_lkp_categorias_residuos`, `tb_lkp_niveis_confianca`, `tb_lkp_status_validacoes_postagens`, `tb_lkp_tipos_votos_postagens`, `tb_lkp_motivos_denuncia`, `tb_lkp_tipos_eventos_auditados`, `tb_lkp_tipos_operacoes_auditoria` | Valores de domínio, categorias, status, níveis de confiança e tipos de auditoria. | `sql/ecociente_schema.sql:15-97` |
| Endereços e pessoas (5) | `tb_enderecos`, `tb_usuarios`, `tb_sindicos`, `tb_telefones`, `tb_notificacoes` | Cadastro e comunicação com usuários. | `sql/ecociente_schema.sql:98-155` |
| Condomínios (3) | `tb_condominios`, `tb_torres`, `tb_moradores` | Estrutura física e moradia. | `sql/ecociente_schema.sql:156-197` |
| Cooperativas e pontos de coleta (4) | `tb_cooperativas`, `tb_pontos_coletas`, `tb_rel_cooperativas_categorias_materiais`, `tb_rel_pontos_coletas_categorias` | Cooperativas, locais de entrega e materiais aceitos. | `sql/ecociente_schema.sql:198-246` |
| Vínculo com condomínio (1) | `tb_rel_usuarios_condominios` | Associação e aprovação de usuários em condomínios, com dados de confiança. | `sql/ecociente_schema.sql:247-279` |
| Descartes e moderação (2) | `tb_postagens`, `tb_rel_votos_postagens` | Postagens de descarte e votos de aprovação ou denúncia. | `sql/ecociente_schema.sql:280-341` |
| Coletas (4) | `tb_agendamentos_coletas`, `tb_visitas_coletas`, `tb_avaliacoes_visitas_coletas`, `tb_rel_recorrencias_agendamentos` | Solicitação, visita, avaliação e recorrência da coleta. | `sql/ecociente_schema.sql:342-399` |
| Educação (8) | `tb_cursos`, `tb_aulas`, `tb_quizzes`, `tb_perguntas_quiz`, `tb_alternativas_quiz`, `tb_tentativas_quiz`, `tb_rel_respostas_tentativas_quiz`, `tb_rel_usuarios_cursos` | Trilhas, conteúdo educacional e resultados de quiz. | `sql/ecociente_schema.sql:400-501` |
| Autenticação e pontos (2) | `tb_autenticacoes_api`, `tb_movimentacoes_pontos` | Tokens de API e histórico oficial de pontuação. | `sql/ecociente_schema.sql:502-681` |
| Auditoria (4) | `tb_log_auditoria`, `tb_log_auditoria_postagens`, `tb_log_auditoria_agendamentos_coletas`, `tb_log_auditoria_usuarios_condominios` | Registro de eventos e alterações relevantes. | `sql/ecociente_schema.sql:682-788` |
| Atividade e recuperação (3) | `tb_atividades_diarias_usuarios`, `tb_metricas_dau`, `tb_recuperacoes_senha` | Atividade diária, métricas de uso e recuperação de senha. | `sql/ecociente_schema.sql:2105-2183` |
| Migração (1) | `tb_migracao_ids_map` | Correspondência de IDs legados com IDs novos. | `sql/ecociente_schema.sql:2298-2320` |
| Conversas entre organizações (2) | `tb_conversas`, `tb_mensagens_conversas` | Chat entre cooperativa e condomínio. | `sql/ecociente_schema.sql:2321-2451` |

Os números entre parênteses somam 50. O SQL declara chaves primárias, chaves estrangeiras, restrições e regras de negócio; a tabela acima resume a finalidade dos grupos e não substitui o detalhamento de cada coluna. O mesmo arquivo também define funções, procedimentos, gatilhos e *views*, que não entram na contagem de tabelas base do CSV. Fonte: `sql/ecociente_schema.sql` do populador.

### Estrutura das 7 dimensões e 2 fatos do Data Mart

O arquivo `EcoCiente_DataMart (3).sql:1-19,39-210` define um **modelo estrela** para análise. As dimensões descrevem tempo, pessoas, organizações, categorias e status; os fatos registram uma linha por postagem ou por visita de coleta. As chaves `sk_*` identificam linhas das dimensões e são referenciadas pelos fatos. Esta é a estrutura **declarada no arquivo recebido**, não uma introspecção das tabelas existentes no servidor.

| Tabela | Campos declarados | Origem e finalidade |
| --- | --- | --- |
| `dim_tempo` | `sk_tempo` (PK), `data_completa` (única), `ano`, `trimestre`, `mes`, `nome_mes`, `dia`, `dia_semana_numero`, `nome_dia_semana`, `is_fim_de_semana` | Datas dos eventos; compartilhada pelos dois fatos. |
| `dim_usuario` | `sk_usuario` (PK), `id_usuario` (único), `nome_usuario`, `email_usuario`, `tipo_usuario`, `ativo`, `carregado_em` | `tb_usuarios` e `tb_lkp_tipos_usuarios`. |
| `dim_condominio` | `sk_condominio` (PK), `id_condominio` (único), `nome_condominio`, `tipo_condominio`, `cidade`, `estado`, `ativo`, `carregado_em` | `tb_condominios`, tipo e endereço. |
| `dim_cooperativa` | `sk_cooperativa` (PK), `id_cooperativa` (único), `nome_cooperativa`, `cidade`, `estado`, `carregado_em` | `tb_cooperativas` e endereço. |
| `dim_categoria_residuo` | `sk_categoria` (PK), `id_categoria` (único), `nome_categoria`, `permite_reciclagem`, `pontos_base`, `limite_pontos_ciclo`, `carregado_em` | `tb_lkp_categorias_residuos`; o campo de limite apresenta divergência com o esquema do populador, descrita abaixo. |
| `dim_status_postagem` | `sk_status_postagem` (PK), `id_status_validacao` (único), `codigo` (único), `descricao` | `tb_lkp_status_validacoes_postagens`. |
| `dim_status_agendamento` | `sk_status_agendamento` (PK), `id_status` (único), `nome_status` | `tb_lkp_status_agendamentos`. |
| `fato_postagens` | `sk_fato_postagem` (PK), `id_postagem` (único), `sk_tempo`, `sk_usuario`, `sk_condominio`, `sk_categoria`, `sk_status_postagem` (FKs), `qtd_postagens`, `foi_aprovada`, `pontos_base_categoria` | Uma linha por `tb_postagens`; permite análises por data, usuário, condomínio, categoria e status. |
| `fato_coletas` | `sk_fato_coleta` (PK), `id_visita_coleta` (único), `sk_tempo`, `sk_condominio`, `sk_cooperativa`, `sk_status_agendamento` (FKs), `foi_realizada`, `houve_confirmacao`, `qtd_visitas` | Uma linha por `tb_visitas_coletas`, vinculada ao agendamento; permite análises por data, condomínio, cooperativa e status. |

Fontes da tabela: `EcoCiente_DataMart (3).sql:39-210,319-490`. As colunas `qtd_postagens` e `qtd_visitas` recebem `1` em cada linha; `pontos_base_categoria` vem do cadastro da categoria, não do saldo individual do ledger `tb_movimentacoes_pontos`. Fonte: `EcoCiente_DataMart (3).sql:425-490`.

**Exemplo fictício de uso analítico:** uma consulta pode agrupar `fato_postagens` por `dim_tempo.mes` e `dim_categoria_residuo.nome_categoria`, somar `qtd_postagens` e contar as linhas com `foi_aprovada=true` para comparar volume e aprovação por mês e material. Esse uso decorre das chaves e medidas declaradas; nenhuma consulta ao Data Mart real foi feita. Fontes: `EcoCiente_DataMart (3).sql:142-177,425-458,598-615`.

O script define `sp_carga_datamart()` para recarregar as dimensões e fatos a partir das tabelas `tb_*`. Ele começa com `DROP TABLE IF EXISTS ... CASCADE` para as nove tabelas, define a rotina de recarga com `TRUNCATE` e contém `CALL sp_carga_datamart()` no próprio arquivo. **Não foi executado nesta revisão.** Fonte: `EcoCiente_DataMart (3).sql:20-33,214-250,557-564`.

### Exemplo de modelagem: histórico de pontos

`tb_movimentacoes_pontos` usa `id_movimentacao` como chave primária. Cada linha registra `usuario_id`, origem (`POSTAGEM` ou `QUIZ`), tipo (`CREDITO`, `ESTORNO` ou `RESTAURACAO`), quantidade positiva de `pontos`, instante `ocorrido_em` e `idempotency_key` única. Pode apontar para uma postagem ou tentativa de quiz e, no caso de estorno/restauração, para a movimentação de crédito original. Há campos de acompanhamento da projeção para Redis: `redis_sincronizado`, `redis_sincronizado_em`, `tentativas_sync_redis` e `ultimo_erro_redis`. Fontes: `sql/ecociente_schema.sql:529-601`.

Exemplo **fictício** de três eventos para o mesmo crédito de postagem:

```text
1. CREDITO      +12 pontos  → postagem 91
2. ESTORNO      -12 pontos  → referência ao crédito 1
3. RESTAURACAO  +12 pontos  → referência ao crédito 1
Saldo desses eventos: 12 pontos
```

Os valores negativos no exemplo indicam o efeito no saldo; a coluna `pontos` armazena valores positivos e o tipo da movimentação determina a soma ou subtração. O README do populador usa esse histórico para calcular saldos em uma consulta de ranking. Fontes: `sql/ecociente_schema.sql:566-601` e `README.md:262-270` do populador.

### Papel do populador e limites da verificação

- `src/main.py` e `src/utils/database.py` do populador geram uma massa fictícia, inclusive eventos de crédito, estorno e restauração. A rotina `registrar_ledger_pontos()` atualiza os campos de sincronização com valores simulados; não há escrita real nas chaves de ranking do Redis nesse projeto. Fontes: `src/main.py:327-334`, `src/utils/database.py:808-891` e `requirements.txt:1-2`.
- O populador **não cria as tabelas** ao ser executado: ele pressupõe a aplicação prévia do SQL. Sua execução normal apaga dados das tabelas de negócio antes de inserir a nova massa. Por isso, nenhum comando do populador foi executado nesta revisão. Fontes: `README.md:39-50,119-121` e `src/utils/database.py:1518-1562`.
- A frase inicial do `README.md` que menciona 46 tabelas está desatualizada perante as 50 declarações `CREATE TABLE` do SQL e as 59 tabelas listadas no CSV. A documentação usa a contagem obtida dos arquivos, sem tratar o README como prova do estado do servidor.
- O arquivo recebido define exatamente as sete `dim_` e duas `fato_` do CSV, mas há **divergência de coluna** entre suas fontes: `sp_carga_datamart()` lê `tb_lkp_categorias_residuos.limite_pontos_ciclo`, enquanto `sql/ecociente_schema.sql` do populador define `limite_pontos_diario` nessa tabela e não define `limite_pontos_ciclo`. Se o banco seguir o esquema do populador, essa instrução da carga falharia. Não foi verificado qual coluna existe no servidor. Fontes: `EcoCiente_DataMart (3).sql:103-112,381-397` e `sql/ecociente_schema.sql:40-52` do populador.
- O cabeçalho do Data Mart diz que não há fato de pontuação porque o OLTP não teria histórico persistente de pontos. Essa justificativa está desatualizada perante `tb_movimentacoes_pontos`, definida no esquema do populador. O Data Mart recebido continua tendo apenas `fato_postagens` e `fato_coletas`; seu `pontos_base_categoria` não representa o saldo efetivo do ledger. Fontes: `EcoCiente_DataMart (3).sql:8-18,142-164,425-458` e `sql/ecociente_schema.sql:529-601` do populador.
- Não foram consultados dados, volumes de linhas, restrições efetivamente implantadas nem funcionamento das rotinas no PostgreSQL real. O CSV enviado comprova apenas o resultado da consulta de listagem que o usuário executou.

### Fontes consultadas

- `C:\Users\dominicvitorino-ieg\Downloads\data-1793370859203.csv` — lista de 59 tabelas `public` fornecida pelo usuário.
- `C:\Users\dominicvitorino-ieg\OneDrive - Instituto J&F\Área de Trabalho\Escola\2 ano\BD (Grilo)\Inter_populador\md-populador-pgsql\sql\ecociente_schema.sql` — estrutura SQL das 50 tabelas `tb_` e regras de negócio.
- `src/main.py`, `src/utils/database.py`, `README.md` e `requirements.txt` do projeto `md-populador-pgsql` — comportamento e alcance do populador.
- `C:\Users\dominicvitorino-ieg\Downloads\EcoCiente_DataMart (3).sql` — DDL, grão dos fatos, chaves e rotina de carga das nove tabelas analíticas.
- `src/etl/populate_graph.py` e `src/services/ranking_service.py` do projeto de IA — leituras derivadas de PostgreSQL e Redis.
