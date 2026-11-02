# Contribuindo com o Relatório dos Bancos de Dados do EcoCiente

Obrigado por querer melhorar este relatório. Este guia explica como configurar o projeto,
como testar uma mudança e como abrir um pull request.

Ao participar, você concorda em seguir o [Código de Conduta](CODE_OF_CONDUCT.md). Para reportar
um problema de segurança, **não** abra uma issue — siga o [SECURITY.md](SECURITY.md).

## Idioma

Issues e pull requests são bem-vindos em português ou inglês. Mantenha o código novo consistente
com o arquivo que você está editando (nomes, idioma dos identificadores e dos comentários).

## Configurando o ambiente

Para editar a documentação basta um editor de texto e um navegador. Para regenerar os diagramas
você precisa do Python 3.9 ou superior.

```bash
git clone https://github.com/EcoCiente-Instituto-J-F/bd2-relatorio-bancos.git
cd bd2-relatorio-bancos
```

Não há dependências a instalar nem `.env` a configurar. Veja o [README](README.md) para os
comandos de geração dos diagramas.

## Testando sua mudança

Este repositório não tem testes automatizados. Antes de abrir o PR:

- abra `index.html` e `modelo-postgresql-interativo.html` no navegador e confira que a página
  carrega e que o conteúdo alterado aparece corretamente;
- se mudou um script `gerar_*.py`, rode-o e confira os SVGs e o `.js` gerados em `assets/`;
- se mudou uma afirmação da documentação, confira-a no código ou no esquema SQL de origem e
  diga no PR onde a evidência está. Não afirme o que não foi verificado.

## Regras do projeto

Um pull request que quebre alguma destas regras será devolvido para ajuste.

- **Nenhum segredo no repositório.** Nada de senhas, tokens, strings de conexão ou chaves de API
  na documentação, nos scripts ou nos exemplos.
- **Nenhum dado pessoal real.** Os exemplos de documentos, linhas e payloads são fictícios.
  Também não deixe caminhos locais com nome de pessoa nos textos.
- **Nenhuma dependência nova sem discussão.** Os scripts de diagramas usam só a biblioteca
  padrão; abra uma issue antes de mudar isso.
- **Arquivos gerados não se editam à mão.** `assets/modelo-*.svg` e
  `assets/modelo-postgresql-dados.js` saem dos scripts `gerar_*.py`; altere o script e regenere.
- **Documente o que foi verificado e o que não foi.** O relatório foi feito sem conexão aos
  bancos; mantenha essa distinção.

## Pull requests

1. Crie um branch a partir da `main` com o nome da mudança, por exemplo `feat/nome-curto` ou
   `fix/nome-curto`.
2. Faça commits focados. Usamos prefixos curtos no assunto do commit: `feat:`, `fix:`,
   `chore:`, `docs:`, `test:`, `refactor:`.
3. Faça as conferências da seção anterior.
4. Abra um pull request para a `main`. Descreva o que mudou, por quê e como você testou.
   Informe qualquer nova variável de ambiente, migração ou mudança de comportamento.
5. O PR Bot (`.github/workflows/pr-bot.yml`) gera a descrição da PR; revise o texto gerado.
6. Um mantenedor revisa a mudança. Responda aos comentários com novos commits; fazemos squash
   ou merge quando for aprovada.

## Reportando bugs e propondo funcionalidades

Abra uma issue com:

- o que você esperava e o que aconteceu;
- os passos que reproduzem o problema (com dados falsos);
- o commit que você usou e o navegador, se for um problema nas páginas HTML.

Para uma funcionalidade nova, explique o problema que ela resolve antes de propor a solução.
