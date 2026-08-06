"""Immutable prompt specification and safe renderer."""

import hashlib
import html
import json
import string
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class PromptSpec:
    name: str
    version: str
    template: str
    variables: tuple[str, ...]
    content_hash: str

    @classmethod
    def create(
        cls, name: str, version: str, template: str, variables: tuple[str, ...]
    ) -> "PromptSpec":
        fields = []
        for _, field, _, _ in string.Formatter().parse(template):
            if field is None:
                continue
            if not field.isidentifier():
                raise ValueError("模板包含不安全的属性或索引访问")
            fields.append(field)
        if set(fields) != set(variables) or len(set(variables)) != len(variables):
            raise ValueError("声明变量必须与模板字段完全一致")
        payload = {
            "name": name,
            "version": version,
            "template": template,
            "variables": list(variables),
        }
        digest = hashlib.sha256(
            json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest()
        return cls(name, version, template, variables, digest)

    def render(self, values: dict[str, str]) -> str:
        if set(values) != set(self.variables):
            raise ValueError("渲染变量必须与 Prompt 契约完全一致")
        wrapped = {
            key: f'<input name="{key}">{html.escape(value)}</input>'
            for key, value in values.items()
        }
        return self.template.format_map(wrapped)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, object]) -> "PromptSpec":
        raw_variables = value["variables"]
        if not isinstance(raw_variables, list):
            raise ValueError("Prompt variables 必须是列表")
        spec = cls.create(
            str(value["name"]),
            str(value["version"]),
            str(value["template"]),
            tuple(str(item) for item in raw_variables),
        )
        if spec.content_hash != value["content_hash"]:
            raise ValueError("Prompt 内容哈希校验失败")
        return spec
