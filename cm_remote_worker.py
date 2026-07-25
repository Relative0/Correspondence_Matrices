from __future__ import annotations

import argparse
import json
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from cm_ir import compile_expr, evaluate_compiled
from cmbench.output_budget import OutputBudget, OutputBudgetExceeded, OutputStatus
from cm_runpod_protocol import CMRemoteRequest, CMRemoteResponse, result_payload


def execute_cm_request(request: CMRemoteRequest) -> CMRemoteResponse:
    started = time.perf_counter()
    # Echoed back so the client can verify words provenance: a worker that
    # predates the words_eval field will not emit this key, and the client
    # refuses to record a words run against such a worker.
    diagnostics: dict[str, Any] = {"remote_words_eval": bool(request.words_eval)}
    try:
        expr = request.to_expr()
        t_compile = time.perf_counter()
        compiled = compile_expr(expr, diagnostics=diagnostics, use_persistent_cache=request.use_persistent_cache)
        compile_s = time.perf_counter() - t_compile

        t_exec = time.perf_counter()
        result = None
        output_budget = OutputBudget(
            max_output_bytes=request.max_output_bytes,
            max_temporary_bytes=request.max_temporary_bytes,
            max_output_vars=request.max_full_output_vars,
            allow_reduced_output=request.allow_reduced_output,
        )
        for _ in range(max(1, request.eval_repeat)):
            result = evaluate_compiled(
                compiled,
                mode=request.mode,
                vars_all=request.vars_all,
                diagnostics=diagnostics,
                hybrid_threshold=request.hybrid_threshold,
                words_eval=bool(request.words_eval),
                output_budget=output_budget,
                allow_reduced_output=request.allow_reduced_output,
                max_full_output_vars=request.max_full_output_vars,
            )
        exec_s = time.perf_counter() - t_exec
        repr_name, payload = result_payload(result, return_format=request.return_format)
        return CMRemoteResponse(
            request_id=request.request_id,
            ok=True,
            result_repr=repr_name,
            status=result.status.value,
            result=payload,
            diagnostics=_jsonable_dict(diagnostics),
            timing={
                "remote_total_time_s": time.perf_counter() - started,
                "remote_compile_time_s": compile_s,
                "remote_exec_time_s": exec_s,
            },
        )
    except Exception as exc:
        if isinstance(exc, OutputBudgetExceeded):
            status = OutputStatus.REFUSED.value
        elif isinstance(exc, TimeoutError):
            status = OutputStatus.TIMEOUT.value
        elif isinstance(exc, MemoryError):
            status = OutputStatus.OOM.value
        else:
            status = "error"
        return CMRemoteResponse(
            request_id=request.request_id,
            ok=False,
            result_repr="error",
            status=status,
            diagnostics=_jsonable_dict(diagnostics),
            timing={"remote_total_time_s": time.perf_counter() - started},
            error=str(exc),
        )


class CMWorkerHandler(BaseHTTPRequestHandler):
    server_version = "CMRemoteWorker/0.1"

    def do_GET(self) -> None:
        if self.path.rstrip("/") == "/health":
            self._send_json({"ok": True, "service": "cm-remote-worker"})
            return
        self.send_error(404)

    def do_POST(self) -> None:
        if self.path.rstrip("/") != "/execute":
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            data = json.loads(self.rfile.read(length).decode("utf-8"))
            response = execute_cm_request(CMRemoteRequest.from_dict(data))
            self._send_json(response.to_dict(), status=200 if response.ok else 500)
        except Exception as exc:
            self._send_json({"ok": False, "error": str(exc), "result_repr": "error"}, status=400)

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _send_json(self, payload: dict[str, Any], status: int = 200) -> None:
        raw = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


def serve(host: str = "0.0.0.0", port: int = 8080) -> None:
    server = ThreadingHTTPServer((host, port), CMWorkerHandler)
    print(f"CM remote worker listening on http://{host}:{port}")
    server.serve_forever()


def _jsonable_dict(data: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in data.items():
        if isinstance(v, (str, int, float, bool)) or v is None:
            out[str(k)] = v
        else:
            out[str(k)] = str(v)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=8080)
    args = ap.parse_args()
    serve(args.host, args.port)


if __name__ == "__main__":
    main()
