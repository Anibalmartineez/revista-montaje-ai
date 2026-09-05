from __future__ import annotations

import argparse
import socket
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Sequence


ROOT_URL = "http://127.0.0.1:5000/"
EDITOR_V1_URL = "http://127.0.0.1:5000/editor_offset_visual"
EDITOR_V2_URL = "http://127.0.0.1:5000/editor_offset_visual_v2"
URLS_BY_TARGET: dict[str, tuple[str, ...]] = {
    "root": (ROOT_URL,),
    "v1": (ROOT_URL, EDITOR_V1_URL),
    "v2": (ROOT_URL, EDITOR_V2_URL),
    "both": (ROOT_URL, EDITOR_V1_URL, EDITOR_V2_URL),
}
SUCCESS_STATUS_MIN = 200
SUCCESS_STATUS_MAX = 399


@dataclass(frozen=True)
class CheckResult:
    url: str
    status: int | None
    ok: bool
    detail: str


class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(
        self,
        req: urllib.request.Request,
        fp: object,
        code: int,
        msg: str,
        headers: object,
        newurl: str,
    ) -> None:
        return None


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("debe ser un entero mayor o igual que 1")
    return parsed


def non_negative_float(value: str) -> float:
    parsed = float(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("debe ser un número mayor o igual que 0")
    return parsed


def positive_float(value: str) -> float:
    parsed = float(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("debe ser un número mayor que 0")
    return parsed


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Comprueba las rutas HTTP obligatorias de Flask local."
    )
    parser.add_argument(
        "--target",
        choices=tuple(URLS_BY_TARGET),
        default="v1",
        help="superficie que debe responder: v1, v2, both o root (uso interno)",
    )
    parser.add_argument("--attempts", type=positive_int, default=5)
    parser.add_argument("--interval", type=non_negative_float, default=1.0)
    parser.add_argument("--timeout", type=positive_float, default=2.0)
    return parser.parse_args(argv)


def is_success_status(status: int) -> bool:
    return SUCCESS_STATUS_MIN <= status <= SUCCESS_STATUS_MAX


def check_url(url: str, timeout: float) -> CheckResult:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "editor-offset-local-qa/1.0"},
        method="GET",
    )
    opener = urllib.request.build_opener(NoRedirectHandler())
    try:
        with opener.open(request, timeout=timeout) as response:
            status = response.getcode()
            if not isinstance(status, int):
                return CheckResult(url, None, False, "respuesta sin estado HTTP válido")
            return CheckResult(
                url,
                status,
                is_success_status(status),
                "estado aceptado" if is_success_status(status) else "estado fuera del rango aceptado",
            )
    except urllib.error.HTTPError as exc:
        status = exc.code
        return CheckResult(
            url,
            status,
            is_success_status(status),
            f"respuesta HTTP: {exc.reason}",
        )
    except urllib.error.URLError as exc:
        reason = exc.reason
        if isinstance(reason, socket.timeout):
            detail = "timeout de conexión"
        elif isinstance(reason, ConnectionRefusedError):
            detail = "conexión rechazada"
        elif isinstance(reason, socket.gaierror):
            detail = f"error DNS: {reason}"
        else:
            detail = f"error de conexión: {reason}"
        return CheckResult(url, None, False, detail)
    except (socket.timeout, TimeoutError) as exc:
        return CheckResult(url, None, False, f"timeout: {exc}")
    except OSError as exc:
        return CheckResult(url, None, False, f"error del sistema: {exc}")
    except Exception as exc:
        return CheckResult(
            url,
            None,
            False,
            f"respuesta inesperada ({type(exc).__name__}): {exc}",
        )


def print_result(result: CheckResult) -> None:
    status_text = str(result.status) if result.status is not None else "sin estado"
    verdict = "OK" if result.ok else "FALLO"
    print(f"  [{verdict}] {result.url} -> HTTP {status_text}; {result.detail}")


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    required_urls = URLS_BY_TARGET[args.target]
    print(
        f"Criterio de éxito: todas las rutas deben devolver HTTP "
        f"{SUCCESS_STATUS_MIN}-{SUCCESS_STATUS_MAX}."
    )
    print(
        f"Configuración: target={args.target}, intentos={args.attempts}, "
        f"intervalo={args.interval}s, timeout={args.timeout}s."
    )

    final_results: list[CheckResult] = []
    for attempt in range(1, args.attempts + 1):
        print(f"Intento {attempt}/{args.attempts}:")
        final_results = [check_url(url, args.timeout) for url in required_urls]
        for result in final_results:
            print_result(result)
        if all(result.ok for result in final_results):
            print("Resumen final: todas las comprobaciones obligatorias fueron satisfactorias.")
            return 0
        if attempt < args.attempts:
            time.sleep(args.interval)

    failed_urls = [result.url for result in final_results if not result.ok]
    print(
        "Resumen final: fallaron comprobaciones obligatorias: "
        + ", ".join(failed_urls)
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

