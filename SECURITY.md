<!-- TEMPLATE — troque os {{ placeholders }} e adapte "Escopo" e "Checklist de deploy" ao seu projeto. -->

# Política de Segurança

O {{PROJECT_NAME}} {{ONE_LINE_ABOUT_DATA_HANDLED}}. Levamos a sério os relatos sobre isso.

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
[**Reportar uma vulnerabilidade**](https://github.com/{{OWNER}}/{{REPO}}/security/advisories/new)
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

- Ler ou alterar dados de outro usuário pela API.
- Burlar autenticação ou autorização.
- Injeção (SQL, comandos, prompt) que leve à exposição de dados ou a uma ação não autorizada.
- Dados pessoais ou segredos vazando em logs, traces, métricas ou respostas.
- Segredos commitados no repositório.

Fora do escopo:

- Bugs sem impacto de segurança — abra uma issue normal.
- Vulnerabilidades em serviços de terceiros — reporte aos mantenedores deles.
- Credenciais padrão apenas para desenvolvimento, claramente marcadas (por exemplo, `CHANGEME`
  no `.env.example`).
- Negação de serviço enviando grande volume de tráfego para o seu próprio deploy.

## Checklist de deploy

Se você executa o {{PROJECT_NAME}} fora de uma máquina de desenvolvimento:

- Defina `APP_ENV=production` e desative qualquer atalho de teste ou debug.
- Mantenha os segredos em um cofre de segredos ou em um `Secret` do Kubernetes, nunca em
  `ConfigMap`, na imagem ou no repositório.
- Dê à role de banco da aplicação só as permissões necessárias (somente leitura, quando possível).
- Troque todo valor `CHANGEME` antes de expor um serviço.
- Não exponha endpoints internos (por exemplo, `/metrics`) para a internet pública.
