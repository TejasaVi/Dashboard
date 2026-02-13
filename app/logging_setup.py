import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

import requests
from flask import Flask, g, request


_LOGGER_NAME = "dashboard"
_REQUESTS_PATCHED = False


def _safe_repr(value: Any, *, max_len: int = 2000) -> str:
    try:
        text = json.dumps(value, default=str)
    except Exception:
        text = repr(value)
    if len(text) > max_len:
        return f"{text[:max_len]}...<truncated>"
    return text


def _get_logger() -> logging.Logger:
    return logging.getLogger(_LOGGER_NAME)


def configure_file_logging(app: Flask) -> None:
    log_dir = Path(app.root_path).parent / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "app_debug.log"

    logger = _get_logger()
    logger.setLevel(logging.DEBUG)

    if not logger.handlers:
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        logger.addHandler(file_handler)

    logger.propagate = False

    app.config["DEBUG_LOG_FILE"] = str(log_file)

    @app.before_request
    def _log_incoming_request() -> None:
        if not request.path.startswith("/api"):
            return
        g._log_api_request = True
        payload = request.get_json(silent=True)
        logger.debug(
            "INCOMING API | method=%s path=%s args=%s json=%s form=%s",
            request.method,
            request.path,
            _safe_repr(request.args.to_dict(flat=False)),
            _safe_repr(payload),
            _safe_repr(request.form.to_dict(flat=False)),
        )

    @app.after_request
    def _log_api_response(response):
        if getattr(g, "_log_api_request", False):
            body = response.get_data(as_text=True)
            logger.debug(
                "OUTGOING API RESPONSE | method=%s path=%s status=%s body=%s",
                request.method,
                request.path,
                response.status,
                _safe_repr(body),
            )
        return response


def patch_requests_logging() -> None:
    global _REQUESTS_PATCHED
    if _REQUESTS_PATCHED:
        return

    logger = _get_logger()
    original_request = requests.sessions.Session.request

    def _logged_request(self, method, url, *args, **kwargs):
        logger.debug(
            "EXTERNAL API CALL | method=%s url=%s params=%s data=%s json=%s headers=%s",
            method,
            url,
            _safe_repr(kwargs.get("params")),
            _safe_repr(kwargs.get("data")),
            _safe_repr(kwargs.get("json")),
            _safe_repr(kwargs.get("headers")),
        )
        try:
            response = original_request(self, method, url, *args, **kwargs)
        except Exception as exc:
            logger.exception("EXTERNAL API ERROR | method=%s url=%s error=%s", method, url, exc)
            raise

        logger.debug(
            "EXTERNAL API RESPONSE | method=%s url=%s status=%s body=%s",
            method,
            url,
            response.status_code,
            _safe_repr(response.text),
        )
        return response

    requests.sessions.Session.request = _logged_request
    _REQUESTS_PATCHED = True
