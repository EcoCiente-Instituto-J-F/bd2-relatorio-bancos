# Política de Segurança

Este repositório documenta a estrutura dos bancos de dados do EcoCiente (tabelas, coleções, chaves e esquemas), mas não guarda dados de pessoas reais: os exemplos são fictícios e o relatório foi feito sem conexão aos servidores. Levamos a sério os relatos sobre isso.

## Versões suportadas

Somente o código mais recente do branch `main` recebe correções de segurança. Não há branches de
release mantidos.

| Versão | Suportada |
| --- | --- |
| `main` (mais recente) | Sim |
| Commits antigos, forks e branches pessoais | Não |

## Reportando uma vulnerabilidade

**Não abra issue, pull request ou discussão pública para um problema de segurança.**

Reporte de forma privada pelo GitHub:
[**Reportar uma vulnerabilidade**](https://github.com/EcoCiente-Instituto-J-F/bd2-relatorio-bancos/security/advisories/new)
(repositório → *Security* → *Advisories* → *Report a vulnerability*).

> Ative antes: repositório → *Settings* → *Code security* → *Private vulnerability reporting*.

Inclua, por favor:

- o que um atacante consegue fazer e quais dados são afetados;
- os passos ou a requisição que reproduz o problema (use dados falsos, nunca dados de pessoas
  reais);
- o commit ou a data do código que você testou e a sua configuração;
- qualquer ideia que você tenha para a correção.

O que acontece depois:

1. Confirmamos o recebimento e verificamos se conseguimos reproduzir.
2. Trabalhamos na correção de forma privada e podemos pedir mais detalhes a você.
3. Publicamos a correção e um aviso de segurança (advisory) no GitHub. Se você quiser, damos o
   crédito a você.

Pedimos um prazo razoável para corrigir o problema antes de você divulgá-lo publicamente.

## Escopo

Dentro do escopo — este repositório e o comportamento dele:

- Dados pessoais, credenciais, strings de conexão ou segredos commitados (inclusive no histórico do git, na documentação e nos arquivos gerados).
- Informação na documentação ou nos diagramas que facilite um ataque aos sistemas reais (por exemplo, endereços de servidores, usuários ou chaves).
- Vulnerabilidade nas páginas HTML (`index.html`, `modelo-postgresql-interativo.html`), como execução de script injetado.
- Falhas no workflow do PR Bot (`.github/workflows/pr-bot.yml`) que exponham segredos do repositório ou permitam executar código não confiável.

Fora do escopo:

- Bugs sem impacto de segurança — abra uma issue normal.
- Vulnerabilidades nos sistemas descritos (EcoCiente, MongoDB, Redis etc.) ou em serviços de terceiros — reporte aos mantenedores deles. Se você perceber uma falha neles ao ler este relatório, use o canal privado acima.
- Inconsistências entre o relatório e o banco real, tratadas como correção de documentação.
- Negação de serviço enviando grande volume de tráfego.

## Como o repositório se protege

| Camada | Onde | O que faz |
| --- | --- | --- |
| Exemplos fictícios | `documentacao-bancos-revisada.md`, `index.html` | Documentos e linhas de exemplo usam dados inventados. |
| PR Bot restrito | `.github/workflows/pr-bot.yml` | Usa `permissions` mínimas, faz checkout do código da branch base e só roda para branches do próprio repositório (não para forks). |

## Checklist de manutenção

- Antes de publicar, procure por senhas, tokens, strings de conexão e caminhos locais com nome de pessoa nos textos e nos arquivos gerados.
- Mantenha o segredo do PR Bot (chave do Gemini) apenas em *Settings* → *Secrets*, nunca no repositório.
- Ative *Private vulnerability reporting* para o link de relato acima funcionar.
