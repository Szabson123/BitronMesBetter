import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Optional, Tuple

# Osobny plik logu (poza stdout/stderr) - leży obok projektu, niezależnie od katalogu startu serwera.
LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_FILE = LOG_DIR / "received_data.log"

received_logger = logging.getLogger("received_data")
received_logger.setLevel(logging.INFO)
received_logger.propagate = False  # nie dubluj wpisów w konsoli / basicConfig

if not received_logger.handlers:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    _handler = RotatingFileHandler(
        LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    _handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
    received_logger.addHandler(_handler)


def find_value(data: Any, key: str) -> Optional[str]:
    """Szuka klucza (bez rozróżniania wielkości liter) w dowolnie zagnieżdżonym JSON-ie.

    Zwraca pierwszą niepustą wartość skalarną (str/int/float) jako string albo None.
    """
    target = key.lower()

    if isinstance(data, dict):
        for k, v in data.items():
            if (
                isinstance(k, str)
                and k.lower() == target
                and isinstance(v, (str, int, float))
                and not isinstance(v, bool)
                and str(v).strip()
            ):
                return str(v).strip()
        for v in data.values():
            found = find_value(v, key)
            if found is not None:
                return found

    elif isinstance(data, list):
        for item in data:
            found = find_value(item, key)
            if found is not None:
                return found

    return None


def extract_parts_info(body: Any) -> Tuple[Optional[str], Optional[str]]:
    """Zwraca (idParts, msn) z dowolnego body; brakująca informacja = None."""
    return find_value(body, "idParts"), find_value(body, "msn")


def log_received_data(id_parts: str, msn: str) -> None:
    # json.dumps zabezpiecza przed wstrzyknięciem nowych linii do logu
    received_logger.info("idParts=%s msn=%s", json.dumps(id_parts), json.dumps(msn))
