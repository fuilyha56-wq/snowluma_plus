"""中文配置必须进入当前WebUI实际使用的Schema。"""

from __future__ import annotations

import re
import sys
import types
import zipfile
from pathlib import Path

import pytest

from ..config import SnowLumaConfig


def test_all_webui_sections_and_fields_have_chinese_labels(monkeypatch):
    """读取已安装WebUI的纯Schema解析器，不启动其服务或修改其文件。"""
    workspace = Path(__file__).resolve().parents[3]
    packages = list((workspace / "plugins").glob("neo-mofox-webui*.mfp"))
    if not packages:
        pytest.skip("未安装WebUI，字段模型元数据可由配置类独立检查")
    package_name = "snowluma_plus_test_webui_schema"
    package = types.ModuleType(package_name)
    package.__path__ = []
    monkeypatch.setitem(sys.modules, package_name, package)
    with zipfile.ZipFile(packages[0]) as archive:
        for suffix in ("config_types", "config_parser"):
            name = package_name + "." + suffix
            module = types.ModuleType(name)
            module.__package__ = package_name
            monkeypatch.setitem(sys.modules, name, module)
            source = archive.read("utils/" + suffix + ".py").decode("utf-8-sig")
            exec(
                compile(source, str(packages[0]) + "!/utils/" + suffix + ".py", "exec"),
                module.__dict__,
            )
    sections = module.ConfigParser.extract_schema(SnowLumaConfig)
    assert len(sections) == 7
    assert sum(len(section.fields) for section in sections) == 53
    for section in sections:
        assert re.search(r"[\u4e00-\u9fff]", section.title), section.name
        for field in section.fields:
            assert re.search(r"[\u4e00-\u9fff]", field.label), (section.name, field.key)
            assert field.description
    assert sections[0].title == "插件设置"
    assert sections[0].fields[0].label == "启用插件"
