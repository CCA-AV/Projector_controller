import json
import importlib
import pkgutil
from typing import Dict, List, Optional, Tuple

import requests


PROJECTORS_PACKAGE = "projectors"

# Network range taken from the existing discover() function in projector.py
DEFAULT_BASE_NETWORK = "192.168.0"

# HTTP timeouts (seconds)
PING_TIMEOUT = 0.3
PROBE_TIMEOUT = 0.5


def _iter_projector_types() -> List[str]:
    """
    Automatically discover all projector type modules in the `projectors` package.
    """
    package = importlib.import_module(PROJECTORS_PACKAGE)
    types: List[str] = []
    types.extend(
        module_name
        for _, module_name, is_pkg in pkgutil.iter_modules(package.__path__)
        if not is_pkg
    )
    return types


def _load_projector_module(projector_type: str):
    """
    Import a specific projector module, e.g. projectors.christie.
    """
    return importlib.import_module(f"{PROJECTORS_PACKAGE}.{projector_type}")


def _ip_responds(ip: str) -> bool:
    """
    Basic liveness check for an IP address.
    We just try an HTTP GET to the root and see if it connects.
    """
    try:
        resp = requests.get(f"http://{ip}", timeout=PING_TIMEOUT)
        # Any HTTP status means the host is up enough to talk HTTP
        return True
    except requests.RequestException:
        return False


def _format_headers(headers: Dict[str, str], ip: str) -> Dict[str, str]:
    """
    Some projector modules define headers that include '{ip}'.
    Format those placeholders if present.
    """
    out: Dict[str, str] = {
        k: v.format(ip=ip) if isinstance(v, str) else v for k, v in headers.items()
    }
    return out


def _probe_projector_type(
    ip: str, projector_type: str
) -> Optional[Tuple[str, Dict[str, str]]]:
    """
    Check whether a given IP looks like it hosts a specific projector type.

    Returns:
        ("high", payload) on high-confidence match (200 with working login)
        ("low", payload) on low-confidence match (401 even with default login)
        None if this type does not appear to match this IP.
    """
    module = _load_projector_module(projector_type)

    control_page = getattr(module, "control_page", None)
    default_login = getattr(module, "default_login", None)
    req_headers = getattr(module, "req_headers", {})

    if control_page is None or default_login is None:
        return None

    username = default_login.get("username", "")
    password = default_login.get("password", "")

    headers = _format_headers(req_headers, ip)

    control_url = f"http://{ip}{control_page}"

    # First, hit the control page without credentials.
    try:
        r = requests.get(control_url, timeout=PROBE_TIMEOUT, headers=headers)
    except requests.RequestException:
        return None

    # If the control page is open and returns 200, treat it as success using
    # the module's known default credentials.
    if r.status_code == 200:
        payload = {
            "ip": ip,
            "projector_type": projector_type,
            "username": username,
            "password": password,
        }
        return "high", payload

    # If we get a 401, try again using the module's default credentials.
    if r.status_code == 401:
        auth_url = f"http://{username}:{password}@{ip}{control_page}"
        try:
            r_auth = requests.get(auth_url, timeout=PROBE_TIMEOUT, headers=headers)
        except requests.RequestException:
            # We know the control page exists, but cannot confirm login
            payload = {
                "ip": ip,
                "projector_type": projector_type,
            }
            return "low", payload

        if r_auth.status_code == 200:
            # Assume any 200 response from a control page with a login counts as successful.
            payload = {
                "ip": ip,
                "projector_type": projector_type,
                "username": username,
                "password": password,
            }
            return "high", payload

        if r_auth.status_code == 401:
            # Control page exists but the default credentials don't work.
            payload = {
                "ip": ip,
                "projector_type": projector_type,
            }
            return "low", payload

    # Any other status codes are treated as non-matches
    return None


def auto_discover(
    base_network: str = DEFAULT_BASE_NETWORK,
    start_host: int = 0,
    end_host: int = 254,
) -> Dict[str, List[Dict[str, str]]]:
    """
    Discover projectors on the given network and categorize them.

    Returns a dict with two arrays:
        {
          "resolved": [  # high-confidence matches (known working credentials)
            {
              "ip": "...",
              "projector_type": "...",
              "username": "...",
              "password": "..."
            },
            ...
          ],
          "unauthorized": [  # low-confidence matches (control page found but login failed)
            {
              "ip": "...",
              "projector_type": "..."
            },
            ...
          ]
        }
    """
    projector_types = _iter_projector_types()

    resolved: List[Dict[str, str]] = []
    unauthorized: List[Dict[str, str]] = []

    for i in range(start_host, end_host + 1):
        ip = f"{base_network}.{i}"

        if not _ip_responds(ip):
            continue

        best_match_kind: Optional[str] = None
        best_payload: Optional[Dict[str, str]] = None

        for projector_type in projector_types:
            result = _probe_projector_type(ip, projector_type)
            if result is None:
                continue

            kind, payload = result

            # Prefer high-confidence over low-confidence matches.
            if kind == "high":
                best_match_kind = kind
                best_payload = payload
                # Once we have a high-confidence match, we stop checking other types.
                break

            if best_match_kind is None:
                best_match_kind = kind
                best_payload = payload

        if best_match_kind and best_payload:
            if best_match_kind == "high":
                resolved.append(best_payload)
            else:
                unauthorized.append(best_payload)

    return {"resolved": resolved, "unauthorized": unauthorized}


def save_discovery_results(
    results: Dict[str, List[Dict[str, str]]], path: str = "data.json"
) -> None:
    """
    Save discovery results to a JSON file.
    """
    with open(path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)


if __name__ == "__main__":
    data = auto_discover()
    save_discovery_results(data, "data.json")
