"""Exporta os metadados do mapa interativo a partir dos três SQLs.

Uso: python gerar_mapa_interativo.py EXPORT_PGADMIN POPULADOR DATA_MART
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from gerar_diagramas_postgresql import (
    GROUPS, ROOT, mart_fks, pgadmin_fks, primary_key, table_blocks,
)


SQL_TYPES = {
    "integer", "int", "int4", "int8", "bigint", "smallint", "serial",
    "bigserial", "character", "varchar", "char", "text", "uuid",
    "boolean", "bool", "numeric", "decimal", "float", "real", "double",
    "timestamp", "timestamptz", "date", "time", "json", "jsonb", "bytea",
}


def fields(block: str) -> list[str]:
    result = []
    for line in block.splitlines():
        match = re.match(r"^\s{4,}([A-Za-z_]\w+)\s+([A-Za-z_]\w+)", line)
        if match and match.group(2).lower() in SQL_TYPES:
            result.append(match.group(1))
    return result


def main() -> None:
    if len(sys.argv) != 4:
        raise SystemExit(__doc__)
    pgadmin = Path(sys.argv[1]).read_text(encoding="utf-8")
    populador = Path(sys.argv[2]).read_text(encoding="utf-8")
    datamart = Path(sys.argv[3]).read_text(encoding="utf-8")

    operational = table_blocks(pgadmin)
    for name in ("tb_metricas_dau", "tb_migracao_ids_map"):
        match = re.search(
            rf"(?ims)^CREATE TABLE IF NOT EXISTS {name}\s*\((.*?)^\);",
            populador,
        )
        if match is None:
            raise ValueError(f"Tabela não encontrada no populador: {name}")
        operational[name] = match.group(1)
    mart = table_blocks(datamart)
    relations = pgadmin_fks(pgadmin) + mart_fks(mart)
    assert len(operational) == 50 and len(mart) == 9 and len(relations) == 92

    group_for = {
        name: slug for slug, _, names in GROUPS for name in names
    }
    group_for.update({name: "datamart" for name in mart})
    group_for.update({
        "tb_metricas_dau": "apoio", "tb_migracao_ids_map": "apoio",
    })
    data = {"tables": [], "relations": []}
    for name, block in {**operational, **mart}.items():
        columns = fields(block)
        pk = [item.strip() for item in primary_key(block).split(",")]
        if not columns or any(item not in columns for item in pk):
            raise ValueError(f"Colunas ou PK não identificadas: {name}")
        data["tables"].append({
            "name": name,
            "group": group_for.get(name, "referencias"),
            "columns": columns,
            "pk": pk,
        })
    columns_by_name = {table["name"]: set(table["columns"]) for table in data["tables"]}
    for source, source_cols, target, target_cols in relations:
        source_list = [item.strip() for item in source_cols.split(",")]
        target_list = [item.strip() for item in target_cols.split(",")]
        if len(source_list) != len(target_list):
            raise ValueError(f"FK com aridade diferente: {source} → {target}")
        if any(item not in columns_by_name[source] for item in source_list):
            raise ValueError(f"Coluna FK não encontrada: {source}.{source_cols}")
        if any(item not in columns_by_name[target] for item in target_list):
            raise ValueError(f"Coluna referenciada não encontrada: {target}.{target_cols}")
        data["relations"].append({
            "source": source,
            "sourceColumns": source_list,
            "target": target,
            "targetColumns": target_list,
        })
    data["tables"].sort(key=lambda table: (table["group"], table["name"]))
    out = ROOT / "assets" / "modelo-postgresql-dados.js"
    out.write_text(
        "/* Gerado dos SQLs do pgAdmin, populador e Data Mart. */\n"
        + "window.ECOCIENTE_PG_MODEL = "
        + json.dumps(data, ensure_ascii=False, separators=(",", ":"))
        + ";\n",
        encoding="utf-8",
    )
    print(f"{len(data['tables'])} tabelas, {len(data['relations'])} FKs, "
          f"{sum(len(t['columns']) for t in data['tables'])} colunas")


if __name__ == "__main__":
    main()
