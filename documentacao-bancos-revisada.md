# Como os bancos de dados entram no EcoCiente

Esta documentação reúne o que encontramos no código do EcoCiente e nos esquemas de banco disponíveis. A análise foi feita sem conexão aos serviços. Quando um processo está implementado, mas ainda não foi testado com dados reais, isso aparece no texto.

## MongoDB

O MongoDB guarda as conversas com a Eko em duas coleções. `sessoes` mantém o histórico da conversa em andamento. `memoria_usuarios` guarda um resumo por pessoa, que pode ser usado em conversas futuras. O nome padrão do banco é `ecociente`, configurável por `MONGODB_DATABASE`.

### Sessões de conversa

A aplicação monta os documentos de `sessoes` com os seguintes campos:

| Campo | Tipo | O que guarda |
| --- | --- | --- |
| `_id` | Identificador do MongoDB | Identificação interna; o serviço omite esse campo ao devolver a sessão. |
| `session_id` | UUID em texto | Identificador usado pela aplicação para retomar a conversa. |
| `usuario_id` | Inteiro | Dono da sessão. |
| `status` | Texto | Começa como `active`. |
| `created_at` | Data e hora UTC | Criação da sessão. |
| `updated_at` | Data e hora UTC | Última atualização. |
| `expira_em` | Data e hora UTC | Momento a partir do qual a sessão pode expirar. |
| `ultima_rota` | Texto ou `null` | Última rota escolhida pela Eko. |
| `memory_summary` | Texto | Resumo das mensagens antigas. |
| `memory_revision` | Inteiro | Versão do resumo, usada para evitar gravações concorrentes. |
| `messages` | Lista de documentos | Mensagens do usuário e da Eko. |
| `memoria_longa_ate` | Data e hora UTC, opcional | Marca até qual mensagem a memória entre conversas já foi consolidada. |

Cada mensagem em `messages` tem `id`, `role`, `content` e `created_at`. O papel pode ser `user` ou `assistant`. Se uma mensagem for barrada pelo controle de entrada, o campo opcional `bloqueada` impede que ela entre na memória entre conversas. As mensagens são acrescentadas à lista com `$push`.

`session_id` tem índice único. `expira_em` tem índice TTL com `expireAfterSeconds=0`. O prazo padrão é de 1.800 segundos, ou 30 minutos, e é renovado quando novas mensagens entram ou a memória da sessão é compactada. Ao encerrar uma sessão, a API apaga seu documento e devolve `closed` como resultado; ela não grava `closed` no campo `status`.

Este documento é um exemplo fictício. As datas aparecem como texto para facilitar a leitura; a aplicação grava datas no MongoDB. O `_id` foi omitido e `memoria_longa_ate` ainda não existe porque a sessão do exemplo não passou pela consolidação.

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

Uma pessoa autenticada envia uma pergunta sem `session_id`. A aplicação cria a sessão, grava a pergunta e depois a resposta. Na próxima pergunta, o mesmo `session_id` permite recuperar o histórico. Quando a conversa passa de 20 mensagens, o fluxo normal pode resumir as antigas em `memory_summary` e manter as 6 mais recentes em `messages`. `memory_revision` controla gravações concorrentes desse resumo. No modo `FAST_LOCAL_MODE`, essa compactação não é acionada.

### Memória entre conversas

`memoria_usuarios` mantém um documento por pessoa, sem TTL definido no código:

| Campo | Tipo | O que guarda |
| --- | --- | --- |
| `_id` | Identificador do MongoDB | Identificação interna, omitida na leitura do serviço. |
| `usuario_id` | Inteiro | Dono da memória; possui índice único. |
| `texto` | Texto | Resumo consolidado do que o usuário contou. |
| `revision` | Inteiro | Versão usada para evitar que uma gravação antiga substitua uma mais nova. |
| `updated_at` | Data e hora UTC | Última alteração. |

O primeiro resumo cria o documento. As atualizações seguintes só são aceitas quando `revision` ainda tem o valor esperado. Para apagar essa memória, o serviço esvazia `texto` e aumenta `revision`; o documento permanece. Um exemplo fictício:

```json
{
  "usuario_id": 42,
  "texto": "- prefere respostas curtas\n- tem uma composteira em casa",
  "revision": 1,
  "updated_at": "2026-10-29T15:31:00Z"
}
```

Quando a memória entre conversas está habilitada, a Eko lê `texto` para compor o contexto. Ao encerrar a sessão, a API tenta consolidar as mensagens ainda pendentes antes de apagar o documento de `sessoes`. A configuração prevê consolidação a cada certo número de turnos, mas, nas chamadas encontradas, o método de consolidação é acionado apenas no encerramento. Ainda não há evidência de que ele rode depois de cada resposta.

Se MongoDB ou Redis falhar na inicialização e o fallback estiver habilitado, as sessões passam a ficar na memória do processo, sem persistência no MongoDB. O estado de saúde pode indicar `memory_fallback`. Há um teste de integração com MongoDB real que só roda quando `TEST_MONGODB_URI` está configurado; sua presença não comprova execução neste ambiente.

Um texto de instruções do agente ainda usa o nome `MongoDB.memoria_longo_prazo.resumo_consolidado`. A implementação usa `memoria_usuarios.texto`. O texto de instruções não define uma terceira coleção. Não consultamos o servidor para confirmar dados existentes ou índices efetivamente criados.

## Qdrant

O Qdrant foi preparado para buscar perguntas frequentes por semelhança de significado. A pergunta vira um vetor; a busca encontra FAQs próximas e a Eko pode devolver a resposta canônica do melhor resultado, sem pedir a um modelo de linguagem que a reescreva. Esse caminho é usado quando `FAQ_BACKEND=qdrant`. O valor padrão da configuração ainda é `rag`.

Em 29/10/2026, o usuário informou que o painel consultado não mostrava nenhuma coleção. Não houve nova consulta ao servidor depois disso. O código já define a carga e a busca, mas não confirma se a coleção existe, se tem pontos ou se o modo Qdrant está ativo no ambiente.

### Como uma FAQ vira um ponto

O carregador lê as perguntas frequentes canônicas. Cada entrada precisa de um identificador como `FAQ-001`, título, intenção, perfis relacionados e resposta canônica; palavras-chave são opcionais. Uma entrada malformada ou um identificador duplicado interrompe a carga.

| Elemento | Estrutura definida |
| --- | --- |
| Coleção | Nome configurável, com `faq` como padrão. Cada ponto tem um vetor sem nome. |
| ID do ponto | UUID versão 5 derivado de um namespace fixo e do `faq_id`. A mesma FAQ recebe o mesmo ID em novas cargas. |
| Texto enviado ao modelo | Título, resposta canônica e, quando existem, palavras-chave. |
| Modelo | `intfloat/multilingual-e5-large` por padrão. Para modelos da família E5, os documentos recebem o prefixo `passage: ` e as perguntas, `query: `. |
| Dimensão | Tamanho do vetor gerado pelo modelo; não há número fixo definido no carregador. |
| Distância | Cosseno (`COSINE`). |
| Payload | `faq_id`, `titulo`, `intencao`, `perfis_relacionados`, `resposta_canonica`, `palavras_chave`, `tipo`, `categoria`, `perfis_texto`, `embedding_model` e `content_hash`. |

`perfis_relacionados` e `palavras_chave` são listas. `tipo` recebe `faq_canonica`, com índice `KEYWORD`. A pontuação de similaridade, chamada `score`, vem do resultado da busca; ela não é gravada no payload.

O ponto abaixo é fictício. O UUID, o hash e o vetor numérico dependem da execução e foram omitidos.

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

### Carga e busca

O modo `--dry-run` valida as FAQs e mostra um resumo sem criar o cliente Qdrant ou gerar vetores. A carga normal cria a coleção, se necessário, e grava FAQs novas ou alteradas com `upsert`. `content_hash` evita recalcular vetores quando o conteúdo não mudou. Como o ID é determinístico, uma nova carga não duplica a FAQ. Por padrão, FAQs canônicas que saíram da base são removidas da coleção; `--manter-ausentes` desativa a remoção.

Ao trocar o modelo ou precisar mudar a dimensão, `--recriar` apaga e recria a coleção. O carregador gera os novos vetores antes de apagar a coleção anterior.

Na consulta, o serviço pede até três resultados por padrão, junto com seus payloads. Ele aceita a primeira resposta com similaridade mínima de `0,80`, conteúdo preenchido e perfil compatível com o usuário. Se não houver resultado adequado, ou se a busca falhar, o fluxo antigo de RAG com modelo de linguagem só entra quando `FAQ_LLM_FALLBACK=true`.

As bibliotecas `qdrant-client` e `fastembed` são dependências opcionais declaradas pelo projeto; isso não confirma que estejam instaladas no ambiente. Um indexador antigo usava IDs inteiros, `tipo=faq` e perfis em texto. Esses detalhes não descrevem o carregador atual. Não executamos carga, busca ou teste com Qdrant; a dimensão efetiva, a quantidade de pontos e a qualidade das respostas seguem sem verificação.

## Redis

O Redis aparece em três partes do sistema: um ponteiro para a sessão de cada usuário, um bloqueio temporário que evita respostas simultâneas na mesma conversa e a leitura dos rankings de moradores e torres. Para os pontos, o PostgreSQL é a fonte oficial; o Redis foi desenhado como uma projeção de leitura.

O cliente usa `REDIS_URL`, decodifica respostas como texto (`decode_responses=True`) e tem tempo limite de conexão configurável. O endereço padrão de desenvolvimento é `redis://localhost:6379/0`. Esses valores descrevem a configuração, não uma instância que tenhamos confirmado em execução.

| Chave | Tipo esperado | Conteúdo e funcionamento | Prazo encontrado no código |
| --- | --- | --- | --- |
| `session:ptr:<usuario_id>` | String | Guarda o `session_id`. É regravada quando entra uma mensagem e removida ao fechar a sessão, se ainda apontar para ela. | 1.800 segundos por padrão, com `SET ... EX`. |
| `session:lock:<session_id>` | String | Guarda um token aleatório enquanto uma mensagem é processada. `SET ... NX PX` impede que duas réplicas assumam a mesma sessão. A renovação e a liberação comparam o token por script Lua. | 30 segundos por padrão, renovados durante o processamento. |
| `ranking:moradores:condominio:<condominio_id>:ciclo:<ciclo_id>` | Sorted Set | Membros identificados por texto e pontuações numéricas. Permite consultar a posição do próprio `usuario_id`. | Nenhuma regra de expiração encontrada. |
| `ranking:torres:condominio:<condominio_id>:ciclo:<ciclo_id>` | Sorted Set | Membros e pontuações das torres, devolvidos na listagem do ranking. | Nenhuma regra de expiração encontrada. |

O tipo *Sorted Set* dos rankings é deduzido dos comandos de leitura `ZREVRANGE`, `ZSCORE` e `ZREVRANK`. Não inspecionamos as chaves no servidor.

Exemplo fictício:

```text
session:ptr:42  →  "e1a2b3c4-..."          (String; prazo padrão de 1.800 s)

ranking:moradores:condominio:7:ciclo:3     (Sorted Set esperado)
  membro "18"  →  1.380 pontos
  membro "42"  →  1.250 pontos
```

Uma consulta a `/api/v1/rankings/moradores?ciclo_id=3&condominio_id=7` leria os maiores escores com `ZREVRANGE` e devolveria identificador, pontos e posição. `/api/v1/rankings/me` usaria `ZSCORE` e `ZREVRANK` para obter os pontos e a posição da pessoa autenticada. Os valores do exemplo não vieram do Redis.

Ainda não localizamos, no projeto de IA ou no populador PostgreSQL, a rotina que grava ou atualiza os *Sorted Sets* do ranking com operações como `ZADD` ou `ZINCRBY`. Por isso, não sabemos a frequência da atualização nem a expiração real dessas chaves. A rotina pode estar em outro serviço. O ponteiro `session:ptr` também não é usado para retomar automaticamente a conversa: sem `session_id` na requisição, a aplicação cria outra sessão.

Quando Redis está indisponível, as rotas de ranking respondem HTTP 503. As sessões podem passar para a memória do processo se a inicialização de MongoDB ou Redis falhar e o fallback estiver habilitado. O teste de integração disponível cobre conexão, `SET`, `GET` e remoção quando `TEST_REDIS_URL` está configurado, mas não a montagem do ranking.

O esquema PostgreSQL traz um histórico oficial de créditos, estornos e restaurações em `tb_movimentacoes_pontos`, com campos para acompanhar a sincronização com Redis. O populador cria eventos fictícios e preenche esses campos com estados simulados. Ele não escreve os pontos nas chaves `ranking:*`. Não executamos testes nem conexão ao Redis nesta revisão.

## Neo4j

O Neo4j representa em grafo entidades que já existem no PostgreSQL. Uma carga lê as tabelas relacionais e cria ou atualiza nós e vínculos com `MERGE`. O agente de grafo pode procurar caminhos entre entidades, listar conexões e identificar usuários mais conectados em um condomínio. Não verificamos se o servidor tem dados carregados.

### Nós e relações

O modelo de domínio define sete tipos de nó: `Usuario`, `Condominio`, `Torre`, `Cooperativa`, `CategoriaResiduo`, `Curso` e `Postagem`. Cada nó usa `id` como identificador, com uma restrição de unicidade prevista por tipo. A carga mantém ainda o nó técnico `EtlCheckpoint`, usado para lembrar quando terminou com sucesso.

| Relação | O que liga |
| --- | --- |
| `(Usuario)-[:MORA_EM]->(Condominio)` e `(Usuario)-[:PERTENCE_A]->(Condominio)` | Moradia e vínculo aprovado e ativo de uma pessoa com o condomínio. |
| `(Torre)-[:PERTENCE_A]->(Condominio)` | Torre e condomínio ao qual ela pertence. |
| `(Cooperativa)-[:REPRESENTADA_POR]->(Usuario)` | Cooperativa e usuário que a representa. |
| `(Usuario)-[:CRIOU]->(Postagem)` | Autor e postagem. |
| `(Postagem)-[:NO_CONDOMINIO]->(Condominio)`, `[:NA_TORRE]->(Torre)` e `[:DA_CATEGORIA]->(CategoriaResiduo)` | Local e categoria da postagem. |
| `(Usuario)-[:VALIDOU]->(Postagem)` e `(Usuario)-[:DENUNCIOU]->(Postagem)` | Validação ou denúncia, com propriedades da interação. |
| `(Usuario)-[:APROVADO_EM]->(Curso)` e `(Usuario)-[:TEM_DIFICULDADE_EM]->(Curso)` | Resultado agregado das tentativas de quiz. |
| `(Curso)-[:RECOMENDADO_PARA]->(Usuario)` | Recomendação por dificuldade no curso ou por aprovações de pessoas do mesmo condomínio. |

Um exemplo inventado mostra como uma pergunta pode atravessar mais de um vínculo:

```text
(Usuario {id: 42, nome: "Ana"})-[:PERTENCE_A]->(Condominio {id: 7, nome: "Jardim"})
(Usuario {id: 42})-[:CRIOU]->(Postagem {id: 91})
(Postagem {id: 91})-[:DA_CATEGORIA]->(CategoriaResiduo {id: 3, nome: "Vidro"})
```

Essas relações permitem investigar postagens de vidro feitas por pessoas vinculadas a um condomínio. A ferramenta `caminho_relacionamento` procura o menor caminho entre duas entidades identificadas; `conexoes_diretas` lista vizinhos até uma profundidade limitada. As ferramentas aceitam apenas os tipos de nó e relação do modelo e aplicam o escopo do condomínio e do usuário.

### Como o grafo é atualizado

A carga `full` relê as tabelas do PostgreSQL. A `incremental` parte do último checkpoint bem-sucedido e inclui uma sobreposição de dez minutos para captar alterações que terminaram depois da execução anterior. Sem checkpoint, a carga incremental passa a ser completa. O checkpoint só é gravado ao fim de uma execução sem erro.

As recomendações derivadas são recalculadas na carga completa. A opção `--prune`, também restrita à carga completa, reconcilia postagens e alguns vínculos removidos da origem. A opção `--validar` compara contagens entre PostgreSQL e Neo4j, executa outra carga completa para conferir se `MERGE` evita duplicações e mede uma carga incremental. Não executamos essa validação.

O agendamento previsto em Kubernetes roda a carga incremental a cada 15 minutos e a completa todos os dias às 03:00, no horário de São Paulo. O serviço opcional de Docker Compose prevê incrementais a cada 900 segundos e uma carga completa a cada 24 horas. São configurações encontradas nos arquivos; não há confirmação de implantação ou execução.

O serviço usa um driver assíncrono para se conectar e executar Cypher. Não iniciamos essa conexão. Permanecem sem confirmação as contagens de nós e relações, o checkpoint, os agendamentos ativos e as respostas reais do agente.

## PostgreSQL

O PostgreSQL guarda os dados relacionais do EcoCiente: pessoas, condomínios, cooperativas, descartes, coletas, educação, auditoria e pontos. Também fornece as tabelas que alimentam o grafo Neo4j. O histórico oficial de pontos está em `tb_movimentacoes_pontos`; o ranking em Redis foi pensado para ser reconstruído a partir dele.

Uma listagem enviada pelo usuário mostrou 59 tabelas base no esquema `public`: 50 com prefixo `tb_`, sete `dim_` e duas `fato_`. As 50 `tb_` aparecem no esquema do populador. Um segundo script define exatamente as nove tabelas analíticas da listagem. A correspondência dos nomes não confirma que as colunas, chaves e restrições do servidor sejam idênticas às dos scripts; não inspecionamos o banco.

### As 50 tabelas operacionais

| Área | Tabelas | Papel no sistema |
| --- | --- | --- |
| Tipos e referências (11) | `tb_lkp_tipos_usuarios`, `tb_lkp_tipos_condominios`, `tb_lkp_status_agendamentos`, `tb_lkp_dias_semanas`, `tb_lkp_categorias_residuos`, `tb_lkp_niveis_confianca`, `tb_lkp_status_validacoes_postagens`, `tb_lkp_tipos_votos_postagens`, `tb_lkp_motivos_denuncia`, `tb_lkp_tipos_eventos_auditados`, `tb_lkp_tipos_operacoes_auditoria` | Tipos, categorias, status, níveis de confiança e tipos de auditoria. |
| Endereços e pessoas (5) | `tb_enderecos`, `tb_usuarios`, `tb_sindicos`, `tb_telefones`, `tb_notificacoes` | Cadastro e comunicação. |
| Condomínios (3) | `tb_condominios`, `tb_torres`, `tb_moradores` | Estrutura física e moradia. |
| Cooperativas e pontos de coleta (4) | `tb_cooperativas`, `tb_pontos_coletas`, `tb_rel_cooperativas_categorias_materiais`, `tb_rel_pontos_coletas_categorias` | Cooperativas, locais de entrega e materiais aceitos. |
| Vínculo com condomínio (1) | `tb_rel_usuarios_condominios` | Associação, aprovação e confiança dos usuários. |
| Descartes e moderação (2) | `tb_postagens`, `tb_rel_votos_postagens` | Postagens e votos de aprovação ou denúncia. |
| Coletas (4) | `tb_agendamentos_coletas`, `tb_visitas_coletas`, `tb_avaliacoes_visitas_coletas`, `tb_rel_recorrencias_agendamentos` | Solicitações, visitas, avaliações e recorrências. |
| Educação (8) | `tb_cursos`, `tb_aulas`, `tb_quizzes`, `tb_perguntas_quiz`, `tb_alternativas_quiz`, `tb_tentativas_quiz`, `tb_rel_respostas_tentativas_quiz`, `tb_rel_usuarios_cursos` | Cursos, aulas e desempenho nos quizzes. |
| Autenticação e pontos (2) | `tb_autenticacoes_api`, `tb_movimentacoes_pontos` | Tokens da API e histórico oficial da pontuação. |
| Auditoria (4) | `tb_log_auditoria`, `tb_log_auditoria_postagens`, `tb_log_auditoria_agendamentos_coletas`, `tb_log_auditoria_usuarios_condominios` | Registro de eventos e alterações. |
| Atividade e recuperação (3) | `tb_atividades_diarias_usuarios`, `tb_metricas_dau`, `tb_recuperacoes_senha` | Atividade diária, métricas de uso e recuperação de senha. |
| Migração (1) | `tb_migracao_ids_map` | Correspondência entre IDs antigos e novos. |
| Conversas entre organizações (2) | `tb_conversas`, `tb_mensagens_conversas` | Chat entre cooperativa e condomínio. |

Os grupos somam 50 tabelas. O esquema também declara chaves primárias e estrangeiras, restrições, funções, procedimentos, gatilhos e *views*. As *views* não entram na contagem das 59 tabelas base. Uma descrição antiga do populador fala em 46 tabelas; a contagem dos comandos de criação do esquema é 50.

### As nove tabelas do Data Mart

O Data Mart usa um modelo estrela. As sete dimensões dão contexto aos dados; os dois fatos registram eventos que podem ser contados e agrupados. As chaves `sk_*` identificam as dimensões e são referenciadas pelos fatos. A tabela mostra o que o script recebido declara, sem afirmar que o servidor esteja com a mesma estrutura.

| Tabela | Campos declarados | Origem e uso |
| --- | --- | --- |
| `dim_tempo` | `sk_tempo` (PK), `data_completa` (única), `ano`, `trimestre`, `mes`, `nome_mes`, `dia`, `dia_semana_numero`, `nome_dia_semana`, `is_fim_de_semana` | Datas dos eventos, compartilhadas pelos dois fatos. |
| `dim_usuario` | `sk_usuario` (PK), `id_usuario` (único), `nome_usuario`, `email_usuario`, `tipo_usuario`, `ativo`, `carregado_em` | Usuários e seus tipos. |
| `dim_condominio` | `sk_condominio` (PK), `id_condominio` (único), `nome_condominio`, `tipo_condominio`, `cidade`, `estado`, `ativo`, `carregado_em` | Condomínios, tipos e endereços. |
| `dim_cooperativa` | `sk_cooperativa` (PK), `id_cooperativa` (único), `nome_cooperativa`, `cidade`, `estado`, `carregado_em` | Cooperativas e endereços. |
| `dim_categoria_residuo` | `sk_categoria` (PK), `id_categoria` (único), `nome_categoria`, `permite_reciclagem`, `pontos_base`, `limite_pontos_ciclo`, `carregado_em` | Categorias de resíduo. Há uma divergência no nome do campo de limite, detalhada abaixo. |
| `dim_status_postagem` | `sk_status_postagem` (PK), `id_status_validacao` (único), `codigo` (único), `descricao` | Estados de validação das postagens. |
| `dim_status_agendamento` | `sk_status_agendamento` (PK), `id_status` (único), `nome_status` | Estados dos agendamentos. |
| `fato_postagens` | `sk_fato_postagem` (PK), `id_postagem` (único), `sk_tempo`, `sk_usuario`, `sk_condominio`, `sk_categoria`, `sk_status_postagem` (FKs), `qtd_postagens`, `foi_aprovada`, `pontos_base_categoria` | Uma linha por postagem. Permite analisar data, pessoa, condomínio, categoria e status. |
| `fato_coletas` | `sk_fato_coleta` (PK), `id_visita_coleta` (único), `sk_tempo`, `sk_condominio`, `sk_cooperativa`, `sk_status_agendamento` (FKs), `foi_realizada`, `houve_confirmacao`, `qtd_visitas` | Uma linha por visita de coleta. Permite analisar data, condomínio, cooperativa e status. |

Cada linha de `fato_postagens` recebe `qtd_postagens=1`; cada visita recebe `qtd_visitas=1`. `pontos_base_categoria` vem do cadastro da categoria, não do saldo de pontos efetivamente concedidos. Por exemplo, seria possível agrupar postagens por mês e material, somar `qtd_postagens` e contar as linhas com `foi_aprovada=true` para comparar volume e aprovação. Não fizemos essa consulta no banco.

O script do Data Mart define `sp_carga_datamart()`, rotina que limpa e recarrega dimensões e fatos a partir das tabelas `tb_*`. O próprio script começa apagando as nove tabelas com `DROP TABLE IF EXISTS ... CASCADE` e inclui `CALL sp_carga_datamart()` para fazer a primeira carga. Não o executamos.

### Histórico oficial de pontos

`tb_movimentacoes_pontos` usa `id_movimentacao` como chave primária. Cada linha registra o usuário, a origem (`POSTAGEM` ou `QUIZ`), o tipo (`CREDITO`, `ESTORNO` ou `RESTAURACAO`), a quantidade positiva de pontos, a data `ocorrido_em` e uma `idempotency_key` única. A linha pode apontar para uma postagem ou tentativa de quiz. Estornos e restaurações apontam para o crédito original. Os campos `redis_sincronizado`, `redis_sincronizado_em`, `tentativas_sync_redis` e `ultimo_erro_redis` acompanham a projeção para Redis.

No exemplo fictício abaixo, os sinais mostram o efeito no saldo. A coluna `pontos` continua positiva; o tipo da movimentação determina se o valor entra ou sai.

```text
1. CREDITO      +12 pontos  → postagem 91
2. ESTORNO      -12 pontos  → referência ao crédito 1
3. RESTAURACAO  +12 pontos  → referência ao crédito 1
Saldo desses eventos: 12 pontos
```

O populador gera eventos fictícios desse tipo. Também simula o estado dos campos de sincronização com Redis, sem atualizar as chaves de ranking. Ele pressupõe que o esquema já exista e, quando executado normalmente, apaga os dados das tabelas de negócio antes de inserir uma nova massa. Não executamos o populador.

### O que ainda precisa ser conferido

A carga do Data Mart lê `tb_lkp_categorias_residuos.limite_pontos_ciclo`, enquanto o esquema do populador declara `limite_pontos_diario` nessa tabela. Se o banco seguir esse esquema, a carga falhará nessa instrução. Ainda não verificamos qual coluna existe no servidor.

O cabeçalho do script do Data Mart afirma que não há um fato de pontuação porque o banco operacional não teria histórico persistente de pontos. Essa justificativa está desatualizada: o esquema do populador já define `tb_movimentacoes_pontos`. O Data Mart recebido continua tendo apenas `fato_postagens` e `fato_coletas`, e `pontos_base_categoria` não substitui o saldo do histórico de pontos.

A listagem enviada informa os nomes das 59 tabelas, mas não seus dados, volumes de linhas nem restrições implantadas. Também não executamos a carga do Data Mart ou as demais rotinas no PostgreSQL real.
