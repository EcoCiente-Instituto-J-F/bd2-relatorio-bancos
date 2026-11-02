<!-- TEMPLATE — troque os {{ placeholders }} e adapte "Regras do projeto" ao seu projeto. -->

# Contribuindo com o {{PROJECT_NAME}}

Obrigado por querer melhorar o {{PROJECT_NAME}}. Este guia explica como configurar o projeto,
como testar uma mudança e como abrir um pull request.

Ao participar, você concorda em seguir o [Código de Conduta](CODE_OF_CONDUCT.md). Para reportar
um problema de segurança, **não** abra uma issue — siga o [SECURITY.md](SECURITY.md).

## Idioma

Issues e pull requests são bem-vindos em português ou inglês. Mantenha o código novo consistente
com o arquivo que você está editando (nomes, idioma dos identificadores e dos comentários).

## Configurando o ambiente

Você precisa do Python {{PYTHON_VERSION}} ou superior.

```bash
git clone https://github.com/{{OWNER}}/{{REPO}}.git
cd {{REPO}}
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # Windows: copy .env.example .env
```

Veja o [README](README.md) para saber como executar o projeto.

## Testando sua mudança

Rode o mesmo comando que o CI roda:

```bash
python -m pytest -q
```

- Toda mudança precisa de testes que falhem sem ela. Correção de bug começa com um teste que
  reproduz o bug.
- Os testes não podem chamar APIs pagas, bancos reais nem a rede. Use mocks ou fixtures.
- Nunca aponte os testes para dados ou serviços de produção.

## Regras do projeto

Adapte esta lista ao seu projeto. Um pull request que quebre alguma destas regras será
devolvido para ajuste.

- **Nenhum segredo no repositório.** O `.env` é ignorado; adicione novas variáveis ao
  `.env.example` (com um valor padrão seguro).
- **Nenhum dado pessoal real** em testes, fixtures, exemplos ou issues. Use nomes e ids falsos.
- **Nenhuma dependência nova sem discussão.** Abra uma issue antes e explique por que a
  biblioteca padrão ou um pacote já instalado não resolve.
- Leia a configuração em um único lugar (por exemplo, uma classe `Settings`); não espalhe
  `os.getenv` pelo código.

## Pull requests

1. Crie um branch a partir da `main` com o nome da mudança, por exemplo `feat/nome-curto` ou
   `fix/nome-curto`.
2. Faça commits focados. Usamos prefixos curtos no assunto do commit: `feat:`, `fix:`,
   `chore:`, `docs:`, `test:`, `refactor:`.
3. Rode a suíte de testes localmente.
4. Abra um pull request para a `main`. Descreva o que mudou, por quê e como você testou.
   Informe qualquer nova variável de ambiente, migração ou mudança de comportamento.
5. O CI (`.github/workflows/`) precisa passar.
6. Um mantenedor revisa a mudança. Responda aos comentários com novos commits; fazemos squash
   ou merge quando for aprovada.

## Reportando bugs e propondo funcionalidades

Abra uma issue com:

- o que você esperava e o que aconteceu;
- os passos que reproduzem o problema (com dados falsos);
- a sua configuração e o commit que você usou.

Para uma funcionalidade nova, explique o problema que ela resolve antes de propor a solução.
