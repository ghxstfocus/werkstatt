"""OP-382: Server-Start laedt .env + Default-Port 8001."""
import ast
from pathlib import Path


def _main_pfad() -> Path:
    return Path(__file__).parent.parent / "werkstatt" / "web" / "__main__.py"


def test_main_importiert_load_env():
    """load_env muss importiert werden."""
    tree = ast.parse(_main_pfad().read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "werkstatt.env_loader":
            for name in node.names:
                if name.name == "load_env":
                    return
    raise AssertionError("load_env muss in __main__.py importiert werden")


def test_main_ruft_load_env_auf_modulebene():
    """load_env() muss auf Modulebene laufen (Side-Effect beim Import)."""
    tree = ast.parse(_main_pfad().read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            call = node.value
            if isinstance(call.func, ast.Name) and call.func.id == "load_env":
                return
    raise AssertionError("load_env() muss im Modul-Body stehen, nicht in main()")


def test_default_port_ist_8001():
    """Werkstatt-Konvention: 8001, nicht 8000."""
    quelle = _main_pfad().read_text(encoding="utf-8")
    assert "default=8001" in quelle, "default=8001 fuer --port fehlt"
    assert "default=8000" not in quelle, "default=8000 (alte Konvention) noch drin"
