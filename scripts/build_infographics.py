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
        generated_at="2026-08-09",
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
    manifest = write_manifest(records)
    print(f"Built {len(records)} infographic(s); manifest: {manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
