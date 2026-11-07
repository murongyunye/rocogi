from __future__ import annotations

import json
import urllib.error
import urllib.request

from ..contracts import FieldDef, NodeContract, NodeResult, PortDef, register

INPUT = [PortDef("in", "输入")]
OUT = [PortDef("out", "输出")]


@register(
    NodeContract(
        type="http.request",
        title="HTTP 请求",
        category="net",
        description="调用本地或远程 HTTP 服务，把响应写入运行变量。",
        effectful=True,
        inputs=INPUT,
        outputs=OUT,
        fields=[
            FieldDef("method", "方法", "select", "GET", options=[
                {"value": "GET", "label": "GET"},
                {"value": "POST", "label": "POST"},
            ]),
            FieldDef("url", "地址", "text", "http://127.0.0.1:8787/api/health", required=True),
            FieldDef("body", "请求体", "textarea", "{}", rows=3),
            FieldDef("timeout", "超时秒", "number", 8, minimum=1, maximum=60, step=1),
        ],
        tags=["集成", "API"],
    )
)
def http_request(ctx, node):
    url = ctx.text(node.config.get("url", ""))
    method = node.config.get("method", "GET")
    timeout = float(ctx.eval(node.config.get("timeout"), 8) or 8)
    body = ctx.text(node.config.get("body", "")).encode("utf-8") if method == "POST" else None
    request = urllib.request.Request(url, data=body, method=method)
    if body is not None:
        request.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status = int(response.status)
            text = response.read(200000).decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        status = int(exc.code)
        text = exc.read(200000).decode("utf-8", errors="replace")
    except Exception as exc:  # noqa: BLE001
        return NodeResult(outputs={"ok": False, "error": str(exc)}, message=f"请求失败: {exc}")
    preview = text[:400]
    ctx.vars["http_status"] = status
    ctx.vars["http_body"] = text
    return NodeResult(
        outputs={"ok": 200 <= status < 400, "status": status, "body": preview},
        message=f"HTTP {status}",
    )
