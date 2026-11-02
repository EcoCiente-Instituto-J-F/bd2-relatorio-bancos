"""Desenha os modelos conceituais de MongoDB e Neo4j do relatório."""

from __future__ import annotations

from html import escape
from pathlib import Path
import re
from math import hypot
from xml.etree import ElementTree as ET


ASSETS = Path(__file__).resolve().parent / "assets"
SVG_NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG_NS)


def esc(value: str) -> str:
    return escape(value, quote=True)


def label(x: int, y: int, value: str, width: int | None = None) -> str:
    width = width or max(98, int(len(value) * 9.4 + 28))
    return (
        f'<g><rect x="{x-width/2:g}" y="{y-20}" width="{width}" height="40" '
        'rx="19" fill="#fff" stroke="#bed1c6" stroke-width="1.5"/>'
        f'<text x="{x}" y="{y+5}" text-anchor="middle" class="edge-label">'
        f'{esc(value)}</text></g>'
    )


def directed_edge(path: str, stroke: str, width: float) -> str:
    coordinates = [float(value) for value in re.findall(r"-?\d+(?:\.\d+)?", path)]
    c2x, c2y, end_x, end_y = coordinates[-4:]
    dx, dy = end_x - c2x, end_y - c2y
    length = hypot(dx, dy)
    ux, uy = dx / length, dy / length
    px, py = -uy, ux
    base_x, base_y = end_x - 13 * ux, end_y - 13 * uy
    left = (base_x + 5.2 * px, base_y + 5.2 * py)
    right = (base_x - 5.2 * px, base_y - 5.2 * py)
    points = f"{end_x:g},{end_y:g} {left[0]:.1f},{left[1]:.1f} {right[0]:.1f},{right[1]:.1f}"
    return (
        f'<path d="{path}" fill="none" stroke="{stroke}" stroke-width="{width:g}"/>'
        f'<polygon points="{points}" fill="{stroke}"/>'
    )


def mongo_card(x: int, y: int, w: int, h: int, kind: str,
               title: str, fields: list[str], tone: str = "#e8eee8") -> str:
    lines = [
        f'<g><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="16" '
        'fill="#fff" stroke="#bfd0c3" stroke-width="1.6"/>',
        f'<path d="M{x+16} {y}H{x+w-16}A16 16 0 0 1 {x+w} {y+16}V{y+62}'
        f'H{x}V{y+16}A16 16 0 0 1 {x+16} {y}" fill="{tone}"/>',
        f'<text x="{x+20}" y="{y+25}" class="kind">{esc(kind)}</text>',
        f'<text x="{x+20}" y="{y+50}" class="card-title">{esc(title)}</text>',
    ]
    for i, field in enumerate(fields):
        fy = y + 100 + i * 34
        if i:
            lines.append(f'<path d="M{x+20} {fy-17}H{x+w-20}" stroke="#e4ebe4"/>')
        lines.append(f'<text x="{x+21}" y="{fy}" class="field">{esc(field)}</text>')
    lines.append('</g>')
    return ''.join(lines)


def mongodb() -> str:
    edges = [
        directed_edge("M340 443 C410 440 438 298 501 298", "#177456", 3),
        directed_edge("M340 491 C411 514 445 685 501 685", "#177456", 3),
        directed_edge("M885 298 C953 298 997 298 1046 298", "#177456", 3),
    ]
    cards = [
        mongo_card(80, 388, 260, 150, "IDENTIDADE", "Usuário", ["usuario_id"]),
        mongo_card(510, 150, 375, 290, "COLEÇÃO", "sessoes", [
            "session_id (único)", "usuario_id", "expira_em (TTL)",
            "memory_summary", "messages[]",
        ]),
        mongo_card(510, 575, 440, 230, "COLEÇÃO", "memoria_usuarios", [
            "usuario_id (único)", "texto", "revision", "updated_at",
        ], "#e1f0e5"),
        mongo_card(1055, 165, 385, 270, "DOCUMENTO EMBUTIDO", "messages[]", [
            "id", "role", "content", "created_at",
        ], "#e4eff2"),
    ]
    return ''.join([
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1540 900" '
        'role="img" aria-labelledby="title desc">',
        '<title id="title">MongoDB · sessões e memória de usuários</title>',
        '<desc id="desc">O usuário se relaciona às coleções sessoes e '
        'memoria_usuarios pelo campo usuario_id. Cada sessão contém '
        'mensagens embutidas.</desc>',
        '<style>text{font-family:Segoe UI,Arial,sans-serif}'
        '.heading{fill:#0f1723;font:600 36px Georgia,serif}'
        '.sub{fill:#425a57;font-size:18px}'
        '.kind{fill:#4d7261;font-size:13px;font-weight:700;letter-spacing:.08em}'
        '.card-title{fill:#064e3b;font-size:23px;font-weight:700}'
        '.field{fill:#29483b;font:17px Consolas,monospace}'
        '.edge{fill:none;stroke:#177456;stroke-width:3}'
        '.edge-label{fill:#07513d;font-size:16px;font-weight:700}</style>',
        '<rect width="1540" height="900" rx="18" fill="#f7f3f0"/>',
        '<text x="50" y="62" class="heading">MongoDB · sessões e memória</text>',
        '<text x="50" y="96" class="sub">Duas coleções por usuário; as mensagens ficam dentro da sessão.</text>',
        *edges,
        *cards,
        label(415, 347, "usuario_id", 128),
        label(415, 607, "usuario_id", 128),
        label(970, 250, "messages[]", 133),
        '</svg>',
    ])


def graph_node(x: int, y: int, color: str, lines: list[str]) -> str:
    row_start = y - (len(lines) - 1) * 13
    content = [
        f'<g><circle cx="{x}" cy="{y}" r="83" fill="#fff" stroke="{color}" '
        'stroke-width="3"/>',
        f'<circle cx="{x}" cy="{y}" r="75" fill="{color}"/>',
    ]
    for i, line in enumerate(lines):
        content.append(
            f'<text x="{x}" y="{row_start+i*26+6}" text-anchor="middle" '
            f'class="node-label">{esc(line)}</text>'
        )
    content.append('</g>')
    return ''.join(content)


def neo4j() -> str:
    # Cada ligação abaixo corresponde a um tipo e direção descritos no modelo.
    edges = [
        ("MORA_EM", "M375 525 C520 385 670 365 822 408", 580, 354, 112),
        ("PERTENCE_A", "M383 563 C555 545 680 490 822 438", 600, 515, 143),
        ("PERTENCE_A", "M1368 248 C1240 224 1100 317 982 397", 1180, 255, 143),
        ("REPRESENTADA_POR", "M1405 629 C1280 136 648 102 327 481", 920, 160, 211),
        ("CRIOU", "M374 613 C540 650 690 760 850 848", 590, 671, 92),
        ("VALIDOU", "M370 640 C530 776 685 839 850 878", 620, 789, 110),
        ("DENUNCIOU", "M354 650 C493 933 703 999 865 914", 668, 972, 146),
        ("NO_CONDOMINIO", "M925 797 C980 672 953 560 912 503", 1085, 648, 192),
        ("NA_TORRE", "M1004 844 C1363 793 1630 480 1495 308", 1555, 535, 117),
        ("DA_CATEGORIA", "M1011 920 C1195 956 1337 1008 1457 1036", 1257, 964, 169),
        ("APROVADO_EM", "M268 638 C190 760 180 873 260 991", 137, 781, 158),
        ("TEM_DIFICULDADE_EM", "M339 638 C461 754 460 885 333 994", 510, 840, 246),
        ("RECOMENDADO_PARA", "M211 1030 C43 940 66 728 244 630", 130, 925, 226),
    ]
    nodes = [
        graph_node(300, 560, "#075541", ["Usuario"]),
        graph_node(900, 420, "#3e6c94", ["Condominio"]),
        graph_node(1450, 235, "#a76839", ["Torre"]),
        graph_node(1480, 660, "#74649a", ["Cooperativa"]),
        graph_node(930, 880, "#b45774", ["Postagem"]),
        graph_node(1540, 1050, "#55895e", ["Categoria", "Residuo"]),
        graph_node(280, 1070, "#9f7e22", ["Curso"]),
    ]
    return ''.join([
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1800 1260" '
        'role="img" aria-labelledby="title desc">',
        '<title id="title">Neo4j · modelo de nós e relações</title>',
        '<desc id="desc">Sete tipos de nó em círculos coloridos e treze '
        'ligações direcionadas, com doze tipos de relação.</desc>',
        '<style>text{font-family:Segoe UI,Arial,sans-serif}'
        '.heading{fill:#0f1723;font:600 39px Georgia,serif}'
        '.sub{fill:#425a57;font-size:18px}'
        '.edge{fill:none;stroke:#607d75;stroke-width:2.7}'
        '.edge-label{fill:#07513d;font-size:16px;font-weight:700}'
        '.node-label{fill:#fff;font-size:20px;font-weight:700}</style>',
        '<rect width="1800" height="1260" rx="18" fill="#f7f3f0"/>',
        '<text x="50" y="65" class="heading">Neo4j · nós e relações</text>',
        '<text x="50" y="100" class="sub">Sete tipos de nó · doze tipos de relação · direção indicada pelas setas</text>',
        *[directed_edge(path, "#607d75", 2.7)
          for _, path, _, _, _ in edges],
        *nodes,
        *[label(x, y, name, width) for name, _, x, y, width in edges],
        '</svg>',
    ])


def inline_styles(svg: str, styles: dict[str, dict[str, str]]) -> str:
    root = ET.fromstring(svg)
    for element in root.iter():
        css_class = element.attrib.pop("class", None)
        if css_class:
            for key, value in styles[css_class].items():
                element.set(key, value)
    for element in list(root):
        if element.tag == f"{{{SVG_NS}}}style":
            root.remove(element)
    return ET.tostring(root, encoding="unicode")


def main() -> None:
    ASSETS.mkdir(exist_ok=True)
    common_text = {"font-family": "Segoe UI, Arial, sans-serif"}
    mongo_styles = {
        "heading": {**common_text, "fill": "#0f1723", "font-family": "Georgia, serif", "font-size": "36", "font-weight": "600"},
        "sub": {**common_text, "fill": "#425a57", "font-size": "18"},
        "kind": {**common_text, "fill": "#4d7261", "font-size": "13", "font-weight": "700", "letter-spacing": ".08em"},
        "card-title": {**common_text, "fill": "#064e3b", "font-size": "23", "font-weight": "700"},
        "field": {"font-family": "Consolas, monospace", "fill": "#29483b", "font-size": "17"},
        "edge": {"fill": "none", "stroke": "#177456", "stroke-width": "3"},
        "edge-label": {**common_text, "fill": "#07513d", "font-size": "16", "font-weight": "700"},
    }
    neo_styles = {
        "heading": {**common_text, "fill": "#0f1723", "font-family": "Georgia, serif", "font-size": "39", "font-weight": "600"},
        "sub": {**common_text, "fill": "#425a57", "font-size": "18"},
        "edge": {"fill": "none", "stroke": "#607d75", "stroke-width": "2.7"},
        "edge-label": {**common_text, "fill": "#07513d", "font-size": "16", "font-weight": "700"},
        "node-label": {**common_text, "fill": "#fff", "font-size": "20", "font-weight": "700"},
    }
    (ASSETS / "modelo-mongodb.svg").write_text(
        inline_styles(mongodb(), mongo_styles), encoding="utf-8")
    (ASSETS / "modelo-neo4j.svg").write_text(
        inline_styles(neo4j(), neo_styles), encoding="utf-8")
    print("MongoDB e Neo4j atualizados")


if __name__ == "__main__":
    main()
