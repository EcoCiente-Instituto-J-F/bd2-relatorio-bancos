<p align="center">
  <img src="assets/card-readme.png" alt="Card do repositório" width="100%">
</p>

<!--
  TEMPLATE — troque os placeholders antes de usar (busque por {{ )
    {{OWNER}}          usuário/organização no GitHub
    {{REPO}}           nome do repositório
    {{PROJECT_NAME}}   nome de exibição do projeto
    {{PYTHON_VERSION}} versão mínima do Python (ex.: 3.11) — mantenha igual ao .python-version
    {{LICENSE}}        MIT, Apache--2.0, GPL--3.0 ... (hífen duplo no shields.io = hífen)
    {{LICENSE_COLOR}}  green, blue, orange ...
  Badges: https://shields.io/badges · ícones (logo=): https://simpleicons.org
  Dica: deixe só os badges das tecnologias que o projeto realmente usa.
-->

# {{PROJECT_NAME}}

![Python](https://img.shields.io/badge/Python-{{PYTHON_VERSION}}-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-14+-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![GitHub repo size](https://img.shields.io/github/repo-size/{{OWNER}}/{{REPO}}?style=for-the-badge)
![GitHub last commit](https://img.shields.io/github/last-commit/{{OWNER}}/{{REPO}}?style=for-the-badge)
![License](https://img.shields.io/badge/license-{{LICENSE}}-{{LICENSE_COLOR}}?style=for-the-badge)

> Descrição curta do projeto em uma ou duas frases.

## Sobre o projeto

Explique o problema que o projeto resolve, para quem e como.

## Pré-requisitos

- Python `{{PYTHON_VERSION}}` ou superior
- Docker e Docker Compose (opcional)

## Instalando

```bash
git clone https://github.com/{{OWNER}}/{{REPO}}.git
cd {{REPO}}
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # Windows: copy .env.example .env
```

## Usando

```bash
python -m uvicorn src.api.main:app --reload
```

## Testes

```bash
pytest
```

## Estrutura do projeto

```
{{REPO}}/
├── .github/            # workflows (CI) e templates de issue/PR
├── src/
├── tests/
├── docs/
├── .env.example
├── .python-version
├── requirements.txt
├── README.md
├── CONTRIBUTING.md
├── CODE_OF_CONDUCT.md
├── SECURITY.md
└── LICENSE
```

## Contribuindo

Leia o [CONTRIBUTING.md](CONTRIBUTING.md) antes de abrir um PR. Ao participar, você concorda com o [Código de Conduta](CODE_OF_CONDUCT.md).

## Segurança

Encontrou uma vulnerabilidade? Siga o [SECURITY.md](SECURITY.md). **Não abra issue pública.**

## Licença

Este projeto está sob a licença {{LICENSE}}. Veja o arquivo [LICENSE](LICENSE).
