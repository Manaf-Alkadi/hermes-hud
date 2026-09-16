"""i18n 回归测试：locale 归一化、四语文案、缓存按语言隔离、事故 canonical 语义。

对应 PR 评审提出的 4 个 blocker：
  1. 事故 title/detail 必须恒为 zh（落盘 / state_changes / hud_alert 的依据），
     按语言渲染的文案只走 display_title/display_detail
  2. /health 内存缓存按 locale 分桶
  3. /snapshot 缓存按 locale 分桶
  4. resolve_locale 归一化 region/script 子标签（zh-CN / zh-Hant / fr-FR ...）

全部用纯 pytest 跑（不依赖 macOS / Chrome / hermes CLI），CI 里真实执行。
"""

from __future__ import annotations

import asyncio
import os
import sys
import tempfile
import types
from pathlib import Path

import pytest

# plugin_api 在 import 期就会建 store（$HERMES_HOME/hud/telemetry.db）并读取
# collectors.HERMES_HOME —— 先把 HERMES_HOME 指到临时目录，别碰真实家目录。
_TMP_HOME = tempfile.mkdtemp(prefix="hud-i18n-test-")
os.environ["HERMES_HOME"] = _TMP_HOME

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "dashboard"))


def _ensure_fastapi_stub() -> None:
    """CI 只装 pytest；补上 plugin_api import 需要的最小 fastapi 表面。"""
    try:
        import fastapi  # noqa: F401
        return
    except ImportError:
        pass

    mod = types.ModuleType("fastapi")

    class APIRouter:
        def get(self, *a, **k):
            return lambda fn: fn

        def websocket(self, *a, **k):
            return lambda fn: fn

    class HTTPException(Exception):
        def __init__(self, status_code: int = 500, detail: str = "") -> None:
            super().__init__(detail)
            self.status_code, self.detail = status_code, detail

    class WebSocket:  # pragma: no cover - 仅用于满足 import
        pass

    class WebSocketDisconnect(Exception):
        pass

    mod.APIRouter = APIRouter
    mod.HTTPException = HTTPException
    mod.Query = lambda default=None, **k: default
    mod.WebSocket = WebSocket
    mod.WebSocketDisconnect = WebSocketDisconnect
    mod.status = types.SimpleNamespace(WS_1008_POLICY_VIOLATION=1008)
    sys.modules["fastapi"] = mod


_ensure_fastapi_stub()

from hud import rules, storage  # noqa: E402
from hud.i18n import resolve_locale, t  # noqa: E402

import plugin_api  # noqa: E402

LOCALES = ("zh", "en", "fr", "ar")

# gateway 不存活 —— 最稳定的一条事故（四语模板齐全，无平台依赖）。
_FAKE_SNAP = {
    "gateway": {"alive": False, "state": "stopped", "pid": 4242, "platforms": {}},
    "db": {"error": None, "today_sessions": {}},
    "system": {"disk_free_percent": 80.0, "memory": {"percent": 40.0}},
    "errors": {"count_30m": 0},
    "launchd": {"status": "not_applicable"},
    "dashboard": {"procs": [{"pid": 1}]},
    "cron": {"jobs": []},
    "active_sessions": [],
}


def _snapshot_for(locale: str) -> dict:
    return dict(_FAKE_SNAP)


@pytest.fixture()
def api(tmp_path, monkeypatch):
    """干净的 plugin_api：临时 DB + 清空的按语言缓存 + 假 collector。"""
    monkeypatch.setattr(plugin_api, "store", storage.TelemetryStore(db_path=tmp_path / "telemetry.db"))
    monkeypatch.setattr(plugin_api.collectors, "build_snapshot", _snapshot_for)
    monkeypatch.setattr(plugin_api, "_snapshot_cache", {})
    monkeypatch.setattr(plugin_api, "_last_health", {})
    monkeypatch.setattr(plugin_api, "_last_snapshot", None)
    monkeypatch.setattr(plugin_api, "_last_overall", None)
    # 落盘限频默认 60s，测试里要每次都真的写
    monkeypatch.setattr(plugin_api, "_last_telemetry_ts", 0.0)
    monkeypatch.setattr(plugin_api, "_TELEMETRY_INTERVAL", 0.0)
    return plugin_api


# --------------------------------------------------------------------------
# 1 / 6 / 7 —— resolve_locale
# --------------------------------------------------------------------------

def test_resolve_locale_matrix() -> None:
    for loc in LOCALES:
        assert resolve_locale(loc) == loc


def test_resolve_locale_unknown_falls_back_to_en() -> None:
    for raw in ("de", "ja", "xx-YY", "klingon", "  ", "123"):
        assert resolve_locale(raw) == "en"


def test_resolve_locale_missing_keeps_zh_default() -> None:
    """未带 locale 的老客户端保持历史行为（中文）。"""
    assert resolve_locale(None) == "zh"
    assert resolve_locale("") == "zh"


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("zh-CN", "zh"), ("zh-Hant", "zh"), ("zh-Hans", "zh"), ("zh-hant", "zh"),
        ("ZH-HANT", "zh"), ("zh_TW", "zh"),
        ("en-US", "en"), ("EN", "en"), ("en_GB", "en"),
        ("fr-FR", "fr"), ("fr-CA", "fr"), ("FR", "fr"),
        ("ar-SA", "ar"), ("ar-MA", "ar"), ("  ar-EG  ", "ar"),
    ],
)
def test_resolve_locale_normalizes_subtags(raw: str, expected: str) -> None:
    """region/script 子标签归一到主语言，不再整体掉回英文。"""
    assert resolve_locale(raw) == expected


# --------------------------------------------------------------------------
# 2 / 3 / 4 / 5 —— 四语文案
# --------------------------------------------------------------------------

def _first_incident(locale: str) -> dict:
    health = rules.evaluate_snapshot(dict(_FAKE_SNAP), locale)
    incidents = [i for i in health["incidents"] if i["fingerprint"] == "gateway:not-alive"]
    assert incidents, "fake snapshot 应触发 gateway:not-alive"
    return incidents[0]


def test_zh_baseline_unchanged() -> None:
    """中文是原文，逐字节不变。"""
    inc = _first_incident("zh")
    assert inc["title"] == "Gateway 不存活"
    assert inc["display_title"] == "Gateway 不存活"


@pytest.mark.parametrize("locale,expected", [
    ("en", "Gateway is down"),
    ("fr", "Gateway est arrêtée"),
    ("ar", "Gateway متوقفة"),
])
def test_incident_display_title_translated(locale: str, expected: str) -> None:
    assert _first_incident(locale)["display_title"] == expected


def test_all_locales_have_distinct_display_text() -> None:
    titles = {loc: _first_incident(loc)["display_title"] for loc in LOCALES}
    assert len(set(titles.values())) == len(LOCALES), titles


def test_templates_cover_all_locales_with_same_placeholders() -> None:
    """66 条模板 × 4 语言，无缺键、占位符一致。"""
    import re

    from hud import i18n
    for key, bundle in i18n.TEMPLATES.items():
        missing = [loc for loc in LOCALES if not bundle.get(loc)]
        assert not missing, f"{key} 缺少 {missing}"
        placeholders = {loc: set(re.findall(r"\{(\w+)\}", bundle[loc])) for loc in LOCALES}
        assert len(set(map(frozenset, placeholders.values()))) == 1, f"{key} 占位符不一致: {placeholders}"


# --------------------------------------------------------------------------
# 11 —— 事故 canonical 语义
# --------------------------------------------------------------------------

def test_canonical_title_is_zh_in_every_locale() -> None:
    """title/detail 是落盘依据，任何请求语言下都必须是中文原文。"""
    for loc in LOCALES:
        inc = _first_incident(loc)
        assert inc["title"] == t("gateway_not_alive_title", "zh")
        assert inc["detail"] == t("gateway_not_alive_detail", "zh", pid=4242, state="stopped")


def test_display_fields_present_for_every_incident() -> None:
    """前端回退链要成立：每条事故都带 display_*。"""
    for loc in LOCALES:
        for inc in rules.evaluate_snapshot(dict(_FAKE_SNAP), loc)["incidents"]:
            assert inc.get("display_title"), inc["fingerprint"]
            assert "display_detail" in inc, inc["fingerprint"]


# --------------------------------------------------------------------------
# 10 —— 切换语言不得制造假的状态变化（hud_alert 重复推送的根因）
# --------------------------------------------------------------------------

def test_state_changes_stable_across_locales(api) -> None:
    for loc in LOCALES:
        health = rules.evaluate_snapshot(dict(_FAKE_SNAP), loc)
        api._update_telemetry(dict(_FAKE_SNAP), health)

    rows = [i for i in api.store.list_incidents() if i["fingerprint"] == "gateway:not-alive"]
    assert len(rows) == 1
    inc = rows[0]
    assert inc["observations"] == len(LOCALES)   # 每次观测都记
    assert inc["state_changes"] == 1             # 但语言切换不是状态变化
    assert inc["title"] == t("gateway_not_alive_title", "zh")   # 落盘恒中文
    assert inc["detail"] == t("gateway_not_alive_detail", "zh", pid=4242, state="stopped")


# --------------------------------------------------------------------------
# 8 / 9 —— 缓存按语言隔离
# --------------------------------------------------------------------------

def test_snapshot_cache_isolated_per_locale(api) -> None:
    """zh 之后立刻请求 en（TTL 窗口内）必须拿到英文，不是上一个标签页的中文。"""
    async def scenario() -> tuple[dict, dict]:
        zh = await api._get_snapshot("zh")
        en = await api._get_snapshot("en")
        return zh, en

    zh, en = asyncio.run(scenario())
    zh_inc = zh["_health"]["incidents"][0]
    en_inc = en["_health"]["incidents"][0]
    assert zh_inc["display_title"] == "Gateway 不存活"
    assert en_inc["display_title"] == "Gateway is down"


def test_snapshot_cache_serves_all_four_locales(api) -> None:
    async def scenario() -> dict:
        return {loc: (await api._get_snapshot(loc))["_health"]["incidents"][0]["display_title"]
                for loc in LOCALES}

    titles = asyncio.run(scenario())
    assert len(set(titles.values())) == len(LOCALES), titles


def test_health_cache_isolated_per_locale(api) -> None:
    """/health 命中内存缓存时也必须按语言分桶。"""
    async def scenario() -> tuple[dict, dict, dict]:
        first_zh = await api.get_health(locale="zh")
        en = await api.get_health(locale="en")
        again_zh = await api.get_health(locale="zh")   # 这次走缓存
        return first_zh, en, again_zh

    zh, en, zh_cached = asyncio.run(scenario())
    assert zh["incidents"][0]["display_title"] == "Gateway 不存活"
    assert en["incidents"][0]["display_title"] == "Gateway is down"
    assert zh_cached["incidents"][0]["display_title"] == "Gateway 不存活"


def test_health_normalizes_locale_before_caching(api) -> None:
    """zh-CN 与 zh 共用同一个桶，不会各算一份、也不会掉回英文。"""
    async def scenario() -> tuple[dict, dict]:
        return await api.get_health(locale="zh-CN"), await api.get_health(locale="zh-Hant")

    cn, hant = asyncio.run(scenario())
    assert cn["incidents"][0]["display_title"] == "Gateway 不存活"
    assert hant["incidents"][0]["display_title"] == "Gateway 不存活"
    assert set(api._last_health) == {"zh"}


# --------------------------------------------------------------------------
# 12 —— Desktop /health 契约保持不变
# --------------------------------------------------------------------------

def test_health_api_contract_preserved(api) -> None:
    """i18n 不改动 Desktop 协商契约，且不带 locale 的老客户端仍是中文。"""
    payload = asyncio.run(api.get_health())
    assert payload["api_schema_version"] == 1
    assert payload["plugin_version"]
    for key in ("overall", "counts", "checks", "incidents", "evaluated_at"):
        assert key in payload
    inc = payload["incidents"][0]
    assert inc["display_title"] == "Gateway 不存活"
    assert inc["title"] == t("gateway_not_alive_title", "zh")


def test_health_contract_identical_across_locales(api) -> None:
    """语言只改文案，不改结构 / 等级 / 计数。"""
    async def scenario() -> list[dict]:
        return [await api.get_health(locale=loc) for loc in LOCALES]

    payloads = asyncio.run(scenario())
    assert len({p["overall"] for p in payloads}) == 1
    assert len({tuple(sorted(p["counts"].items())) for p in payloads}) == 1
    assert len({tuple(sorted(i["fingerprint"] for i in p["incidents"])) for p in payloads}) == 1
