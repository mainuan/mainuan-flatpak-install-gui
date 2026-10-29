"""Leitura local de referências, sem executar comandos ou acessar a rede."""
import configparser
from pathlib import Path
from urllib.parse import urlsplit

def read_reference(path):
    path = Path(path)
    if path.suffix.lower() != ".flatpakref":
        raise ValueError("Selecione um arquivo .flatpakref.")
    with path.open("rb") as stream:
        raw = stream.read(65537)
    if len(raw) > 65536:
        raise ValueError("Arquivo de referência muito grande.")
    parser = configparser.ConfigParser(interpolation=None)
    try:
        parser.read_string(raw.decode("utf-8-sig"))
        section = parser["Flatpak Ref"]
        app_id = section["Name"].strip()
        url = section["Url"].strip()
    except (UnicodeError, configparser.Error, KeyError) as exc:
        raise ValueError("Referência Flatpak inválida.") from exc
    import re
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_-]*(?:\.[A-Za-z_][A-Za-z0-9_-]*){2,}", app_id):
        raise ValueError("Identificador do aplicativo inválido.")
    parsed = urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("A origem precisa usar HTTPS sem credenciais na URL.")
    if section.get("IsRuntime", "false").lower() != "false":
        raise ValueError("Esta interface é destinada a aplicativos.")
    return {"name": section.get("Title", app_id).strip() or app_id,
            "id": app_id, "source": url}
