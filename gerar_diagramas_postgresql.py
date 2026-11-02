"""Gera mapas de chaves estrangeiras a partir dos SQLs do projeto.

Uso: python gerar_diagramas_postgresql.py EXPORT_PGADMIN POPULADOR DATA_MART
"""

from __future__ import annotations

import re
import sys
from collections import defaultdict
from html import escape
from pathlib import Path


ROOT = Path(__file__).resolve().parent
GROUPS = [
    ("cadastros", "Pessoas e condomínios", [
        "tb_usuarios", "tb_sindicos", "tb_condominios", "tb_torres",
        "tb_moradores", "tb_rel_usuarios_condominios", "tb_telefones",
        "tb_notificacoes", "tb_autenticacoes_api",
        "tb_atividades_diarias_usuarios", "tb_recuperacoes_senha",
    ]),
    ("coletas", "Cooperativas e coletas", [
        "tb_cooperativas", "tb_pontos_coletas",
        "tb_rel_cooperativas_categorias_materiais",
        "tb_rel_pontos_coletas_categorias", "tb_agendamentos_coletas",
        "tb_visitas_coletas", "tb_avaliacoes_visitas_coletas",
        "tb_rel_recorrencias_agendamentos",
    ]),
    ("postagens", "Postagens e pontos", [
        "tb_postagens", "tb_rel_votos_postagens", "tb_movimentacoes_pontos",
    ]),
    ("educacao", "Educação e quizzes", [
        "tb_cursos", "tb_aulas", "tb_quizzes", "tb_perguntas_quiz",
        "tb_alternativas_quiz", "tb_tentativas_quiz",
        "tb_rel_respostas_tentativas_quiz", "tb_rel_usuarios_cursos",
    ]),
    ("auditoria", "Conversas e auditoria", [
        "tb_conversas", "tb_mensagens_conversas", "tb_log_auditoria",
        "tb_log_auditoria_postagens",
        "tb_log_auditoria_agendamentos_coletas",
        "tb_log_auditoria_usuarios_condominios",
    ]),
]


def table_blocks(sql: str) -> dict[str, str]:
    pattern = re.compile(
        r"(?ims)^CREATE TABLE(?: IF NOT EXISTS)? (?:public\.)?(\w+)\s*\((.*?)^\);"
    )
    return {match.group(1): match.group(2) for match in pattern.finditer(sql)}


def primary_key(block: str) -> str:
    constraint = re.search(r"PRIMARY KEY\s*\(([^)]+)\)", block, re.I)
    if constraint:
        return re.sub(r"\s+", "", constraint.group(1))
    inline = re.search(r"(?im)^\s*(\w+)\s+\w+[^\n]*\bPRIMARY KEY\b", block)
    if inline:
        return inline.group(1)
    raise ValueError("Tabela sem chave primária identificável")


def pgadmin_fks(sql: str) -> list[tuple[str, str, str, str]]:
    pattern = re.compile(
        r"(?is)ALTER TABLE IF EXISTS public\.(\w+)\s+"
        r"ADD CONSTRAINT \w+ FOREIGN KEY \(([^)]+)\)\s+"
        r"REFERENCES public\.(\w+)\s*\(([^)]+)\)"
    )
    return [
        (source, re.sub(r"\s+", "", src_cols), target,
         re.sub(r"\s+", "", target_cols))
        for source, src_cols, target, target_cols in pattern.findall(sql)
    ]


def mart_fks(blocks: dict[str, str]) -> list[tuple[str, str, str, str]]:
    pattern = re.compile(
        r"(?im)^\s*(\w+)\s+\w+[^\n]*\n\s*REFERENCES\s+(\w+)\s*\(([^)]+)\)"
    )
    return [
        (source, col, target, target_col)
        for source, block in blocks.items()
        for col, target, target_col in pattern.findall(block)
    ]


def svg_diagram(
    title: str,
    tables: list[str],
    keys: dict[str, str],
    fks: list[tuple[str, str, str, str]],
    source_note: str,
) -> str:
    by_source: dict[str, list[tuple[str, str, str]]] = defaultdict(list)
    for source, source_col, target, target_col in fks:
        by_source[source].append((source_col, target, target_col))

    width = 1460
    start_y = 163
    row_h = 43
    gap = 16
    card_header = 42
    card_pad = 13
    heights = [card_header + max(1, len(by_source[t])) * row_h + card_pad for t in tables]
    height = start_y + sum(heights) + gap * (len(tables) - 1) + 42
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'role="img" aria-labelledby="title desc">',
        f'<title id="title">PostgreSQL · {escape(title)}</title>',
        f'<desc id="desc">Chaves primárias e {len(fks)} chaves estrangeiras '
        f'de {len(tables)} tabelas. Cada seta sai da coluna FK e aponta para '
        'a tabela e a coluna referenciadas.</desc>',
        '<defs><marker id="arrow" markerWidth="9" markerHeight="9" '
        'refX="8" refY="4.5" orient="auto"><path d="M1 1L8 4.5L1 8" '
        'fill="none" stroke="#075540" stroke-width="1.8"/></marker></defs>',
        '<style>text{font-family:Segoe UI,Arial,sans-serif}'
        '.title{font:700 31px Georgia,serif;fill:#073f35}'
        '.sub{font-size:17px;fill:#46645a}'
        '.col{font-size:15px;font-weight:700;letter-spacing:.09em;fill:#527369}'
        '.name{font-size:18px;font-weight:700;fill:#064e3b}'
        '.pk{font-size:15px;fill:#52675e}'
        '.field{font-size:16px;fill:#223b34}'
        '.ref{font-size:16px;font-weight:600;fill:#124b3b}'
        '.sourcebox{fill:#fff;stroke:#bbd0c4;stroke-width:1.5}'
        '.targetbox{fill:#e9f1e9;stroke:#b3cdbb;stroke-width:1.2}'
        '.line{stroke:#075540;stroke-width:2;fill:none}'
        '.divider{stroke:#e1eae1;stroke-width:1}</style>',
        f'<rect width="{width}" height="{height}" rx="18" fill="#f7f3f0"/>',
        f'<text x="52" y="55" class="title">{escape(title)}</text>',
        f'<text x="52" y="86" class="sub">{len(tables)} tabelas · '
        f'{len(fks)} relações por chave estrangeira</text>',
        f'<text x="52" y="112" class="sub">{escape(source_note)}</text>',
        '<text x="72" y="148" class="col">TABELA E COLUNA FK</text>',
        '<text x="850" y="148" class="col">TABELA E COLUNA REFERENCIADA</text>',
    ]
    y = start_y
    for table, card_h in zip(tables, heights):
        entries = by_source[table]
        parts.append(f'<g aria-label="{escape(table)}">')
        parts.append(
            f'<rect class="sourcebox" x="52" y="{y}" width="605" '
            f'height="{card_h}" rx="13"/>'
        )
        parts.append(f'<rect x="53" y="{y+1}" width="603" height="41" rx="12" fill="#e7eee7"/>')
        parts.append(f'<text x="72" y="{y+27}" class="name">{escape(table)}</text>')
        parts.append(f'<text x="638" y="{y+27}" class="pk" text-anchor="end">PK {escape(keys[table])}</text>')
        if entries:
            for index, (source_col, target, target_col) in enumerate(entries):
                row_y = y + card_header + index * row_h
                mid_y = row_y + 22
                if index:
                    parts.append(f'<path class="divider" d="M72 {row_y}H638"/>')
                parts.append(f'<text x="73" y="{mid_y+5}" class="field">FK {escape(source_col)}</text>')
                parts.append(
                    f'<path class="line" d="M657 {mid_y}H816" '
                    'marker-end="url(#arrow)"/>'
                )
                parts.append(
                    f'<rect class="targetbox" x="832" y="{row_y+2}" '
                    f'width="574" height="38" rx="9"/>'
                )
                parts.append(f'<text x="848" y="{mid_y+5}" class="ref">{escape(target)}</text>')
                parts.append(f'<text x="1390" y="{mid_y+5}" class="pk" text-anchor="end">{escape(target_col)}</text>')
        else:
            parts.append(f'<text x="73" y="{y+card_header+28}" class="pk">Sem chave estrangeira de saída</text>')
        parts.append('</g>')
        y += card_h + gap
    parts.append('</svg>')
    return ''.join(parts)


def main() -> None:
    if len(sys.argv) != 4:
        raise SystemExit(__doc__)
    pgadmin = Path(sys.argv[1]).read_text(encoding="utf-8")
    populator = Path(sys.argv[2]).read_text(encoding="utf-8")
    mart = Path(sys.argv[3]).read_text(encoding="utf-8")

    pg_tables = table_blocks(pgadmin)
    pop_names = set(re.findall(
        r"(?im)^CREATE TABLE(?: IF NOT EXISTS)? (\w+)", populator
    ))
    pop_tables = {
        name: match.group(1)
        for name in ("tb_metricas_dau", "tb_migracao_ids_map")
        if (match := re.search(
            rf"(?ims)^CREATE TABLE IF NOT EXISTS {name}\s*\((.*?)^\);",
            populator,
        ))
    }
    mart_tables = table_blocks(mart)
    pg_fks = pgadmin_fks(pgadmin)
    dm_fks = mart_fks(mart_tables)
    assert len(pg_tables) == 48 and len(pg_fks) == 83, (len(pg_tables), len(pg_fks))
    assert len(pop_names) == 50 and len(mart_tables) == 9 and len(dm_fks) == 9
    assert set(pg_tables) <= pop_names
    assert pop_names - set(pg_tables) == {"tb_metricas_dau", "tb_migracao_ids_map"}
    assert set(pop_tables) == pop_names - set(pg_tables)
    assert all(source in pg_tables and target in pg_tables for source, _, target, _ in pg_fks)
    assert all(source in mart_tables and target in mart_tables for source, _, target, _ in dm_fks)

    keys = {name: primary_key(block) for name, block in pg_tables.items()}
    keys.update({name: primary_key(block) for name, block in pop_tables.items()})
    mart_keys = {name: primary_key(block) for name, block in mart_tables.items()}
    covered = [table for _, _, tables in GROUPS for table in tables]
    assert len(covered) == len(set(covered))
    assert {source for source, _, _, _ in pg_fks} <= set(covered)

    output = ROOT / "assets"
    output.mkdir(exist_ok=True)
    for slug, title, tables in GROUPS:
        group_fks = [fk for fk in pg_fks if fk[0] in tables]
        content = svg_diagram(title, tables, keys, group_fks,
                              "Relações declaradas no SQL exportado pelo pgAdmin")
        (output / f"modelo-postgresql-{slug}.svg").write_text(content, encoding="utf-8")
        print(slug, len(tables), len(group_fks))
    mart_source = ["fato_postagens", "fato_coletas"]
    (output / "modelo-postgresql-datamart.svg").write_text(
        svg_diagram("Data Mart · modelo estrela", mart_source, mart_keys, dm_fks,
                    "Sete dimensões e dois fatos definidos no SQL do Data Mart"),
        encoding="utf-8",
    )
    (output / "modelo-postgresql-apoio.svg").write_text(
        svg_diagram("Tabelas de apoio", ["tb_metricas_dau", "tb_migracao_ids_map"],
                    keys, [], "Tabelas definidas no esquema SQL do populador"),
        encoding="utf-8",
    )
    print("total", len(pop_names) + len(mart_tables), len(pg_fks) + len(dm_fks))


if __name__ == "__main__":
    main()
