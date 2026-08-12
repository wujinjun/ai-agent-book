#!/usr/bin/env python3
"""Build editable SVG and PNG fallbacks for authored textbook infographics."""

from __future__ import annotations

import argparse
import base64
import hashlib
import html
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
ASSET_ROOT = ROOT / "assets/infographics"
PUBLISH_ROOT = ROOT / "docs/assets/infographics"
FONT_ROOT = ROOT / "assets/fonts/noto-sans-sc"


@dataclass(frozen=True, slots=True)
class Label:
    x: int
    y: int
    text: str
    size: int
    weight: str = "regular"
    color: str = "#203449"
    stroke_width: int = 0


@dataclass(frozen=True, slots=True)
class InfographicRecord:
    semantic_id: str
    source_path: str
    source_asset: str
    svg_asset: str
    png_asset: str
    width: int
    height: int
    source_sha256: str
    svg_sha256: str
    png_sha256: str
    generated_with: str
    generated_at: str


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _font(size: int, weight: str = "regular") -> ImageFont.FreeTypeFont:
    name = "NotoSansSC-Bold.otf" if weight == "bold" else "NotoSansSC-Regular.otf"
    return ImageFont.truetype(str(FONT_ROOT / name), size=size)


def _svg_text(label: Label) -> str:
    lines = label.text.split("\n")
    start = label.y - (len(lines) - 1) * label.size * 0.62
    tspans = []
    for index, line in enumerate(lines):
        y = start + index * label.size * 1.25
        tspans.append(f'<tspan x="{label.x}" y="{y:.1f}">{html.escape(line)}</tspan>')
    weight = 700 if label.weight == "bold" else 500
    stroke = ""
    if label.stroke_width:
        stroke = (
            f' stroke="#FFFDF8" stroke-width="{label.stroke_width * 2}" '
            'paint-order="stroke fill" stroke-linejoin="round"'
        )
    return (
        f'<text text-anchor="middle" font-size="{label.size}" font-weight="{weight}" '
        f'fill="{label.color}"{stroke}>{"".join(tspans)}</text>'
    )


def _draw_arrow(
    draw: ImageDraw.ImageDraw,
    points: list[tuple[int, int]],
    *,
    color: str = "#486985",
    width: int = 4,
) -> None:
    draw.line(points, fill=color, width=width, joint="curve")
    if len(points) < 2:
        return
    x2, y2 = points[-1]
    x1, y1 = points[-2]
    if abs(x2 - x1) >= abs(y2 - y1):
        direction = 1 if x2 > x1 else -1
        triangle = [(x2, y2), (x2 - 13 * direction, y2 - 8), (x2 - 13 * direction, y2 + 8)]
    else:
        direction = 1 if y2 > y1 else -1
        triangle = [(x2, y2), (x2 - 8, y2 - 13 * direction), (x2 + 8, y2 - 13 * direction)]
    draw.polygon(triangle, fill=color)


def _pilot_one_labels() -> list[Label]:
    return [
        Label(768, 52, "从大语言模型到可部署 Agent 系统", 34, "bold", "#24476B"),
        Label(202, 205, "人工智能\n研究与工程领域", 22, "bold"),
        Label(456, 282, "机器学习\n从数据学习参数", 20, "bold"),
        Label(700, 360, "深度学习\n多层神经网络", 20, "bold"),
        Label(941, 430, "Transformer\nAttention 序列建模", 19, "bold"),
        Label(1202, 468, "大语言模型\n预训练语言模型", 20, "bold"),
        Label(1415, 164, "规则、搜索与符号方法\n仍属于人工智能", 18, "bold", "#7A4A23"),
        Label(508, 636, "聊天产品\n界面、账户、搜索与文件", 22, "bold"),
        Label(958, 636, "Agent Runtime\n状态、工具、循环与终止", 22, "bold"),
        Label(155, 836, "工具与 MCP\n连接外部动作", 18, "bold"),
        Label(389, 836, "RAG 与 Memory\n知识与长期状态", 18, "bold"),
        Label(620, 836, "工作流\n恢复与终止", 18, "bold"),
        Label(852, 836, "人工审批\n权限与审计", 18, "bold"),
        Label(1086, 836, "观测与评估\nTrace 与回归", 18, "bold"),
        Label(1332, 836, "安全与成本\n工程治理边界", 18, "bold"),
        Label(742, 112, "包含关系与技术演进并存，不表示人工智能只有一条路线", 16),
    ]


def _pilot_two_labels() -> list[Label]:
    return [
        Label(768, 30, "RAG：从文档摄取到带引用回答", 31, "bold", "#24476B"),
        Label(350, 94, "离线摄取管线", 23, "bold", "#178F82"),
        Label(1128, 94, "在线查询与证据链", 23, "bold", "#24476B"),
        Label(98, 389, "原始文档", 17, "bold"),
        Label(229, 389, "解析与清洗", 17, "bold"),
        Label(355, 389, "切分与元数据", 17, "bold"),
        Label(481, 389, "Embedding\n向量表示", 17, "bold"),
        Label(610, 389, "版本化索引", 17, "bold"),
        Label(802, 389, "用户问题", 16, "bold"),
        Label(910, 389, "身份与 ACL", 16, "bold"),
        Label(1013, 389, "混合检索", 16, "bold"),
        Label(1117, 389, "候选片段", 16, "bold"),
        Label(1224, 389, "重排", 16, "bold"),
        Label(1336, 389, "生成", 16, "bold"),
        Label(1445, 389, "引用校验", 16, "bold"),
        Label(282, 592, "摄取质量与版本治理\n解析、Chunk、元数据、可追踪性", 20, "bold"),
        Label(1170, 592, "查询证据链\n权限过滤、检索、重排、引用与核验", 20, "bold"),
        Label(768, 672, "版本化知识索引", 18, "bold", "#177B72"),
        Label(272, 821, "摄取质量评估\n解析成功率 · Chunk 覆盖", 20, "bold"),
        Label(774, 821, "检索与生成评估\nRecall · Faithfulness · Citation", 20, "bold"),
        Label(1270, 821, "回归与反馈\n用失败样本调整数据和策略", 20, "bold"),
    ]


def _pilot_three_labels() -> list[Label]:
    return [
        Label(512, 55, "企业 Agent 平台：五层参考架构", 30, "bold", "#24476B"),
        Label(199, 298, "租户与用户\n主体和权限上下文", 24, "bold", "#B94A48"),
        Label(491, 298, "Web · Mobile · API\n客户端入口", 24, "bold", "#B94A48"),
        Label(761, 298, "身份与租户策略\n认证 · 配额 · 审批", 24, "bold", "#B94A48"),
        Label(309, 582, "Agent Runtime\n状态 · Tool Loop · 终止", 27, "bold", "#24476B"),
        Label(
            749,
            582,
            "Workflow / State Machine\nCheckpoint · Retry · Recovery",
            25,
            "bold",
            "#7656A5",
        ),
        Label(193, 880, "Model Gateway\n路由 · 超时 · 预算", 23, "bold", "#177B72"),
        Label(491, 880, "Tool / MCP Registry\nSchema · Policy · 执行", 23, "bold", "#D9782D"),
        Label(790, 880, "RAG 与 Memory\n证据 · 状态 · 删除", 23, "bold", "#177B72"),
        Label(273, 1137, "Queue 与 Worker\n租约 · 幂等 · 取消", 24, "bold", "#177B72"),
        Label(721, 1137, "PostgreSQL · Vector · Redis\n状态 · 索引 · 缓存", 24, "bold", "#177B72"),
        Label(163, 1430, "Trace\n调用链与成本", 20, "bold", "#7656A5"),
        Label(392, 1430, "Audit\n主体与授权决定", 20, "bold", "#7656A5"),
        Label(620, 1430, "Evaluation\n任务成功与回归", 20, "bold", "#7656A5"),
        Label(848, 1430, "Policy 与 Security\n门禁与人工审批", 20, "bold", "#7656A5"),
        Label(942, 744, "租户与信任边界", 18, "bold", "#B94A48"),
    ]


def build_pilot_one() -> InfographicRecord:
    semantic_id = "llm-product-agent-system-infographic"
    source = ASSET_ROOT / "source/llm-product-agent-system-infographic-base.png"
    if not source.is_file():
        raise FileNotFoundError(f"缺少信息图底稿：{source}")
    image = Image.open(source).convert("RGB")
    width, height = image.size
    labels = _pilot_one_labels()

    encoded = base64.b64encode(source.read_bytes()).decode("ascii")
    svg_lines = [
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">'
        ),
        '<title id="title">从大语言模型到可部署 Agent 系统</title>',
        (
            '<desc id="desc">人工智能包含机器学习与符号方法，机器学习经深度学习和 '
            "Transformer 发展出大语言模型；对齐模型可进入聊天产品或 Agent Runtime，"
            "Agent 再连接工具、知识、记忆、工作流、审批、观测、评估、安全与成本治理。</desc>"
        ),
        (
            '<defs><marker id="arrow" markerWidth="10" markerHeight="10" refX="8" '
            'refY="5" orient="auto"><path d="M0,0 L10,5 L0,10 z" '
            'fill="#486985"/></marker></defs>'
        ),
        (
            f'<image href="data:image/png;base64,{encoded}" x="0" y="0" '
            f'width="{width}" height="{height}"/>'
        ),
        (
            '<g fill="none" stroke="#486985" stroke-width="4" stroke-linecap="round" '
            'stroke-linejoin="round" marker-end="url(#arrow)">'
        ),
        '<path d="M 326 190 L 340 190"/>',
        '<path d="M 574 263 L 588 263"/>',
        '<path d="M 816 338 L 830 338"/>',
        '<path d="M 1064 390 L 1078 390"/>',
        '<path d="M 1202 510 L 1202 518 L 508 518 L 508 526"/>',
        '<path d="M 1202 510 L 1202 518 L 958 518 L 958 526"/>',
        '<path d="M 958 693 L 958 711 L 155 711 L 155 728"/>',
        '<path d="M 958 693 L 958 711 L 389 711 L 389 728"/>',
        '<path d="M 958 693 L 958 711 L 620 711 L 620 728"/>',
        '<path d="M 958 693 L 958 711 L 852 711 L 852 728"/>',
        '<path d="M 958 693 L 958 711 L 1086 711 L 1086 728"/>',
        '<path d="M 958 693 L 958 711 L 1332 711 L 1332 728"/>',
        "</g>",
        '<g font-family="Noto Sans SC, Source Han Sans SC, sans-serif">',
        *[_svg_text(label) for label in labels],
        "</g></svg>",
    ]
    svg_text = "\n".join(svg_lines) + "\n"

    svg_output = PUBLISH_ROOT / f"svg/{semantic_id}.svg"
    png_output = PUBLISH_ROOT / f"png/{semantic_id}-2x.png"
    svg_source = ASSET_ROOT / f"svg/{semantic_id}.svg"
    png_source = ASSET_ROOT / f"png/{semantic_id}-2x.png"
    for directory in {svg_output.parent, png_output.parent, svg_source.parent, png_source.parent}:
        directory.mkdir(parents=True, exist_ok=True)
    svg_output.write_text(svg_text, encoding="utf-8")
    svg_source.write_text(svg_text, encoding="utf-8")

    draw = ImageDraw.Draw(image)
    arrows = [
        [(326, 190), (340, 190)],
        [(574, 263), (588, 263)],
        [(816, 338), (830, 338)],
        [(1064, 390), (1078, 390)],
        [(1202, 510), (1202, 518), (508, 518), (508, 526)],
        [(1202, 510), (1202, 518), (958, 518), (958, 526)],
    ]
    for arrow in arrows:
        _draw_arrow(draw, arrow)
    for x in (155, 389, 620, 852, 1086, 1332):
        _draw_arrow(draw, [(958, 693), (958, 711), (x, 711), (x, 728)])
    for label in labels:
        draw.multiline_text(
            (label.x, label.y),
            label.text,
            font=_font(label.size, label.weight),
            fill=label.color,
            anchor="mm",
            align="center",
            spacing=max(4, label.size // 4),
        )
    image.save(png_output, optimize=True)
    image.save(png_source, optimize=True)

    return InfographicRecord(
        semantic_id=semantic_id,
        source_path="docs/part-01-foundations/ch01-what-is-llm.md",
        source_asset=source.relative_to(ROOT).as_posix(),
        svg_asset=svg_output.relative_to(ROOT).as_posix(),
        png_asset=png_output.relative_to(ROOT).as_posix(),
        width=width,
        height=height,
        source_sha256=_sha256(source),
        svg_sha256=_sha256(svg_output),
        png_sha256=_sha256(png_output),
        generated_with=(
            "built-in imagegen (visual base) + deterministic SVG/Pillow semantic overlay"
        ),
        generated_at="2026-08-09",
    )


def build_pilot_two() -> InfographicRecord:
    semantic_id = "rag-evidence-pipeline-infographic"
    source = ASSET_ROOT / "source/rag-evidence-pipeline-infographic-base.png"
    if not source.is_file():
        raise FileNotFoundError(f"缺少信息图底稿：{source}")
    image = Image.open(source).convert("RGB")
    width, height = image.size
    labels = _pilot_two_labels()
    encoded = base64.b64encode(source.read_bytes()).decode("ascii")
    arrows = [
        [(158, 300), (165, 300)],
        [(285, 300), (293, 300)],
        [(412, 300), (420, 300)],
        [(539, 300), (547, 300)],
        [(850, 300), (857, 300)],
        [(956, 300), (963, 300)],
        [(1061, 300), (1068, 300)],
        [(1167, 300), (1174, 300)],
        [(1277, 300), (1284, 300)],
        [(1387, 300), (1394, 300)],
        [(610, 454), (610, 480), (650, 500)],
        [(786, 500), (820, 480), (1013, 454)],
        [(768, 700), (768, 718)],
    ]

    svg_paths = []
    for points in arrows:
        commands = [f"M {points[0][0]} {points[0][1]}"]
        commands.extend(f"L {x} {y}" for x, y in points[1:])
        svg_paths.append(f'<path d="{" ".join(commands)}"/>')
    svg_lines = [
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">'
        ),
        '<title id="title">RAG：从文档摄取到带引用回答</title>',
        (
            '<desc id="desc">离线摄取将原始文档解析、切分、向量化并发布为版本化索引；'
            "在线查询经过身份权限、混合检索、重排、生成和引用核验；评估结果反馈到数据与检索策略。</desc>"
        ),
        (
            '<defs><marker id="arrow" markerWidth="10" markerHeight="10" refX="8" '
            'refY="5" orient="auto"><path d="M0,0 L10,5 L0,10 z" '
            'fill="#486985"/></marker></defs>'
        ),
        (
            f'<image href="data:image/png;base64,{encoded}" x="0" y="0" '
            f'width="{width}" height="{height}"/>'
        ),
        (
            '<rect x="642" y="642" width="252" height="52" rx="22" '
            'fill="#F7F5F0" fill-opacity="0.94"/>'
        ),
        (
            '<g fill="none" stroke="#486985" stroke-width="4" stroke-linecap="round" '
            'stroke-linejoin="round" marker-end="url(#arrow)">'
        ),
        *svg_paths,
        '</g><g font-family="Noto Sans SC, Source Han Sans SC, sans-serif">',
        *[_svg_text(label) for label in labels],
        "</g></svg>",
    ]
    svg_text = "\n".join(svg_lines) + "\n"

    svg_output = PUBLISH_ROOT / f"svg/{semantic_id}.svg"
    png_output = PUBLISH_ROOT / f"png/{semantic_id}-2x.png"
    svg_source = ASSET_ROOT / f"svg/{semantic_id}.svg"
    png_source = ASSET_ROOT / f"png/{semantic_id}-2x.png"
    for directory in {svg_output.parent, png_output.parent, svg_source.parent, png_source.parent}:
        directory.mkdir(parents=True, exist_ok=True)
    svg_output.write_text(svg_text, encoding="utf-8")
    svg_source.write_text(svg_text, encoding="utf-8")

    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((642, 642, 894, 694), radius=22, fill="#F7F5F0EF")
    for arrow in arrows:
        _draw_arrow(draw, arrow)
    for label in labels:
        draw.multiline_text(
            (label.x, label.y),
            label.text,
            font=_font(label.size, label.weight),
            fill=label.color,
            anchor="mm",
            align="center",
            spacing=max(4, label.size // 4),
        )
    image.save(png_output, optimize=True)
    image.save(png_source, optimize=True)

    return InfographicRecord(
        semantic_id=semantic_id,
        source_path="docs/part-03-rag-and-memory/ch13-rag.md",
        source_asset=source.relative_to(ROOT).as_posix(),
        svg_asset=svg_output.relative_to(ROOT).as_posix(),
        png_asset=png_output.relative_to(ROOT).as_posix(),
        width=width,
        height=height,
        source_sha256=_sha256(source),
        svg_sha256=_sha256(svg_output),
        png_sha256=_sha256(png_output),
        generated_with=(
            "built-in imagegen (visual base) + deterministic SVG/Pillow semantic overlay"
        ),
        generated_at="2026-08-09",
    )


def build_pilot_three() -> InfographicRecord:
    semantic_id = "enterprise-agent-platform-infographic"
    source = ASSET_ROOT / "source/enterprise-agent-platform-infographic-base-v2.png"
    if not source.is_file():
        raise FileNotFoundError(f"缺少信息图底稿：{source}")
    image = Image.open(source).convert("RGB")
    width, height = image.size
    labels = _pilot_three_labels()
    encoded = base64.b64encode(source.read_bytes()).decode("ascii")
    arrows = [
        [(512, 387), (512, 405)],
        [(512, 693), (512, 712)],
        [(512, 970), (512, 989)],
        [(512, 1216), (512, 1234)],
    ]
    svg_paths = []
    for points in arrows:
        commands = [f"M {points[0][0]} {points[0][1]}"]
        commands.extend(f"L {x} {y}" for x, y in points[1:])
        svg_paths.append(f'<path d="{" ".join(commands)}"/>')
    svg_lines = [
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">'
        ),
        '<title id="title">企业 Agent 平台参考架构</title>',
        (
            '<desc id="desc">租户用户和客户端经过 API 身份边界进入 Agent Runtime 与工作流；'
            "运行时组合模型、工具、MCP、RAG、Memory 和规划能力，并依赖队列、Worker、"
            "数据库、向量索引、缓存与对象存储；Trace、Metrics、Audit、Evaluation、Cost、"
            "Policy 与 Security 形成治理证据层。</desc>"
        ),
        (
            '<defs><marker id="arrow" markerWidth="10" markerHeight="10" refX="8" '
            'refY="5" orient="auto"><path d="M0,0 L10,5 L0,10 z" '
            'fill="#486985"/></marker></defs>'
        ),
        (
            f'<image href="data:image/png;base64,{encoded}" x="0" y="0" '
            f'width="{width}" height="{height}"/>'
        ),
        (
            '<g fill="none" stroke="#486985" stroke-width="4" stroke-linecap="round" '
            'stroke-linejoin="round" marker-end="url(#arrow)">'
        ),
        *svg_paths,
        '</g><g font-family="Noto Sans SC, Source Han Sans SC, sans-serif">',
        *[_svg_text(label) for label in labels],
        "</g></svg>",
    ]
    svg_text = "\n".join(svg_lines) + "\n"

    svg_output = PUBLISH_ROOT / f"svg/{semantic_id}.svg"
    png_output = PUBLISH_ROOT / f"png/{semantic_id}-2x.png"
    svg_source = ASSET_ROOT / f"svg/{semantic_id}.svg"
    png_source = ASSET_ROOT / f"png/{semantic_id}-2x.png"
    for directory in {svg_output.parent, png_output.parent, svg_source.parent, png_source.parent}:
        directory.mkdir(parents=True, exist_ok=True)
    svg_output.write_text(svg_text, encoding="utf-8")
    svg_source.write_text(svg_text, encoding="utf-8")

    draw = ImageDraw.Draw(image)
    for arrow in arrows:
        _draw_arrow(draw, arrow)
    for label in labels:
        draw.multiline_text(
            (label.x, label.y),
            label.text,
            font=_font(label.size, label.weight),
            fill=label.color,
            anchor="mm",
            align="center",
            spacing=max(3, label.size // 4),
        )
    published = image.resize(
        (width * 3 // 2, height * 3 // 2),
        resample=Image.Resampling.LANCZOS,
    )
    published.save(png_output, optimize=True)
    published.save(png_source, optimize=True)

    return InfographicRecord(
        semantic_id=semantic_id,
        source_path="docs/part-07-advanced/ch36-architecture.md",
        source_asset=source.relative_to(ROOT).as_posix(),
        svg_asset=svg_output.relative_to(ROOT).as_posix(),
        png_asset=png_output.relative_to(ROOT).as_posix(),
        width=width,
        height=height,
        source_sha256=_sha256(source),
        svg_sha256=_sha256(svg_output),
        png_sha256=_sha256(png_output),
        generated_with=(
            "built-in imagegen (visual base) + deterministic SVG/Pillow semantic overlay"
        ),
        generated_at="2026-08-09",
    )


def _build_portrait_infographic(
    *,
    semantic_id: str,
    title: str,
    description: str,
    source_path: str,
    source_name: str,
    labels: list[Label],
    arrows: list[list[tuple[int, int]]],
    generated_at: str = "2026-08-09",
) -> InfographicRecord:
    """Compose a generated visual base with deterministic semantic overlays."""
    source = ASSET_ROOT / f"source/{source_name}"
    if not source.is_file():
        raise FileNotFoundError(f"缺少信息图底稿：{source}")
    image = Image.open(source).convert("RGB")
    width, height = image.size
    encoded = base64.b64encode(source.read_bytes()).decode("ascii")
    svg_paths = []
    for points in arrows:
        commands = [f"M {points[0][0]} {points[0][1]}"]
        commands.extend(f"L {x} {y}" for x, y in points[1:])
        svg_paths.append(f'<path d="{" ".join(commands)}"/>')
    svg_lines = [
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">'
        ),
        f'<title id="title">{html.escape(title)}</title>',
        f'<desc id="desc">{html.escape(description)}</desc>',
        (
            '<defs><marker id="arrow" markerWidth="10" markerHeight="10" refX="8" '
            'refY="5" orient="auto"><path d="M0,0 L10,5 L0,10 z" '
            'fill="#486985"/></marker></defs>'
        ),
        (
            f'<image href="data:image/png;base64,{encoded}" x="0" y="0" '
            f'width="{width}" height="{height}"/>'
        ),
        (
            '<g fill="none" stroke="#486985" stroke-width="4" stroke-linecap="round" '
            'stroke-linejoin="round" marker-end="url(#arrow)">'
        ),
        *svg_paths,
        '</g><g font-family="Noto Sans SC, Source Han Sans SC, sans-serif">',
        *[_svg_text(label) for label in labels],
        "</g></svg>",
    ]
    svg_text = "\n".join(svg_lines) + "\n"

    svg_output = PUBLISH_ROOT / f"svg/{semantic_id}.svg"
    png_output = PUBLISH_ROOT / f"png/{semantic_id}-2x.png"
    svg_source = ASSET_ROOT / f"svg/{semantic_id}.svg"
    png_source = ASSET_ROOT / f"png/{semantic_id}-2x.png"
    for directory in {svg_output.parent, png_output.parent, svg_source.parent, png_source.parent}:
        directory.mkdir(parents=True, exist_ok=True)
    svg_output.write_text(svg_text, encoding="utf-8")
    svg_source.write_text(svg_text, encoding="utf-8")

    draw = ImageDraw.Draw(image)
    for arrow in arrows:
        _draw_arrow(draw, arrow)
    for label in labels:
        draw.multiline_text(
            (label.x, label.y),
            label.text,
            font=_font(label.size, label.weight),
            fill=label.color,
            anchor="mm",
            align="center",
            spacing=max(3, label.size // 4),
            stroke_width=label.stroke_width,
            stroke_fill="#FFFDF8",
        )
    published = image.resize(
        (width * 3 // 2, height * 3 // 2),
        resample=Image.Resampling.LANCZOS,
    )
    published.save(png_output, optimize=True)
    published.save(png_source, optimize=True)
    return InfographicRecord(
        semantic_id=semantic_id,
        source_path=source_path,
        source_asset=source.relative_to(ROOT).as_posix(),
        svg_asset=svg_output.relative_to(ROOT).as_posix(),
        png_asset=png_output.relative_to(ROOT).as_posix(),
        width=width,
        height=height,
        source_sha256=_sha256(source),
        svg_sha256=_sha256(svg_output),
        png_sha256=_sha256(png_output),
        generated_with=(
            "built-in imagegen (visual base) + deterministic SVG/Pillow semantic overlay"
        ),
        generated_at=generated_at,
    )


def build_transformer_infographic() -> InfographicRecord:
    labels = [
        Label(512, 28, "Transformer：Attention 的信息路由", 27, "bold", "#24476B", 2),
        Label(512, 274, "输入表示：Token Embedding + 位置信息", 21, "bold", "#24476B", 3),
        Label(195, 465, "Query：要找什么", 19, "bold", "#24476B", 3),
        Label(512, 465, "Key：匹配线索", 19, "bold", "#177B72", 3),
        Label(825, 465, "Value：实际内容", 19, "bold", "#C8662D", 3),
        Label(386, 713, "相关性得分 + Softmax", 19, "bold", "#7656A5", 3),
        Label(754, 713, "因果 Mask：不能看未来", 19, "bold", "#4E5968", 3),
        Label(512, 923, "按权重读取 Value，形成上下文表示", 20, "bold", "#7656A5", 3),
        Label(512, 1174, "多头并行 → Concat → 输出投影", 20, "bold", "#24476B", 3),
        Label(274, 1420, "残差 · 归一化 · FFN", 19, "bold", "#7656A5", 3),
        Label(748, 1420, "Decoder-only\n逐 Token 生成", 19, "bold", "#24476B", 3),
    ]
    arrows = [
        [(512, 286), (512, 302)],
        [(512, 483), (512, 496)],
        [(512, 735), (512, 750)],
        [(512, 947), (512, 962)],
        [(512, 1191), (512, 1208)],
    ]
    return _build_portrait_infographic(
        semantic_id="transformer-attention-routing-infographic",
        title="Transformer：Attention 的信息路由",
        description=(
            "输入表示投影为 Query、Key 和 Value，Query 与 Key 计算相关性并应用因果掩码，"
            "归一化权重读取 Value；多头结果拼接后进入残差、归一化和前馈网络，"
            "Decoder-only 模型再逐 Token 解码。"
        ),
        source_path="docs/part-01-foundations/ch03-transformer-attention.md",
        source_name="transformer-attention-infographic-base.png",
        labels=labels,
        arrows=arrows,
    )


def build_agent_runtime_infographic() -> InfographicRecord:
    labels = [
        Label(512, 29, "Agent Runtime：受控决策与执行闭环", 27, "bold", "#24476B", 2),
        Label(170, 230, "人工审批\n允许 · 拒绝", 20, "bold", "#24476B", 3),
        Label(512, 230, "Checkpoint\n状态持久化", 20, "bold", "#177B72", 3),
        Label(854, 230, "预算与超时\n步数 · Token · 成本", 19, "bold", "#B94A48", 3),
        Label(500, 520, "请求与上下文", 21, "bold", "#24476B", 3),
        Label(750, 700, "模型决策\n与计划", 21, "bold", "#177B72", 3),
        Label(680, 1070, "策略门禁\n与工具执行", 21, "bold", "#C8662D", 3),
        Label(350, 1070, "Observation\n与状态更新", 21, "bold", "#7656A5", 3),
        Label(238, 700, "终止检查\n完成 · 暂停 · 失败", 20, "bold", "#B94A48", 3),
        Label(512, 765, "Agent Runtime\n状态、权限和终止权在模型之外", 22, "bold", "#24476B", 3),
        Label(512, 1445, "Trace · 事件 · 审计证据", 21, "bold", "#7656A5", 3),
    ]
    arrows = [
        [(170, 396), (330, 452)],
        [(512, 356), (512, 408)],
        [(854, 396), (694, 452)],
        [(625, 530), (690, 575)],
        [(822, 820), (742, 940)],
        [(590, 1160), (455, 1160)],
        [(260, 1020), (190, 880)],
        [(260, 600), (395, 505)],
        [(512, 1225), (512, 1320)],
    ]
    return _build_portrait_infographic(
        semantic_id="agent-runtime-control-loop-infographic",
        title="Agent Runtime：受控决策与执行闭环",
        description=(
            "Agent Runtime 在请求上下文、模型决策、策略门禁与工具执行、观察状态更新、"
            "终止检查之间循环；人工审批、Checkpoint、预算超时和 Trace 审计形成外部控制边界。"
        ),
        source_path="docs/part-02-agent-core/ch09-agent-runtime.md",
        source_name="agent-runtime-control-loop-infographic-base.png",
        labels=labels,
        arrows=arrows,
    )


def build_mcp_infographic() -> InfographicRecord:
    labels = [
        Label(512, 27, "MCP：协议层、能力层与信任边界", 27, "bold", "#24476B", 2),
        Label(285, 130, "Host / Agent 应用", 23, "bold", "#24476B", 3),
        Label(664, 390, "MCP Client", 22, "bold", "#177B72", 3),
        Label(162, 714, "能力发现\n（可选）", 18, "bold", "#177B72", 3),
        Label(417, 714, "每请求元数据\n版本 · Client 信息", 18, "bold", "#177B72", 3),
        Label(670, 714, "stdio / HTTP\n传输边界", 18, "bold", "#177B72", 3),
        Label(168, 1138, "MCP Server A", 16, "bold", "#7656A5", 3),
        Label(416, 1138, "MCP Server B", 16, "bold", "#7656A5", 3),
        Label(666, 1138, "MCP Server C", 16, "bold", "#7656A5", 3),
        Label(145, 1407, "文件系统", 18, "bold", "#C8662D", 3),
        Label(330, 1407, "数据库", 18, "bold", "#C8662D", 3),
        Label(513, 1407, "代码仓库", 18, "bold", "#C8662D", 3),
        Label(698, 1407, "REST 服务", 18, "bold", "#C8662D", 3),
        Label(910, 115, "信任边界", 17, "bold", "#4E5968", 3),
        Label(910, 365, "主体身份", 17, "bold", "#24476B", 3),
        Label(910, 625, "用户同意", 17, "bold", "#177B72", 3),
        Label(910, 890, "最小权限", 17, "bold", "#C8662D", 3),
        Label(910, 1160, "审计记录", 17, "bold", "#B94A48", 3),
    ]
    arrows = [
        [(512, 478), (512, 510)],
        [(512, 766), (512, 805)],
        [(512, 1200), (512, 1230)],
    ]
    return _build_portrait_infographic(
        semantic_id="mcp-protocol-boundary-infographic",
        title="MCP：协议层、能力层与信任边界",
        description=(
            "宿主应用中的 MCP Client 通过可选能力发现和每请求元数据，经 stdio 或 HTTP 调用"
            "多个 MCP Server；Server 暴露 Tool、Resource 与 Prompt，并受主体身份、用户同意、"
            "最小权限和审计约束后访问文件、数据库、代码仓库与 REST 服务。"
        ),
        source_path="docs/part-03-rag-and-memory/ch11-mcp.md",
        source_name="mcp-protocol-boundary-infographic-base.png",
        labels=labels,
        arrows=arrows,
    )


def build_memory_infographic() -> InfographicRecord:
    labels = [
        Label(512, 27, "Agent Memory：写入、检索与遗忘生命周期", 27, "bold", "#24476B", 2),
        Label(285, 218, "候选信息：对话与动作事件", 20, "bold", "#24476B", 3),
        Label(750, 218, "当前任务上下文与历史状态", 20, "bold", "#177B72", 3),
        Label(512, 292, "长期记忆写入门禁", 23, "bold", "#C8662D", 3),
        Label(224, 451, "未来价值", 16, "bold", "#C8662D", 3),
        Label(365, 451, "用户同意", 16, "bold", "#C8662D", 3),
        Label(510, 451, "敏感性", 16, "bold", "#C8662D", 3),
        Label(650, 451, "来源置信", 16, "bold", "#C8662D", 3),
        Label(795, 451, "冲突检查", 16, "bold", "#C8662D", 3),
        Label(150, 748, "Tenant / Subject\n隔离边界", 17, "bold", "#177B72", 3),
        Label(350, 620, "用户偏好", 19, "bold", "#24476B", 3),
        Label(580, 620, "语义事实", 19, "bold", "#177B72", 3),
        Label(810, 620, "情景事件", 19, "bold", "#7656A5", 3),
        Label(512, 935, "Memory Store：来源 · 版本 · TTL · 敏感级别", 19, "bold", "#24476B", 3),
        Label(150, 1105, "权限过滤", 16, "bold", "#7656A5", 3),
        Label(330, 1105, "时效过滤", 16, "bold", "#7656A5", 3),
        Label(510, 1105, "相关性排序", 16, "bold", "#7656A5", 3),
        Label(780, 1105, "注入短期上下文", 17, "bold", "#7656A5", 3),
        Label(160, 1315, "纠错", 16, "bold", "#B94A48", 3),
        Label(330, 1315, "TTL 过期", 16, "bold", "#B94A48", 3),
        Label(510, 1315, "删除传播", 16, "bold", "#B94A48", 3),
        Label(685, 1315, "恢复后再删除", 16, "bold", "#B94A48", 3),
        Label(850, 1315, "无原值审计", 16, "bold", "#B94A48", 3),
        Label(512, 1475, "主记录 · 向量索引 · 缓存 · 派生摘要", 18, "bold", "#24476B", 3),
    ]
    arrows = [
        [(512, 255), (512, 278)],
        [(512, 553), (512, 560)],
        [(512, 945), (512, 968)],
        [(512, 1148), (512, 1174)],
    ]
    return _build_portrait_infographic(
        semantic_id="memory-governed-lifecycle-infographic",
        title="Agent Memory：写入、检索与遗忘生命周期",
        description="候选交互信息经过未来价值、用户同意、敏感性、来源和冲突门禁，按租户主体隔离写入偏好、语义事实和情景事件；读取先做权限时效过滤，生命周期支持纠错、过期、删除传播和审计。",
        source_path="docs/part-03-rag-and-memory/ch15-memory.md",
        source_name="memory-lifecycle-infographic-base.png",
        labels=labels,
        arrows=arrows,
    )


def build_langgraph_infographic() -> InfographicRecord:
    labels = [
        Label(512, 27, "LangGraph：显式状态与可恢复工作流", 27, "bold", "#24476B", 2),
        Label(512, 205, "StateSnapshot：Schema · thread_id · 版本", 21, "bold", "#24476B", 3),
        Label(108, 680, "并行更新\nReducer 合并", 18, "bold", "#177B72", 3),
        Label(292, 500, "Plan", 20, "bold", "#24476B", 3),
        Label(485, 500, "Research", 20, "bold", "#177B72", 3),
        Label(680, 500, "Review", 20, "bold", "#7656A5", 3),
        Label(292, 950, "Interrupt\n人工审批", 18, "bold", "#C8662D", 3),
        Label(485, 950, "Write", 20, "bold", "#177B72", 3),
        Label(680, 950, "Finish", 20, "bold", "#24476B", 3),
        Label(900, 500, "Checkpoint\n每个 super-step", 17, "bold", "#7656A5", 3),
        Label(900, 1030, "持久化与恢复", 17, "bold", "#7656A5", 3),
        Label(132, 1280, "Interrupt\n暂停", 18, "bold", "#B94A48", 3),
        Label(385, 1280, "Command(resume)\n同一 thread_id", 17, "bold", "#177B72", 3),
        Label(635, 1280, "Retry\n有限且计入预算", 17, "bold", "#C8662D", 3),
        Label(880, 1280, "Time Travel\n形成新分支", 17, "bold", "#7656A5", 3),
        Label(512, 1480, "外部副作用：幂等键 · Outbox · 状态核对", 19, "bold", "#4E5968", 3),
    ]
    arrows = [
        [(292, 635), (390, 635)],
        [(485, 635), (585, 635)],
        [(680, 635), (680, 770), (292, 770), (292, 815)],
        [(380, 950), (395, 950)],
        [(575, 950), (590, 950)],
        [(795, 650), (810, 650)],
        [(512, 1120), (512, 1140)],
    ]
    return _build_portrait_infographic(
        semantic_id="langgraph-recoverable-workflow-infographic",
        title="LangGraph：显式状态与可恢复工作流",
        description=(
            "LangGraph 用 StateSnapshot、Node、Edge 和 Reducer 表达工作流，每个 super-step "
            "保存 Checkpoint；Interrupt 暂停交给人工并以同一 thread_id 恢复，Retry 与 "
            "Time Travel 都可能重执行节点，外部副作用必须幂等。"
        ),
        source_path="docs/part-04-frameworks/ch20-langgraph.md",
        source_name="langgraph-recoverable-workflow-infographic-base.png",
        labels=labels,
        arrows=arrows,
    )


def build_observability_infographic() -> InfographicRecord:
    labels = [
        Label(512, 27, "Agent Observability：从一次 Run 到治理证据", 27, "bold", "#24476B", 2),
        Label(195, 112, "API", 16, "bold", "#24476B", 3),
        Label(340, 112, "Queue / Worker", 16, "bold", "#24476B", 3),
        Label(488, 112, "Agent Run", 16, "bold", "#24476B", 3),
        Label(488, 270, "Model Span", 17, "bold", "#24476B", 3),
        Label(205, 420, "Retrieval", 16, "bold", "#24476B", 3),
        Label(350, 420, "Tool", 16, "bold", "#24476B", 3),
        Label(500, 420, "Guardrail", 16, "bold", "#24476B", 3),
        Label(650, 420, "Checkpoint", 16, "bold", "#24476B", 3),
        Label(805, 420, "Approval", 16, "bold", "#24476B", 3),
        Label(140, 735, "Logs\n离散事件与错误", 19, "bold", "#24476B", 3),
        Label(385, 735, "Metrics\n趋势、SLO 与告警", 19, "bold", "#177B72", 3),
        Label(635, 735, "Traces\n跨组件因果路径", 19, "bold", "#C8662D", 3),
        Label(885, 735, "Audit\n主体与受保护动作", 19, "bold", "#7656A5", 3),
        Label(105, 1190, "Token", 16, "bold", "#C8662D", 3),
        Label(225, 1190, "Cost", 16, "bold", "#C8662D", 3),
        Label(350, 1190, "首 Token", 16, "bold", "#C8662D", 3),
        Label(485, 1190, "P95 / P99", 16, "bold", "#C8662D", 3),
        Label(615, 1190, "任务成功", 16, "bold", "#C8662D", 3),
        Label(740, 1190, "Tool 错误", 16, "bold", "#C8662D", 3),
        Label(900, 1190, "告警 → run_id\n→ 错误定位", 16, "bold", "#B94A48", 3),
        Label(210, 1450, "字段 allowlist", 16, "bold", "#177B72", 3),
        Label(365, 1450, "脱敏", 16, "bold", "#177B72", 3),
        Label(525, 1450, "采样", 16, "bold", "#177B72", 3),
        Label(685, 1450, "保留期", 16, "bold", "#177B72", 3),
        Label(850, 1450, "访问审计", 16, "bold", "#177B72", 3),
    ]
    arrows = [
        [(488, 135), (488, 165)],
        [(488, 250), (488, 295)],
        [(488, 550), (488, 600)],
        [(512, 1010), (512, 1035)],
        [(512, 1250), (512, 1275)],
    ]
    return _build_portrait_infographic(
        semantic_id="agent-observability-evidence-infographic",
        title="Agent Observability：从一次 Run 到治理证据",
        description=(
            "一次 Agent Run 通过跨服务 Trace 连接模型、检索、工具、策略、Checkpoint 与审批；"
            "Logs、Metrics、Traces 和 Audit 分工记录事件、趋势、因果与授权证据，并在隐私"
            "治理下支持成本延迟和失败定位。"
        ),
        source_path="docs/part-05-engineering/ch28-observability.md",
        source_name="agent-observability-infographic-base.png",
        labels=labels,
        arrows=arrows,
    )


def build_security_infographic() -> InfographicRecord:
    labels = [
        Label(512, 26, "Agent 安全：不可绕过的纵深防御", 27, "bold", "#24476B", 2),
        Label(150, 190, "网页", 17, "bold", "#B94A48", 3),
        Label(350, 190, "邮件", 17, "bold", "#B94A48", 3),
        Label(550, 190, "文档", 17, "bold", "#B94A48", 3),
        Label(720, 190, "文件", 17, "bold", "#B94A48", 3),
        Label(430, 360, "不可信内容与模型决策区", 22, "bold", "#B94A48", 3),
        Label(410, 475, "来源标记与上下文隔离", 19, "bold", "#177B72", 3),
        Label(410, 580, "主体身份与对象授权", 19, "bold", "#177B72", 3),
        Label(410, 685, "Tool 参数、网络与文件 allowlist", 18, "bold", "#177B72", 3),
        Label(410, 790, "Sandbox：进程、文件、网络、资源", 18, "bold", "#177B72", 3),
        Label(410, 895, "风险分级与人工审批绑定", 19, "bold", "#177B72", 3),
        Label(410, 1000, "执行前重新校验主体、资源与状态", 18, "bold", "#177B72", 3),
        Label(175, 1225, "受限工具", 20, "bold", "#24476B", 3),
        Label(420, 1225, "敏感数据", 20, "bold", "#C8662D", 3),
        Label(680, 1225, "外部副作用", 20, "bold", "#7656A5", 3),
        Label(915, 185, "Secret 隔离", 17, "bold", "#24476B", 3),
        Label(915, 485, "最小权限", 17, "bold", "#24476B", 3),
        Label(915, 780, "预算与终止", 17, "bold", "#24476B", 3),
        Label(915, 1080, "租户边界", 17, "bold", "#24476B", 3),
        Label(160, 1445, "不可篡改 Audit", 17, "bold", "#7656A5", 3),
        Label(410, 1445, "安全测试", 17, "bold", "#7656A5", 3),
        Label(650, 1445, "告警", 17, "bold", "#7656A5", 3),
        Label(870, 1445, "事件响应", 17, "bold", "#7656A5", 3),
    ]
    arrows = [
        [(410, 400), (410, 418)],
        [(410, 510), (410, 525)],
        [(410, 615), (410, 630)],
        [(410, 720), (410, 735)],
        [(410, 825), (410, 840)],
        [(410, 930), (410, 945)],
        [(410, 1035), (410, 1055)],
        [(512, 1325), (512, 1350)],
    ]
    return _build_portrait_infographic(
        semantic_id="agent-security-trust-boundary-infographic",
        title="Agent 安全：不可绕过的纵深防御",
        description=(
            "网页邮件文档等不可信内容进入模型后，动作仍必须依次经过上下文隔离、主体与对象"
            "授权、参数与网络 allowlist、Sandbox、风险审批和执行前重校验；Secret、权限、"
            "预算、租户与审计边界均在模型之外强制执行。"
        ),
        source_path="docs/part-05-engineering/ch30-security.md",
        source_name="agent-security-boundary-infographic-base.png",
        labels=labels,
        arrows=arrows,
    )


def build_multi_agent_infographic() -> InfographicRecord:
    labels = [
        Label(512, 26, "Multi-Agent：显式协调、共享状态与终止", 27, "bold", "#24476B", 2),
        Label(120, 170, "Supervisor", 21, "bold", "#24476B", 3),
        Label(370, 110, "任务契约", 18, "bold", "#24476B", 3),
        Label(730, 180, "验收 Rubric · 预算 · 允许工具", 19, "bold", "#24476B", 3),
        Label(190, 470, "Worker A\n检索与数据", 20, "bold", "#177B72", 3),
        Label(510, 470, "Worker B\n文档与分析", 20, "bold", "#4B7D3A", 3),
        Label(830, 470, "Worker C\n工具与执行", 20, "bold", "#C8662D", 3),
        Label(512, 650, "每个 Worker 使用独立的最小权限 Scope", 19, "bold", "#4E5968", 3),
        Label(110, 800, "Handoff\nMessage Envelope", 17, "bold", "#177B72", 3),
        Label(
            512,
            835,
            "Typed Blackboard\nTask State · Artifact · Evidence · Version",
            21,
            "bold",
            "#7656A5",
            3,
        ),
        Label(910, 800, "Shared Memory\nArtifact Store", 17, "bold", "#177B72", 3),
        Label(512, 1110, "Reviewer：独立 Rubric · 通过 / 返工", 20, "bold", "#C8662D", 3),
        Label(130, 1415, "依赖 DAG", 17, "bold", "#B94A48", 3),
        Label(315, 1415, "Deadlock 检测", 17, "bold", "#B94A48", 3),
        Label(500, 1415, "回合 · Cost · 时间", 17, "bold", "#B94A48", 3),
        Label(690, 1415, "无进展检测", 17, "bold", "#B94A48", 3),
        Label(880, 1415, "Done / Failed", 17, "bold", "#B94A48", 3),
    ]
    arrows = [
        [(512, 300), (190, 328)],
        [(512, 300), (510, 328)],
        [(512, 300), (830, 328)],
        [(190, 678), (350, 720)],
        [(510, 678), (510, 720)],
        [(830, 678), (670, 720)],
        [(512, 1025), (512, 1045)],
        [(512, 1215), (512, 1235)],
    ]
    return _build_portrait_infographic(
        semantic_id="multi-agent-coordination-infographic",
        title="Multi-Agent：显式协调、共享状态与终止",
        description=(
            "Supervisor 按任务契约和预算分派 Worker，每个 Worker 使用独立最小权限并向类型化"
            "Blackboard 提交版本化 Artifact 与 Evidence；Reviewer 独立验收，运行时通过依赖、"
            "死锁、预算、无进展和完成条件可靠终止。"
        ),
        source_path="docs/part-07-advanced/ch32-multi-agent-principles.md",
        source_name="multi-agent-coordination-infographic-base.png",
        labels=labels,
        arrows=arrows,
    )


def build_project10_infographic() -> InfographicRecord:
    labels = [
        Label(512, 26, "项目 10：企业 Agent 平台部署拓扑", 27, "bold", "#24476B", 2),
        Label(145, 205, "Tenant 用户与管理员", 18, "bold", "#24476B", 3),
        Label(335, 150, "OIDC 身份", 17, "bold", "#24476B", 3),
        Label(485, 150, "租户策略", 17, "bold", "#24476B", 3),
        Label(635, 150, "限流与配额", 17, "bold", "#24476B", 3),
        Label(785, 150, "请求过滤", 17, "bold", "#24476B", 3),
        Label(560, 315, "Ingress / Load Balancer", 20, "bold", "#24476B", 3),
        Label(275, 530, "API 实例 × N", 21, "bold", "#177B72", 3),
        Label(
            700,
            500,
            "控制面发布\nAgent · Tool · MCP · Prompt\nPolicy · Version",
            18,
            "bold",
            "#177B72",
            3,
        ),
        Label(150, 850, "PostgreSQL\n权威 Run 状态", 19, "bold", "#C8662D", 3),
        Label(390, 850, "Redis\n可恢复唤醒信号", 19, "bold", "#C8662D", 3),
        Label(700, 850, "Worker Pool\n租约 · 幂等 · 取消", 20, "bold", "#C8662D", 3),
        Label(130, 1060, "Agent Runtime", 16, "bold", "#7656A5", 3),
        Label(315, 1060, "Model Gateway", 16, "bold", "#7656A5", 3),
        Label(500, 1060, "Tool / MCP", 16, "bold", "#7656A5", 3),
        Label(675, 1060, "RAG / pgvector", 16, "bold", "#7656A5", 3),
        Label(835, 1060, "Approval", 16, "bold", "#7656A5", 3),
        Label(250, 1255, "PostgreSQL · Redis\nObject Store", 15, "bold", "#24476B", 3),
        Label(675, 1255, "Trace · Evaluation\nAudit · Metrics", 15, "bold", "#24476B", 3),
        Label(125, 1440, "Health", 14, "bold", "#B94A48", 3),
        Label(280, 1440, "有限\nRetry", 14, "bold", "#B94A48", 3),
        Label(430, 1440, "Tenant\nDLQ", 14, "bold", "#B94A48", 3),
        Label(580, 1440, "Backup", 14, "bold", "#B94A48", 3),
        Label(740, 1440, "恢复\n演练", 14, "bold", "#B94A48", 3),
        Label(890, 1440, "Secret\n边界", 14, "bold", "#B94A48", 3),
        Label(950, 120, "接入层", 16, "bold", "#FFFFFF", 1),
        Label(950, 455, "服务层", 16, "bold", "#FFFFFF", 1),
        Label(950, 760, "执行层", 16, "bold", "#FFFFFF", 1),
        Label(950, 980, "能力层", 16, "bold", "#FFFFFF", 1),
        Label(950, 1190, "证据层", 16, "bold", "#FFFFFF", 1),
        Label(950, 1390, "运维层", 16, "bold", "#FFFFFF", 1),
    ]
    arrows = [
        [(560, 365), (560, 383)],
        [(275, 645), (275, 665)],
        [(390, 645), (390, 665)],
        [(700, 645), (700, 665)],
        [(700, 900), (700, 920)],
        [(512, 1115), (512, 1135)],
        [(512, 1305), (512, 1325)],
    ]
    return _build_portrait_infographic(
        semantic_id="project10-enterprise-deployment-infographic",
        title="项目 10：企业 Agent 平台部署拓扑",
        description=(
            "多租户请求经 OIDC、策略、限流和入口进入横向 API；PostgreSQL 先提交权威 Run 状态，"
            "Redis 仅发送可恢复唤醒信号，Worker 组合模型、工具、MCP、RAG 和审批并写入存储与"
            "治理证据；健康检查、有限重试、租户 DLQ、备份恢复和 Secret 构成运维边界。"
        ),
        source_path="projects/10-enterprise-platform/README.md",
        source_name="project10-deployment-topology-infographic-base.png",
        labels=labels,
        arrows=arrows,
    )


@dataclass(frozen=True, slots=True)
class PortraitSpec:
    semantic_id: str
    title: str
    description: str
    source_path: str
    source_name: str
    labels: tuple[Label, ...]


_B_FLOW_ARROWS = (
    ((512, 305), (512, 325)),
    ((512, 625), (512, 645)),
    ((512, 930), (512, 950)),
    ((512, 1235), (512, 1255)),
)


def _b_specs() -> dict[str, PortraitSpec]:
    """Return the locked B-level publication infographic specifications."""
    specs = (
        PortraitSpec(
            "context-budget-memory-infographic",
            "上下文窗口：有限预算，不是长期记忆",
            "一次请求先为规则、问题和输出预留硬预算，再在历史、证据和工具结果间分配弹性预算；超限时按价值保留、截断、摘要或外部检索，会话结束后只有显式写入外部存储的信息才能在未来恢复。",
            "docs/part-01-foundations/ch02-token-and-context.md",
            "context-budget-memory-infographic-base.png",
            (
                Label(512, 28, "上下文窗口：有限预算，不是长期记忆", 27, "bold", "#24476B", 3),
                Label(210, 195, "系统规则\n硬约束", 18, "bold", "#24476B", 3),
                Label(512, 195, "当前问题与证据\n任务工作区", 18, "bold", "#177B72", 3),
                Label(815, 195, "工具与历史\n竞争剩余容量", 18, "bold", "#C8662D", 3),
                Label(170, 555, "固定保留", 19, "bold", "#24476B", 3),
                Label(512, 555, "弹性预算", 19, "bold", "#177B72", 3),
                Label(850, 555, "输出预留", 19, "bold", "#C8662D", 3),
                Label(128, 810, "保留", 17, "bold", "#24476B", 3),
                Label(382, 810, "截断", 17, "bold", "#7656A5", 3),
                Label(640, 810, "摘要", 17, "bold", "#177B72", 3),
                Label(890, 810, "外部检索", 17, "bold", "#177B72", 3),
                Label(512, 1085, "成本 · 延迟 · 信息密度", 21, "bold", "#7656A5", 3),
                Label(250, 1400, "持久存储", 19, "bold", "#24476B", 3),
                Label(512, 1400, "按需检索", 19, "bold", "#177B72", 3),
                Label(795, 1400, "下一次上下文", 19, "bold", "#C8662D", 3),
            ),
        ),
        PortraitSpec(
            "generation-control-infographic",
            "生成控制：采样、运行边界与结构化输出",
            (
                "模型从概率分布中选择下一个 Token；Temperature、Top-p 和 Top-k 改变候选"
                "分布，运行时再施加长度、停止与流式边界，结构化结果只有通过语法、"
                "Schema 和业务校验后才能交给下游。"
            ),
            "docs/part-01-foundations/ch04-generation.md",
            "generation-control-infographic-base.png",
            (
                Label(512, 25, "生成控制：从概率分布到可靠结果", 27, "bold", "#24476B", 3),
                Label(512, 185, "Logits → 概率分布 → 候选 Token", 20, "bold", "#24476B", 3),
                Label(170, 505, "Temperature\n分布形状", 18, "bold", "#24476B", 3),
                Label(512, 505, "Top-p\n累计概率", 18, "bold", "#177B72", 3),
                Label(850, 505, "Top-k\n候选数量", 18, "bold", "#C8662D", 3),
                Label(130, 820, "随机种子", 16, "bold", "#7656A5", 3),
                Label(380, 820, "最大长度", 16, "bold", "#7656A5", 3),
                Label(640, 820, "停止条件", 16, "bold", "#7656A5", 3),
                Label(875, 820, "流式事件", 16, "bold", "#7656A5", 3),
                Label(175, 1110, "语法解析", 17, "bold", "#177B72", 3),
                Label(430, 1110, "Schema 校验", 17, "bold", "#177B72", 3),
                Label(680, 1110, "有限重试", 17, "bold", "#C8662D", 3),
                Label(870, 1110, "明确失败", 17, "bold", "#B94A48", 3),
                Label(512, 1400, "按任务复杂度路由普通模型与推理模型", 19, "bold", "#24476B", 3),
            ),
        ),
        PortraitSpec(
            "embedding-retrieval-evidence-infographic",
            "Embedding：从相关候选到可引用证据",
            "文档经过清洗、切分、元数据和向量化形成版本化索引；查询同时使用稀疏与稠密检索，经融合、权限过滤和重排后，还必须验证相关性、可见性、时效与主张支持关系。",
            "docs/part-01-foundations/ch05-embedding.md",
            "embedding-evidence-infographic-base.png",
            (
                Label(512, 25, "Embedding：从相关候选到可引用证据", 27, "bold", "#24476B", 3),
                Label(160, 190, "解析与清洗", 17, "bold", "#24476B", 3),
                Label(390, 190, "Chunk + Metadata", 17, "bold", "#24476B", 3),
                Label(640, 190, "向量表示", 17, "bold", "#177B72", 3),
                Label(865, 190, "版本化索引", 17, "bold", "#177B72", 3),
                Label(245, 525, "稀疏检索\n关键词与编号", 18, "bold", "#24476B", 3),
                Label(775, 525, "稠密检索\n语义改写", 18, "bold", "#177B72", 3),
                Label(170, 835, "租户与 ACL", 18, "bold", "#C8662D", 3),
                Label(510, 835, "融合与 Rerank", 18, "bold", "#7656A5", 3),
                Label(840, 835, "Top-k + 来源", 18, "bold", "#7656A5", 3),
                Label(125, 1110, "相关", 16, "bold", "#24476B", 3),
                Label(375, 1110, "可见", 16, "bold", "#177B72", 3),
                Label(625, 1110, "时效", 16, "bold", "#C8662D", 3),
                Label(875, 1110, "支持主张", 16, "bold", "#B94A48", 3),
                Label(
                    512,
                    1400,
                    "真实查询集 → Recall / MRR → 引用与 Faithfulness",
                    18,
                    "bold",
                    "#7656A5",
                    3,
                ),
            ),
        ),
        PortraitSpec(
            "prompt-context-injection-infographic",
            "Prompt 与 Context：指令层级和注入防线",
            (
                "平台与系统约束高于用户任务，检索网页邮件等外部内容始终是数据而非新"
                "指令；Context Assembly 只装入必要材料，任何工具动作仍在模型外通过"
                "授权、白名单和审批。"
            ),
            "docs/part-02-agent-core/ch06-prompt-engineering.md",
            "prompt-injection-context-infographic-base.png",
            (
                Label(512, 25, "Prompt 与 Context：指令层级和注入防线", 27, "bold", "#24476B", 3),
                Label(320, 105, "平台与系统约束", 18, "bold", "#24476B", 3),
                Label(320, 185, "用户任务", 18, "bold", "#177B72", 3),
                Label(320, 265, "示例与历史", 18, "bold", "#7656A5", 3),
                Label(820, 185, "网页 · 邮件 · 文档\n不可信内容", 18, "bold", "#B94A48", 3),
                Label(
                    512,
                    545,
                    "Context Assembly：规则 + 任务 + 最小证据 + 输出契约",
                    18,
                    "bold",
                    "#177B72",
                    3,
                ),
                Label(160, 825, "来源标记", 16, "bold", "#B94A48", 3),
                Label(365, 825, "数据 / 指令隔离", 16, "bold", "#C8662D", 3),
                Label(575, 825, "Tool Allowlist", 16, "bold", "#177B72", 3),
                Label(775, 825, "主体授权", 16, "bold", "#24476B", 3),
                Label(920, 825, "人工审批", 16, "bold", "#7656A5", 3),
                Label(250, 1115, "模型输出：动作提议", 19, "bold", "#7656A5", 3),
                Label(745, 1115, "模型外策略执行点", 19, "bold", "#24476B", 3),
                Label(512, 1400, "版本 · 测试集 · Trace · 回归", 20, "bold", "#7656A5", 3),
            ),
        ),
        PortraitSpec(
            "structured-output-validation-infographic",
            "Structured Output：契约、校验与恢复",
            (
                "业务契约先映射为版本化 Schema，模型候选依次经过解析、Schema 和业务"
                "校验；只有完整对象通过验收后才提交下游，失败按可修复性进入有限重试"
                "或明确拒绝。"
            ),
            "docs/part-02-agent-core/ch07-structured-output.md",
            "structured-output-validation-infographic-base.png",
            (
                Label(512, 25, "Structured Output：契约、校验与恢复", 27, "bold", "#24476B", 3),
                Label(250, 180, "业务需求", 18, "bold", "#24476B", 3),
                Label(515, 180, "JSON Schema / Pydantic", 18, "bold", "#24476B", 3),
                Label(820, 180, "模型候选对象", 18, "bold", "#177B72", 3),
                Label(255, 520, "语法解析", 18, "bold", "#177B72", 3),
                Label(510, 520, "Schema 校验", 18, "bold", "#177B72", 3),
                Label(760, 520, "业务规则", 18, "bold", "#C8662D", 3),
                Label(250, 825, "可修复格式错误", 16, "bold", "#C8662D", 3),
                Label(512, 825, "字段 / 类型错误", 16, "bold", "#7656A5", 3),
                Label(760, 825, "不可重试拒绝", 16, "bold", "#B94A48", 3),
                Label(900, 825, "重试预算", 16, "bold", "#C8662D", 3),
                Label(250, 1110, "流式部分：仅预览", 18, "bold", "#7656A5", 3),
                Label(650, 1110, "完整验收后提交", 18, "bold", "#177B72", 3),
                Label(
                    512, 1400, "Schema 版本 · 兼容迁移 · 错误样本 · 回归", 18, "bold", "#24476B", 3
                ),
            ),
        ),
        PortraitSpec(
            "tool-permission-execution-infographic",
            "Tool Calling：权限、审批、幂等与审计",
            (
                "模型只提出工具动作，Runtime 依次完成注册表检查、参数校验、主体资源"
                "授权和风险分级；高风险动作绑定人工审批，执行器再施加超时、Sandbox、"
                "幂等和状态核对。"
            ),
            "docs/part-02-agent-core/ch08-tool-calling.md",
            "tool-permission-execution-infographic-base.png",
            (
                Label(512, 25, "Tool Calling：模型提议，Runtime 执行", 27, "bold", "#24476B", 3),
                Label(250, 180, "工具动作提议", 18, "bold", "#24476B", 3),
                Label(770, 180, "注册表 + 参数 Schema", 18, "bold", "#24476B", 3),
                Label(130, 505, "未知工具拒绝", 16, "bold", "#B94A48", 3),
                Label(385, 505, "参数校验", 16, "bold", "#177B72", 3),
                Label(640, 505, "主体 / 资源授权", 16, "bold", "#177B72", 3),
                Label(885, 505, "风险分级", 16, "bold", "#C8662D", 3),
                Label(170, 810, "只读", 18, "bold", "#177B72", 3),
                Label(512, 810, "可逆写入", 18, "bold", "#C8662D", 3),
                Label(850, 810, "不可逆写入\n绑定人工审批", 18, "bold", "#B94A48", 3),
                Label(110, 1100, "超时", 15, "bold", "#7656A5", 3),
                Label(305, 1100, "Allowlist", 15, "bold", "#7656A5", 3),
                Label(505, 1100, "Sandbox", 15, "bold", "#7656A5", 3),
                Label(700, 1100, "幂等键", 15, "bold", "#7656A5", 3),
                Label(890, 1100, "状态核对", 15, "bold", "#7656A5", 3),
                Label(512, 1400, "Observation · 步数预算 · 终止 · Audit", 19, "bold", "#24476B", 3),
            ),
        ),
        PortraitSpec(
            "planning-review-replan-infographic",
            "研究型 Agent：规划、执行、评审与重规划",
            (
                "Planner 将目标分解为带依赖、预算和验收条件的任务，Executor 只执行"
                "当前就绪节点并提交证据，Reviewer 依据独立 Rubric 决定通过、局部返工"
                "或整体重规划。"
            ),
            "docs/part-02-agent-core/ch10-planning-reflection.md",
            "planning-review-replan-infographic-base.png",
            (
                Label(512, 25, "研究型 Agent：规划、执行、评审与重规划", 27, "bold", "#24476B", 3),
                Label(160, 175, "用户目标", 18, "bold", "#24476B", 3),
                Label(510, 175, "任务 DAG + 验收条件", 18, "bold", "#24476B", 3),
                Label(865, 175, "回合 · 成本 · 时间", 17, "bold", "#C8662D", 3),
                Label(250, 520, "Planner\n约束计划", 19, "bold", "#24476B", 3),
                Label(745, 520, "Executor\n搜索 · 阅读 · 工具", 19, "bold", "#177B72", 3),
                Label(512, 625, "显式共享状态", 17, "bold", "#7656A5", 3),
                Label(105, 820, "Evidence", 15, "bold", "#24476B", 3),
                Label(305, 820, "Artifact", 15, "bold", "#177B72", 3),
                Label(505, 820, "状态", 15, "bold", "#C8662D", 3),
                Label(705, 820, "成本", 15, "bold", "#7656A5", 3),
                Label(900, 820, "版本", 15, "bold", "#4E5968", 3),
                Label(
                    512, 1110, "Reviewer：通过 · 局部返工 · 整体重规划", 19, "bold", "#7656A5", 3
                ),
                Label(255, 1400, "预算与无进展终止", 18, "bold", "#B94A48", 3),
                Label(750, 1400, "带来源最终报告", 18, "bold", "#24476B", 3),
            ),
        ),
        PortraitSpec(
            "mcp-server-lifecycle-infographic",
            "MCP Server：生命周期、传输与生产边界",
            (
                "MCP Server 启动后注册能力并与 Client 协商；stdio 和远程 HTTP 具有"
                "不同进程与认证边界，每次调用仍要执行参数、主体、资源范围、超时和"
                "结果限制，最终支持取消和优雅关闭。"
            ),
            "docs/part-03-rag-and-memory/ch12-mcp-server.md",
            "mcp-server-lifecycle-infographic-base.png",
            (
                Label(512, 25, "MCP Server：生命周期、传输与生产边界", 27, "bold", "#24476B", 3),
                Label(165, 180, "启动与配置", 18, "bold", "#24476B", 3),
                Label(500, 180, "能力注册", 18, "bold", "#177B72", 3),
                Label(835, 180, "Tool · Resource · Prompt", 17, "bold", "#177B72", 3),
                Label(250, 500, "初始化与能力协商", 18, "bold", "#24476B", 3),
                Label(750, 500, "发现能力 ≠ 获得权限", 18, "bold", "#7656A5", 3),
                Label(250, 820, "stdio\n本地进程边界", 18, "bold", "#177B72", 3),
                Label(750, 820, "远程 HTTP\n认证与会话", 18, "bold", "#C8662D", 3),
                Label(120, 1110, "参数", 15, "bold", "#177B72", 3),
                Label(300, 1110, "主体权限", 15, "bold", "#24476B", 3),
                Label(500, 1110, "资源范围", 15, "bold", "#177B72", 3),
                Label(690, 1110, "超时", 15, "bold", "#C8662D", 3),
                Label(875, 1110, "结构化错误", 15, "bold", "#B94A48", 3),
                Label(
                    512,
                    1400,
                    "stderr 日志 · 健康 · 取消 · 优雅关闭 · 测试",
                    18,
                    "bold",
                    "#7656A5",
                    3,
                ),
            ),
        ),
        PortraitSpec(
            "advanced-rag-diagnostic-infographic",
            "高级 RAG：按失败类型选择纠错策略",
            (
                "高级 RAG 先定位失败发生在召回、排名、时效冲突、上下文噪声还是生成"
                "忠实度，再选择查询改写、重排、校验、压缩或拒答；Graph、Agentic 与"
                "多模态 RAG 只是按需侧路。"
            ),
            "docs/part-03-rag-and-memory/ch14-advanced-rag.md",
            "advanced-rag-diagnostic-infographic-base.png",
            (
                Label(512, 25, "高级 RAG：按失败类型选择纠错策略", 27, "bold", "#24476B", 3),
                Label(512, 165, "查询分类与改写", 19, "bold", "#24476B", 3),
                Label(115, 430, "Parent-Child\n语义切分", 15, "bold", "#24476B", 3),
                Label(310, 430, "Metadata\n过滤", 15, "bold", "#177B72", 3),
                Label(510, 430, "Multi-Query", 15, "bold", "#177B72", 3),
                Label(705, 430, "Hybrid", 15, "bold", "#7656A5", 3),
                Label(900, 430, "Reranking", 15, "bold", "#C8662D", 3),
                Label(110, 730, "无召回", 14, "bold", "#24476B", 3),
                Label(310, 730, "排名低", 14, "bold", "#177B72", 3),
                Label(510, 730, "冲突 / 过期", 14, "bold", "#B94A48", 3),
                Label(705, 730, "上下文噪声", 14, "bold", "#7656A5", 3),
                Label(900, 730, "回答不忠实", 14, "bold", "#C8662D", 3),
                Label(110, 1015, "扩大 / 改写", 14, "bold", "#24476B", 3),
                Label(310, 1015, "重排", 14, "bold", "#177B72", 3),
                Label(510, 1015, "时效冲突校验", 14, "bold", "#B94A48", 3),
                Label(705, 1015, "Context 压缩", 14, "bold", "#7656A5", 3),
                Label(900, 1015, "拒答 / 纠错检索", 14, "bold", "#C8662D", 3),
                Label(410, 1275, "引用回答 → 评估 → 失败样本回灌", 18, "bold", "#7656A5", 3),
                Label(900, 1380, "Graph · Agentic · 多模态\n按需侧路", 16, "bold", "#4E5968", 3),
            ),
        ),
        PortraitSpec(
            "vector-index-migration-infographic",
            "向量索引：检索、迁移与多租户隔离",
            (
                "摄取记录绑定文档、切分器、Embedding 与租户版本；查询先施加权限和"
                "元数据过滤，再使用 HNSW 或 IVF 等索引；模型变更通过影子构建、双读、"
                "原子切换和回滚完成。"
            ),
            "docs/part-03-rag-and-memory/ch16-vector-databases.md",
            "vector-index-migration-infographic-base.png",
            (
                Label(512, 25, "向量索引：检索、迁移与多租户隔离", 27, "bold", "#24476B", 3),
                Label(160, 175, "文档 / Chunk 版本", 16, "bold", "#24476B", 3),
                Label(390, 175, "Embedding 版本", 16, "bold", "#177B72", 3),
                Label(630, 175, "向量与距离", 16, "bold", "#177B72", 3),
                Label(850, 175, "租户 Metadata", 16, "bold", "#7656A5", 3),
                Label(180, 505, "HNSW\n近邻图", 18, "bold", "#24476B", 3),
                Label(510, 505, "IVF\n聚类分桶", 18, "bold", "#177B72", 3),
                Label(840, 505, "精确基线", 18, "bold", "#4E5968", 3),
                Label(145, 820, "租户 / ACL 过滤", 16, "bold", "#24476B", 3),
                Label(430, 820, "ANN 搜索", 16, "bold", "#177B72", 3),
                Label(690, 820, "候选重排", 16, "bold", "#7656A5", 3),
                Label(880, 820, "可见结果", 16, "bold", "#24476B", 3),
                Label(260, 1110, "活动索引", 17, "bold", "#24476B", 3),
                Label(512, 1110, "双读验证 · 原子切换 · 回滚", 17, "bold", "#7656A5", 3),
                Label(770, 1110, "影子索引", 17, "bold", "#177B72", 3),
                Label(512, 1400, "更新 / 撤权 / 删除传播与审计", 19, "bold", "#B94A48", 3),
            ),
        ),
        PortraitSpec(
            "native-agent-runtime-infographic",
            "原生 Agent Runtime：内核、端口与测试边界",
            (
                "传输和模型供应商位于适配层，确定性 Runtime 内核负责状态、工具、策略、"
                "超时、预算和终止；模型、检索、工具和存储通过端口替换为真实适配器或"
                "离线 Fake。"
            ),
            "docs/part-04-frameworks/ch17-native-api.md",
            "native-agent-runtime-infographic-base.png",
            (
                Label(
                    512, 25, "原生 Agent Runtime：内核、端口与测试边界", 27, "bold", "#24476B", 3
                ),
                Label(200, 175, "任务请求", 18, "bold", "#24476B", 3),
                Label(512, 175, "不可变 Run 配置", 18, "bold", "#7656A5", 3),
                Label(820, 175, "消息与响应", 18, "bold", "#177B72", 3),
                Label(170, 480, "模型适配器", 17, "bold", "#177B72", 3),
                Label(512, 480, "消息 + Tool Schema", 17, "bold", "#177B72", 3),
                Label(850, 480, "结构化动作解析", 17, "bold", "#177B72", 3),
                Label(512, 720, "确定性 Runtime 内核", 22, "bold", "#24476B", 3),
                Label(190, 790, "状态 · Tool Registry · Policy", 15, "bold", "#24476B", 3),
                Label(825, 790, "超时 · Retry · 预算 · 终止", 15, "bold", "#24476B", 3),
                Label(105, 1085, "Model", 15, "bold", "#7656A5", 3),
                Label(305, 1085, "Retrieval", 15, "bold", "#177B72", 3),
                Label(510, 1085, "Tool", 15, "bold", "#C8662D", 3),
                Label(710, 1085, "Storage", 15, "bold", "#24476B", 3),
                Label(905, 1085, "Fake / Mock", 15, "bold", "#B94A48", 3),
                Label(
                    512,
                    1400,
                    "Event Log · Trace · Checkpoint · 测试金字塔",
                    18,
                    "bold",
                    "#7656A5",
                    3,
                ),
            ),
        ),
        PortraitSpec(
            "openai-agents-sdk-concepts-infographic",
            "OpenAI Agents SDK：运行、工具、护栏与交接",
            (
                "Runner 驱动一次 Run 并维护上下文，Agent 组合指令、模型、工具和输出"
                "契约；Guardrail 约束输入输出，Handoff 只移交最小必要上下文，Session、"
                "MCP 和 Tracing 提供外围能力。"
            ),
            "docs/part-04-frameworks/ch18-openai-agents-sdk.md",
            "openai-agents-sdk-infographic-base.png",
            (
                Label(512, 25, "Agents SDK：运行、工具、护栏与交接", 27, "bold", "#24476B", 3),
                Label(250, 155, "任务", 18, "bold", "#C8662D", 3),
                Label(512, 155, "Runner / Run", 20, "bold", "#C8662D", 3),
                Label(512, 390, "上下文与运行控制", 20, "bold", "#24476B", 3),
                Label(130, 690, "Instructions", 15, "bold", "#177B72", 3),
                Label(315, 690, "Model", 15, "bold", "#177B72", 3),
                Label(512, 690, "Agent", 17, "bold", "#177B72", 3),
                Label(700, 690, "Tools", 15, "bold", "#177B72", 3),
                Label(885, 690, "Output Type", 15, "bold", "#7656A5", 3),
                Label(255, 1010, "Input Guardrail", 17, "bold", "#B94A48", 3),
                Label(512, 1010, "Tool Loop", 17, "bold", "#C8662D", 3),
                Label(770, 1010, "Output Guardrail", 17, "bold", "#B94A48", 3),
                Label(512, 1165, "Handoff：最小必要上下文", 18, "bold", "#24476B", 3),
                Label(95, 950, "Session", 15, "bold", "#177B72", 3),
                Label(930, 950, "MCP · Trace", 15, "bold", "#7656A5", 3),
                Label(
                    512,
                    1400,
                    "成功 · 护栏拒绝 · 工具失败 · 超预算 · 人工中断",
                    17,
                    "bold",
                    "#B94A48",
                    3,
                ),
            ),
        ),
        PortraitSpec(
            "agent-api-transport-infographic",
            "Agent API：同步、流式与异步任务边界",
            (
                "请求先通过认证、租户、限流和校验，再按任务性质选择同步、SSE、"
                "WebSocket 或异步 Job；长任务的权威状态写数据库并由 Worker 执行，"
                "客户端断线不等于任务丢失。"
            ),
            "docs/part-05-engineering/ch24-fastapi.md",
            "agent-api-transport-infographic-base.png",
            (
                Label(512, 25, "Agent API：同步、流式与异步任务边界", 27, "bold", "#24476B", 3),
                Label(120, 180, "客户端", 16, "bold", "#24476B", 3),
                Label(310, 180, "认证", 16, "bold", "#24476B", 3),
                Label(500, 180, "租户策略", 16, "bold", "#177B72", 3),
                Label(690, 180, "限流", 16, "bold", "#177B72", 3),
                Label(875, 180, "请求校验", 16, "bold", "#24476B", 3),
                Label(130, 520, "短任务\n同步响应", 17, "bold", "#24476B", 3),
                Label(385, 520, "SSE\n单向事件流", 17, "bold", "#177B72", 3),
                Label(640, 520, "WebSocket\n双向交互", 17, "bold", "#7656A5", 3),
                Label(885, 520, "异步 Job", 17, "bold", "#C8662D", 3),
                Label(200, 855, "创建 Run", 18, "bold", "#24476B", 3),
                Label(512, 855, "权威状态", 18, "bold", "#24476B", 3),
                Label(820, 855, "Queue / Worker", 18, "bold", "#C8662D", 3),
                Label(
                    512, 1120, "序号 · 重连 · 取消 · 超时 · 背压 · 幂等", 18, "bold", "#7656A5", 3
                ),
                Label(
                    512, 1400, "Health · OpenAPI · Mock · Trace · Audit", 18, "bold", "#24476B", 3
                ),
            ),
        ),
        PortraitSpec(
            "agent-data-storage-infographic",
            "Agent 数据：按语义选择权威存储",
            (
                "用户、会话、Run、Artifact、Memory、向量、缓存和审计具有不同一致性"
                "与生命周期；PostgreSQL 保存权威事务状态，Redis 只承担可重建缓存和"
                "唤醒信号。"
            ),
            "docs/part-05-engineering/ch25-storage.md",
            "agent-data-storage-infographic-base.png",
            (
                Label(512, 25, "Agent 数据：按语义选择权威存储", 27, "bold", "#24476B", 3),
                Label(70, 180, "租户", 13, "bold", "#24476B", 3),
                Label(195, 180, "会话", 13, "bold", "#177B72", 3),
                Label(320, 180, "Run", 13, "bold", "#24476B", 3),
                Label(445, 180, "Artifact", 13, "bold", "#C8662D", 3),
                Label(570, 180, "Memory", 13, "bold", "#7656A5", 3),
                Label(695, 180, "Vector", 13, "bold", "#177B72", 3),
                Label(820, 180, "Cache", 13, "bold", "#B94A48", 3),
                Label(945, 180, "Audit", 13, "bold", "#C8662D", 3),
                Label(110, 500, "PostgreSQL", 16, "bold", "#24476B", 3),
                Label(315, 500, "Object Store", 16, "bold", "#C8662D", 3),
                Label(510, 500, "Vector Index", 16, "bold", "#177B72", 3),
                Label(710, 500, "Redis", 16, "bold", "#B94A48", 3),
                Label(905, 500, "Audit Store", 16, "bold", "#7656A5", 3),
                Label(410, 810, "PostgreSQL：权威状态与幂等记录", 19, "bold", "#24476B", 3),
                Label(790, 810, "Redis 丢失后可重建", 17, "bold", "#B94A48", 3),
                Label(
                    512,
                    1110,
                    "Checkpoint · Migration · Version · Tenant · Delete",
                    17,
                    "bold",
                    "#7656A5",
                    3,
                ),
                Label(
                    512,
                    1400,
                    "Backup · Restore Drill · Rollback · Consistency",
                    18,
                    "bold",
                    "#24476B",
                    3,
                ),
            ),
        ),
        PortraitSpec(
            "agent-deployment-release-infographic",
            "Agent 部署：镜像、拓扑、健康与可恢复发布",
            (
                "多阶段构建生成固定版本的最小运行镜像，配置和 Secret 从镜像外注入；"
                "API、Worker 与存储分离部署，通过存活、就绪、滚动发布、迁移和回滚"
                "形成可恢复交付链。"
            ),
            "docs/part-05-engineering/ch26-docker-deployment.md",
            "agent-deployment-release-infographic-base.png",
            (
                Label(
                    512, 25, "Agent 部署：镜像、拓扑、健康与可恢复发布", 27, "bold", "#24476B", 3
                ),
                Label(180, 175, "依赖构建", 18, "bold", "#24476B", 3),
                Label(512, 175, "最小运行镜像", 18, "bold", "#24476B", 3),
                Label(840, 175, "非 root · 固定版本", 18, "bold", "#24476B", 3),
                Label(180, 500, "Secret 外置", 18, "bold", "#7656A5", 3),
                Label(480, 500, "开发", 16, "bold", "#177B72", 3),
                Label(680, 500, "测试", 16, "bold", "#24476B", 3),
                Label(875, 500, "生产", 16, "bold", "#C8662D", 3),
                Label(170, 810, "Ingress", 16, "bold", "#24476B", 3),
                Label(470, 810, "API × N", 17, "bold", "#24476B", 3),
                Label(790, 810, "Worker × N", 17, "bold", "#7656A5", 3),
                Label(512, 940, "PostgreSQL · Redis · Object Store", 17, "bold", "#177B72", 3),
                Label(175, 1110, "启动 / 存活 / 就绪", 17, "bold", "#177B72", 3),
                Label(512, 1110, "滚动发布与连接排空", 17, "bold", "#24476B", 3),
                Label(850, 1110, "有限 Retry 与降级", 17, "bold", "#B94A48", 3),
                Label(
                    512,
                    1400,
                    "CI Gate · Scan · Migration · Backup · Trace · Rollback",
                    17,
                    "bold",
                    "#7656A5",
                    3,
                ),
            ),
        ),
        PortraitSpec(
            "job-queue-reliability-infographic",
            "长任务队列：租约、重试、取消与 DLQ",
            (
                "API 在事务中创建 Job 和 Outbox，Worker 只有取得有效租约后才能执行并"
                "保存 Checkpoint；失败按类型分类，只有幂等暂时故障在预算内重试，"
                "耗尽后进入 DLQ。"
            ),
            "docs/part-05-engineering/ch27-job-queues.md",
            "job-queue-reliability-infographic-base.png",
            (
                Label(512, 25, "长任务队列：租约、重试、取消与 DLQ", 27, "bold", "#24476B", 3),
                Label(160, 180, "API", 17, "bold", "#24476B", 3),
                Label(470, 180, "Job + Outbox\n同一事务", 18, "bold", "#24476B", 3),
                Label(780, 180, "发布唤醒信号", 18, "bold", "#C8662D", 3),
                Label(180, 505, "Queue", 17, "bold", "#24476B", 3),
                Label(510, 505, "Worker 竞争 Lease", 19, "bold", "#177B72", 3),
                Label(835, 505, "Heartbeat\nCheckpoint", 17, "bold", "#177B72", 3),
                Label(90, 790, "排队", 14, "bold", "#24476B", 3),
                Label(260, 790, "运行", 14, "bold", "#177B72", 3),
                Label(430, 790, "成功", 14, "bold", "#177B72", 3),
                Label(600, 790, "失败", 14, "bold", "#B94A48", 3),
                Label(770, 790, "取消", 14, "bold", "#C8662D", 3),
                Label(935, 790, "未知", 14, "bold", "#7656A5", 3),
                Label(160, 1050, "暂时故障", 14, "bold", "#24476B", 3),
                Label(360, 1050, "限流", 14, "bold", "#177B72", 3),
                Label(560, 1050, "业务 / 权限拒绝", 14, "bold", "#C8662D", 3),
                Label(750, 1050, "超时未知", 14, "bold", "#B94A48", 3),
                Label(900, 1120, "DLQ", 17, "bold", "#7656A5", 3),
                Label(
                    512,
                    1400,
                    "协作取消 · 僵尸回收 · 定时防重 · DLQ 审批重放",
                    17,
                    "bold",
                    "#24476B",
                    3,
                ),
            ),
        ),
        PortraitSpec(
            "agent-evaluation-pipeline-infographic",
            "Agent Evaluation：分层指标与持续回归",
            (
                "评估从任务契约和版本化 Golden Dataset 开始，分别验证单元、集成、"
                "端到端和人工评审；指标按工具、检索、证据、任务、成本与延迟分解，"
                "变更必须通过回归门。"
            ),
            "docs/part-05-engineering/ch29-evaluation.md",
            "agent-evaluation-pipeline-infographic-base.png",
            (
                Label(512, 25, "Agent Evaluation：分层指标与持续回归", 27, "bold", "#24476B", 3),
                Label(170, 175, "任务契约", 18, "bold", "#24476B", 3),
                Label(500, 175, "成功 Rubric", 18, "bold", "#24476B", 3),
                Label(835, 175, "Golden Dataset", 18, "bold", "#24476B", 3),
                Label(125, 505, "单元", 15, "bold", "#24476B", 3),
                Label(365, 505, "集成", 15, "bold", "#177B72", 3),
                Label(605, 505, "端到端", 15, "bold", "#177B72", 3),
                Label(845, 505, "人工评审", 15, "bold", "#7656A5", 3),
                Label(80, 775, "结构化输出", 13, "bold", "#24476B", 3),
                Label(225, 775, "Tool", 13, "bold", "#177B72", 3),
                Label(370, 775, "Retrieval", 13, "bold", "#177B72", 3),
                Label(515, 775, "Faithfulness", 13, "bold", "#C8662D", 3),
                Label(660, 775, "任务成功", 13, "bold", "#B94A48", 3),
                Label(805, 775, "成本", 13, "bold", "#C8662D", 3),
                Label(940, 775, "延迟", 13, "bold", "#7656A5", 3),
                Label(
                    512,
                    1095,
                    "Judge：Rubric · 盲测 · 位置交换 · 校准 · 人工抽检",
                    17,
                    "bold",
                    "#7656A5",
                    3,
                ),
                Label(
                    512,
                    1400,
                    "版本变更 → 基线对比 → 退化门禁 → 失败切片 → 回灌",
                    17,
                    "bold",
                    "#B94A48",
                    3,
                ),
            ),
        ),
        PortraitSpec(
            "cost-quality-latency-infographic",
            "成本优化：质量、延迟与单位任务成本",
            "成本必须按成功任务而非单次调用衡量；优化先消除无效循环和错误重试，再压缩上下文与工具集合，随后采用模型路由、缓存、批处理和安全并行。",
            "docs/part-05-engineering/ch31-cost-performance.md",
            "cost-quality-latency-infographic-base.png",
            (
                Label(512, 25, "成本优化：质量、延迟与单位任务成本", 27, "bold", "#24476B", 3),
                Label(95, 230, "模型 Token", 14, "bold", "#24476B", 3),
                Label(300, 230, "检索 / 重排", 14, "bold", "#177B72", 3),
                Label(505, 230, "Tool", 14, "bold", "#C8662D", 3),
                Label(705, 230, "存储 / 队列", 14, "bold", "#7656A5", 3),
                Label(905, 230, "失败 Retry", 14, "bold", "#B94A48", 3),
                Label(512, 520, "任务成功：不可牺牲的硬约束", 19, "bold", "#B94A48", 3),
                Label(330, 625, "质量", 18, "bold", "#24476B", 3),
                Label(512, 625, "P95 延迟", 18, "bold", "#177B72", 3),
                Label(700, 625, "单位任务成本", 18, "bold", "#C8662D", 3),
                Label(130, 885, "先消除循环\n与错误重试", 16, "bold", "#B94A48", 3),
                Label(365, 885, "再缩上下文\n与工具集合", 16, "bold", "#177B72", 3),
                Label(610, 885, "模型路由\n缓存与 Batch", 16, "bold", "#24476B", 3),
                Label(845, 885, "最后调参数\n安全并行", 16, "bold", "#7656A5", 3),
                Label(250, 1120, "小模型：分类 · 路由 · 抽取", 17, "bold", "#177B72", 3),
                Label(755, 1120, "大模型：高复杂度步骤", 17, "bold", "#7656A5", 3),
                Label(
                    512,
                    1400,
                    "预算 · 上限 · 超时 · 熔断 · 降级 · 压测 · 告警",
                    18,
                    "bold",
                    "#24476B",
                    3,
                ),
            ),
        ),
        PortraitSpec(
            "browser-agent-safety-infographic",
            "Browser Agent：感知、动作、验证与恢复",
            (
                "Browser Agent 综合 DOM、截图、OCR、URL 与会话状态定位目标，优先使用"
                "稳定语义选择器；每次有限动作后必须重新观测验证，异常进入恢复分支，"
                "高风险操作绑定确认和审计。"
            ),
            "docs/part-07-advanced/ch34-browser-computer-use.md",
            "browser-agent-safety-infographic-base.png",
            (
                Label(512, 25, "Browser Agent：感知、动作、验证与恢复", 27, "bold", "#24476B", 3),
                Label(120, 180, "DOM / 可访问性树", 15, "bold", "#24476B", 3),
                Label(370, 180, "Screenshot", 15, "bold", "#24476B", 3),
                Label(625, 180, "OCR", 15, "bold", "#177B72", 3),
                Label(865, 180, "URL / Session", 15, "bold", "#24476B", 3),
                Label(260, 500, "语义选择器优先", 18, "bold", "#177B72", 3),
                Label(760, 500, "视觉坐标降级", 18, "bold", "#7656A5", 3),
                Label(512, 750, "点击 · 输入 · 滚动 · 下载 · 上传", 18, "bold", "#177B72", 3),
                Label(220, 865, "重新观测", 17, "bold", "#24476B", 3),
                Label(820, 865, "验证预期状态", 17, "bold", "#177B72", 3),
                Label(100, 1080, "页面变化", 13, "bold", "#B94A48", 3),
                Label(280, 1080, "遮挡 / 弹窗", 13, "bold", "#B94A48", 3),
                Label(465, 1080, "网络超时", 13, "bold", "#B94A48", 3),
                Label(650, 1080, "重复提交", 13, "bold", "#B94A48", 3),
                Label(835, 1080, "登录过期", 13, "bold", "#B94A48", 3),
                Label(
                    512,
                    1400,
                    "凭证隔离 · 域名 Allowlist · 下载 Sandbox · 确认 · 脱敏 Audit",
                    16,
                    "bold",
                    "#24476B",
                    3,
                ),
            ),
        ),
        PortraitSpec(
            "framework-selection-map-infographic",
            "Agent 技术选型：从问题形态到渐进架构",
            (
                "技术选型先建立确定性、状态恢复、类型安全、RAG、协作、MCP、团队和"
                "锁定风险画像，再从原生闭环渐进增加 SDK、图工作流、数据框架或"
                "多 Agent，并用 Spike 与评估验证。"
            ),
            "docs/part-07-advanced/ch38-selection-guide.md",
            "framework-selection-map-infographic-base.png",
            (
                Label(512, 25, "Agent 技术选型：从问题形态到渐进架构", 27, "bold", "#24476B", 3),
                Label(
                    512,
                    210,
                    "需求画像：确定性 · 恢复 · 类型 · RAG · 协作 · MCP · 锁定",
                    18,
                    "bold",
                    "#24476B",
                    3,
                ),
                Label(110, 520, "原生 API", 15, "bold", "#24476B", 3),
                Label(310, 520, "类型安全 SDK", 15, "bold", "#177B72", 3),
                Label(510, 520, "图式工作流", 15, "bold", "#C8662D", 3),
                Label(710, 520, "RAG 数据框架", 15, "bold", "#7656A5", 3),
                Label(910, 520, "Multi-Agent", 15, "bold", "#B94A48", 3),
                Label(120, 820, "评价维度", 16, "bold", "#24476B", 3),
                Label(325, 820, "可控性", 14, "bold", "#177B72", 3),
                Label(500, 820, "学习成本", 14, "bold", "#C8662D", 3),
                Label(675, 820, "工作流 / RAG", 14, "bold", "#7656A5", 3),
                Label(850, 820, "协作 / 运维", 14, "bold", "#B94A48", 3),
                Label(
                    512,
                    1110,
                    "先原生闭环 → 再恢复状态 → 再复杂数据 → 最后真实协作",
                    17,
                    "bold",
                    "#24476B",
                    3,
                ),
                Label(
                    512,
                    1400,
                    "Spike · Golden Dataset · 故障注入 · 迁移出口 · TCO",
                    18,
                    "bold",
                    "#7656A5",
                    3,
                ),
            ),
        ),
    )
    return {spec.semantic_id: spec for spec in specs}


def build_b_infographic(semantic_id: str) -> InfographicRecord:
    spec = _b_specs()[semantic_id]
    return _build_portrait_infographic(
        semantic_id=spec.semantic_id,
        title=spec.title,
        description=spec.description,
        source_path=spec.source_path,
        source_name=spec.source_name,
        labels=list(spec.labels),
        arrows=[list(points) for points in _B_FLOW_ARROWS],
        generated_at="2026-08-11",
    )


@dataclass(frozen=True, slots=True)
class FiveStageSpec:
    semantic_id: str
    title: str
    description: str
    source_path: str
    source_name: str
    stages: tuple[str, str, str, str, str]


def _five_stage_specs() -> dict[str, FiveStageSpec]:
    """Publication overlays that complete chapter and project infographic coverage."""
    specs = (
        FiveStageSpec(
            "pydanticai-type-contract-infographic",
            "PydanticAI：类型契约贯穿请求链路",
            "类型化输入、Agent、依赖、工具和输出形成可测试契约；权限与事实校验仍由领域服务负责，校验失败只在共享预算内有限重试。",
            "docs/part-04-frameworks/ch19-pydanticai.md",
            "pydanticai-type-contract-infographic-base.png",
            (
                "类型化请求契约",
                "Agent · 模型适配边界",
                "Dependencies · Tool · 外部服务",
                "输出校验 · 有限重试 · 明确失败",
                "FastAPI · Fake · Trace · 回归",
            ),
        ),
        FiveStageSpec(
            "framework-layer-boundaries-infographic",
            "框架分层：按问题选择，不让框架侵入领域",
            "稳定领域接口之下，LangChain 组织组件、LangGraph 管理可恢复状态、"
            "LlamaIndex 组织文档检索；适配器连接基础能力并保留测试与迁移出口。",
            "docs/part-04-frameworks/ch21-langchain-llamaindex.md",
            "framework-layer-boundaries-infographic-base.png",
            (
                "业务问题 · 稳定领域接口",
                "组件编排 · 状态图 · 文档检索",
                "可替换 Adapter 边界",
                "模型 · 向量库 · Tool · Storage",
                "Spike · 回归数据集 · 迁移出口",
            ),
        ),
        FiveStageSpec(
            "multi-agent-framework-decision-infographic",
            "Multi-Agent：先证明必要，再选择协作模式",
            "任务先与单 Agent 和确定性工作流比较；确需多角色时，以类型化共享状态"
            "交换工件，并用成本、权限、死锁和终止门约束协作。",
            "docs/part-04-frameworks/ch22-multi-agent-frameworks.md",
            "multi-agent-framework-decision-infographic-base.png",
            (
                "任务价值与必要性判断",
                "单 Agent · Workflow · Supervisor · Role Team",
                "Typed State · Artifact · Evidence",
                "回合 · Token · 延迟 · 权限 · Deadlock",
                "Baseline 对照 · 任务成功率 · 去留决策",
            ),
        ),
        FiveStageSpec(
            "python-agent-engineering-infographic",
            "Python Agent：从环境到发布的质量流水线",
            "Python 3.12 项目以锁定依赖和外置 Secret 起步，通过类型、依赖注入、"
            "异步边界、Fake 和故障测试，最终由静态检查与测试门交付。",
            "docs/part-05-engineering/ch23-python-engineering.md",
            "python-agent-engineering-infographic-base.png",
            (
                "Python 3.12 · pyproject · 依赖锁定",
                "Settings · Secret · 类型 · 依赖注入",
                "async · httpx Timeout · Logging · Exception",
                "Unit · Fake · Integration · Fault Injection",
                "Ruff · Format · mypy · pytest · Build",
            ),
        ),
        FiveStageSpec(
            "coding-agent-patch-transaction-infographic",
            "Coding Agent：隔离的补丁事务",
            "Agent 只读理解源仓库，在一次性 Git 工作区应用受限补丁并运行有界测试；"
            "失败销毁工作区，只有独立验收通过后才导出工件。",
            "docs/part-07-advanced/ch33-agentic-coding.md",
            "coding-agent-patch-transaction-infographic-base.png",
            (
                "只读 Repo Map · Search · Plan",
                "受保护源仓库 → 一次性 Git 工作区",
                "Path Allowlist · Size · apply --check",
                "受限 Test · Timeout · 失败销毁",
                "Reviewer Evidence → 导出 Patch / Commit",
            ),
        ),
        FiveStageSpec(
            "multimodal-evidence-infographic",
            "多模态 Agent：统一证据，不丢定位与时间",
            "图像、音频、视频和文档经模态处理后保留页码、区域、时间戳与来源，汇聚为统一证据对象，再进入检索、推断、引用与治理闭环。",
            "docs/part-07-advanced/ch35-multimodal.md",
            "multimodal-evidence-infographic-base.png",
            (
                "图像 · 音频 · 视频 · 复杂文档",
                "OCR · 转写 · 帧采样 · 版面解析",
                "Evidence Object：来源 · 页码 · 区域 · 时间",
                "检索 · 关联 · 推断 · Tool · 未知边界",
                "引用 · 人审 · 脱敏 · 成本质量评估",
            ),
        ),
        FiveStageSpec(
            "demo-to-product-infographic",
            "从 Demo 到产品：可靠性交付闭环",
            "产品先限定用户任务和不可做事项，再建设可中断体验、可靠状态与审批、"
            "SLA 和治理指标，并通过真实反馈和回归持续发布。",
            "docs/part-07-advanced/ch37-demo-to-product.md",
            "demo-to-product-infographic-base.png",
            (
                "用户任务 · 产品边界 · 不可做事项",
                "Streaming · Progress · Interrupt · Retry · Citation",
                "State · Idempotency · Approval · Permission · Fallback",
                "Quality · Cost · Latency · SLA · Trace · Security",
                "Feedback · Eval · Canary · Migration · Upgrade",
            ),
        ),
        FiveStageSpec(
            "project01-minimal-assistant-infographic",
            "项目 1：最小 AI Assistant",
            "请求加载配置与历史，在上下文预算内调用模型并输出明确流式事件；用量、"
            "延迟、日志和错误可观测，Fake 让离线测试无需付费 API。",
            "projects/01-minimal-assistant/README.md",
            "project01-minimal-assistant-infographic-base.png",
            (
                "请求 · Settings · Session",
                "历史裁剪 · 上下文预算 · Model Adapter",
                "Started · Delta · Completed · Error",
                "Token · Cost · Latency · Structured Log",
                "Fake Provider · Timeout · Test · Local Run",
            ),
        ),
        FiveStageSpec(
            "project02-weather-tool-agent-infographic",
            "项目 2：天气与工具调用 Agent",
            "模型提出工具动作，Runtime 负责注册表、Schema、权限和依赖校验；"
            "高风险动作需人工确认，执行受超时、重试、幂等和终止预算约束。",
            "projects/02-weather-tool-agent/README.md",
            "project02-weather-tool-agent-infographic-base.png",
            (
                "用户意图 · Tool Registry",
                "Action Proposal · Schema · Dependency",
                "天气 · 位置 · 风险 Tool · Human Approval",
                "Timeout · Retry · Idempotency · Merge",
                "Observation → Model · Step / Cost / Done",
            ),
        ),
        FiveStageSpec(
            "project03-mcp-local-agent-infographic",
            "项目 3：MCP 本地工具 Agent",
            "Host 中的 Client 通过 stdio 管理 Server 生命周期，发现受限文件、系统和"
            "数据库能力；每次调用仍受工作目录、SQL、参数、超时与结果边界约束。",
            "projects/03-mcp-local-agent/README.md",
            "project03-mcp-local-agent-infographic-base.png",
            (
                "Host · Agent · MCP Client",
                "stdio · Initialize · Capability Discovery",
                "File Scope · System Read · Parameterized DB",
                "Allowlist · Validation · Timeout · stderr",
                "Result · Cancel · Graceful Shutdown · Test",
            ),
        ),
        FiveStageSpec(
            "project04-knowledge-agent-infographic",
            "项目 4：企业知识库 Agent",
            "多格式文档经过解析质量、Chunk、元数据和 ACL 形成版本化索引；在线查询"
            "先鉴权再混合检索和重排，回答保留引用并进入评估回归。",
            "projects/04-knowledge-agent/README.md",
            "project04-knowledge-agent-infographic-base.png",
            (
                "PDF · Word · PPT · Markdown",
                "Parse · Layout · Chunk · Metadata · ACL",
                "Embedding · Versioned pgvector · Rollback",
                "Identity · Hybrid Search · Filter · Rerank",
                "Cited Answer · Recall · MRR · Faithfulness",
            ),
        ),
        FiveStageSpec(
            "project05-code-review-agent-infographic",
            "项目 5：代码 Review Agent",
            "只读仓库与 Diff 经范围过滤和脱敏后，确定性规则、测试证据和模型审查"
            "并行产出发现；合并报告默认离线，外部评论必须显式审批。",
            "projects/05-code-review-agent/README.md",
            "project05-code-review-agent-infographic-base.png",
            (
                "Read-only Repo · Base · PR Diff",
                "Scope · Binary / Size Filter · Secret Redaction",
                "Static Rules · Test Evidence · LLM Review",
                "Dedup · Risk · Confidence · False-positive Control",
                "Markdown / JSON · Approval · Idempotent PR Comment",
            ),
        ),
        FiveStageSpec(
            "project06-office-agent-infographic",
            "项目 6：自动办公 Agent",
            "邮件日历只读摄取后形成结构化草稿；审批绑定内容、目标、主体和时效，"
            "持久 Outbox 用租约、有限重试与幂等键保证恢复而不重复外发。",
            "projects/06-office-agent/README.md",
            "project06-office-agent-infographic-base.png",
            (
                "Mail · Calendar · Office Data：只读",
                "Summary · Daily Report · Outbound Draft",
                "Approval：Content · Target · Principal · Expiry",
                "Persistent Outbox · Lease · Retry · Idempotency",
                "Publish Once · Restart Recovery · Audit",
            ),
        ),
        FiveStageSpec(
            "project07-stock-research-agent-infographic",
            "项目 7：股票研究 Agent",
            "行情、新闻、公告和财报绑定统一时点并经质量校验；报告严格区分确定性指标、事实、模型推断、风险和未知，保留来源且不提供确定性买卖建议。",
            "projects/07-stock-research-agent/README.md",
            "project07-stock-research-agent-infographic-base.png",
            (
                "行情 · 新闻 · 公告 · 财报 · 统一时点",
                "时间 · 时区 · 缺失 · 数据质量",
                "指标计算 · 行业事实 · 模型分析",
                "事实与来源 · 推断 · 风险 · 未知",
                "生成时间 · 截止时间 · 引用 · 非投资建议",
            ),
        ),
        FiveStageSpec(
            "project08-research-workflow-infographic",
            "项目 8：LangGraph 研究工作流",
            "任务经 Planner 形成依赖计划，研究节点更新类型化 State；Checkpoint 支持"
            "有限重试和恢复，Reviewer 与人工中断控制返工，最终报告保留来源和运行证据。",
            "projects/08-research-workflow/README.md",
            "project08-research-workflow-infographic-base.png",
            (
                "任务契约 · Planner · Dependency Plan",
                "Search · Read · Extract · Organize → State",
                "Checkpoint · Retry · Resume · Idempotency",
                "Reviewer · Local Rework · Replan · Human Interrupt",
                "Cited Report · Trace · Cost · Version · Replay",
            ),
        ),
        FiveStageSpec(
            "project09-multi-agent-dev-infographic",
            "项目 9：Multi-Agent 软件开发团队",
            "五种职责通过类型化共享状态交换工件，不进行无界闲聊；代码只在一次性"
            "工作区执行，独立评审测试和循环检测后，再与单 Agent baseline 比较收益。",
            "projects/09-multi-agent-dev-team/README.md",
            "project09-multi-agent-dev-infographic-base.png",
            (
                "需求 · Task Contract · Acceptance",
                "Product · Planner · Coder · Reviewer · Tester",
                "Typed State · Artifact · Evidence · Disposable Git",
                "Independent Review · Test · Loop / Budget / No-progress",
                "Single-Agent Baseline · Quality Gain · Cost Decision",
            ),
        ),
    )
    return {spec.semantic_id: spec for spec in specs}


def build_five_stage_infographic(semantic_id: str) -> InfographicRecord:
    spec = _five_stage_specs()[semantic_id]
    stage_y = (180, 500, 810, 1110, 1400)
    labels = [Label(512, 26, spec.title, 27, "bold", "#24476B", 3)]
    labels.extend(
        Label(512, y, stage, 18 if len(stage) > 42 else 20, "bold", "#24476B", 4)
        for stage, y in zip(spec.stages, stage_y, strict=True)
    )
    return _build_portrait_infographic(
        semantic_id=spec.semantic_id,
        title=spec.title,
        description=spec.description,
        source_path=spec.source_path,
        source_name=spec.source_name,
        labels=labels,
        arrows=[list(points) for points in _B_FLOW_ARROWS],
        generated_at="2026-08-12",
    )


def write_manifest(records: list[InfographicRecord]) -> Path:
    output = ASSET_ROOT / "manifest.json"
    existing: dict[str, dict[str, object]] = {}
    if output.is_file():
        existing = {
            str(item["semantic_id"]): item
            for item in json.loads(output.read_text(encoding="utf-8"))
        }
    for record in records:
        existing[record.semantic_id] = asdict(record)
    output.write_text(
        json.dumps(
            [existing[key] for key in sorted(existing)],
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pilot",
        choices=(
            "p01",
            "p02",
            "p03",
            "transformer",
            "runtime",
            "mcp",
            "memory",
            "langgraph",
            "observability",
            "security",
            "multi-agent",
            "project10",
            "b-all",
            "coverage-all",
            "all",
        ),
        default="all",
    )
    args = parser.parse_args()
    records: list[InfographicRecord] = []
    if args.pilot in {"p01", "all"}:
        records.append(build_pilot_one())
    if args.pilot in {"p02", "all"}:
        records.append(build_pilot_two())
    if args.pilot in {"p03", "all"}:
        records.append(build_pilot_three())
    if args.pilot in {"transformer", "all"}:
        records.append(build_transformer_infographic())
    if args.pilot in {"runtime", "all"}:
        records.append(build_agent_runtime_infographic())
    if args.pilot in {"mcp", "all"}:
        records.append(build_mcp_infographic())
    if args.pilot in {"memory", "all"}:
        records.append(build_memory_infographic())
    if args.pilot in {"langgraph", "all"}:
        records.append(build_langgraph_infographic())
    if args.pilot in {"observability", "all"}:
        records.append(build_observability_infographic())
    if args.pilot in {"security", "all"}:
        records.append(build_security_infographic())
    if args.pilot in {"multi-agent", "all"}:
        records.append(build_multi_agent_infographic())
    if args.pilot in {"project10", "all"}:
        records.append(build_project10_infographic())
    if args.pilot in {"b-all", "all"}:
        records.extend(build_b_infographic(semantic_id) for semantic_id in _b_specs())
    if args.pilot in {"coverage-all", "all"}:
        records.extend(
            build_five_stage_infographic(semantic_id) for semantic_id in _five_stage_specs()
        )
    manifest = write_manifest(records)
    print(f"Built {len(records)} infographic(s); manifest: {manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
