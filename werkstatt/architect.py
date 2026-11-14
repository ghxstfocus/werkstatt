"""Architect-Agent (Fix AZ Stufe 10, 2026-10-31).

Extrahiert aus planner.py. Baut den Architect-Prompt und ruft den
LLM-Call. Re-Export in planner.py erhaelt API-Kompatibilitaet
(Tests patchen werkstatt.planner._architect_system_with_builder).

Late-Binding-Proxies fuer _with_spinner, ask_llm, audit,
_strip_xml_tags, _get_architect_model -- alle werden in
werkstatt.planner aufgeloest, damit Test-Patches wirken.
"""
from __future__ import annotations


def _extrahiere_op_felder(aufgabe: str, docs_status: str) -> dict:
    """M-Welle-I (2026-11-02): maschinenlesbare OP-Felder aus STATUS.md.

    Der Architect braucht die strukturierten Felder (Existiert bereits,
    Nicht-Ziele, Betroffene Dateien) direkt im Prompt. Ohne sie fuellt
    er Luecken mit Kreativitaet -> Over-Engineering.

    Extrahiert den OP-Block, der zum `aufgabe`-Text passt (OP-NNN-Match),
    parst die strukturierten Felder und gibt sie als dict zurueck.
    """
    import re as _re_op
    if not aufgabe or not docs_status:
        return {}
    # OP-NNN aus aufgabe ziehen
    m = _re_op.search(r"OP-\d{3}", aufgabe)
    if not m:
        return {}
    op_id = m.group(0)
    # Block aus STATUS.md schneiden (### OP-NNN bis naechste ### / ##)
    pat = _re_op.compile(
        rf"(### {_re_op.escape(op_id)}:[^\n]*\n.*?)(?=\n### OP-|\n## |\Z)",
        _re_op.DOTALL,
    )
    block = pat.search(docs_status)
    if not block:
        return {}
    text = block.group(1)

    # Felder extrahieren (mehrzeilig bis naechstes "- **" oder Ende)
    def _feld(name: str) -> str:
        pat = _re_op.compile(
            rf"- \*\*{_re_op.escape(name)}:\*\*\s*\n?(.*?)(?=\n- \*\*|\Z)",
            _re_op.DOTALL,
        )
        fm = pat.search(text)
        return fm.group(1).strip() if fm else ""

    return {
        "id": op_id,
        "betroffene_dateien": _feld("Betroffene Dateien"),
        "nicht_ziele": _feld("Nicht-Ziele"),
        "existiert_bereits": _feld("Existiert bereits"),
        "fehlt_noch": _feld("Fehlt noch"),
        "akzeptanz": _feld("Akzeptanzkriterien"),
        "tests": _feld("Tests"),
    }


def _format_op_felder_for_prompt(felder: dict) -> str:
    """M-Welle-I: OP-Felder als markierter Prompt-Block."""
    if not felder:
        return ""
    parts = [f"## OP-SPEZIFIKATION ({felder.get('id', '?')}, maschinenlesbar aus STATUS.md)"]
    for key, label in [
        ("betroffene_dateien", "Betroffene Dateien (PFLICHT — nur diese)"),
        ("nicht_ziele", "NICHT-ZIELE (verboten)"),
        ("existiert_bereits", "EXISTIERT BEREITS (nicht neu bauen)"),
        ("fehlt_noch", "FEHLT NOCH"),
        ("akzeptanz", "Akzeptanzkriterien"),
        ("tests", "Tests"),
    ]:
        val = felder.get(key, "").strip()
        if val:
            parts.append(f"### {label}\n{val}")
    if len(parts) == 1:
        return ""
    return "\n\n".join(parts) + "\n\n"


def _format_scout_apis_arch(apis: dict, max_lines: int = 20) -> str:
    """M-Welle-I: Scout-API-Auszug als Prompt-Block (Architect)."""
    if not isinstance(apis, dict) or not apis:
        return ""
    lines = []
    for datei, symbole in list(apis.items())[:10]:
        if not isinstance(symbole, list):
            continue
        for sym in symbole[:5]:
            if isinstance(sym, str):
                lines.append(f"  {datei}: {sym}")
                if len(lines) >= max_lines:
                    break
        if len(lines) >= max_lines:
            break
    return chr(10).join(lines)


def _format_scout_auftrag(auftrag: dict, max_prosa: int = 3000) -> str:
    """OP-385: Scout-Report als einzigen Architect-Prompt-Block rendern.

    Enthaelt alles, was der Architect braucht: Auftrag-Prosa,
    API-Auszug, Risiken. Keine Explorer-Rohdaten — die sind
    absichtlich nicht drin (Kontext-Verengung durch Scout).
    """
    if not isinstance(auftrag, dict) or not auftrag:
        return ""
    teile = ["<scout_auftrag>", "## Auftrag (vom Scout)"]
    prosa = str(auftrag.get("auftrag_prosa") or "").strip()
    teile.append(prosa[:max_prosa] if prosa else "(kein Prosa-Auftrag vom Scout)")
    apis = auftrag.get("api_auszug") or {}
    if isinstance(apis, dict) and apis:
        apis_str = _format_scout_apis_arch(apis)
        if apis_str:
            teile.append("")
            teile.append("## API-Auszug (relevante Symbole)")
            teile.append(apis_str)
    risiken = auftrag.get("risiken") or []
    if isinstance(risiken, list) and risiken:
        teile.append("")
        teile.append("## Risiken (vom Scout)")
        for r in risiken[:10]:
            teile.append(f"- {str(r)[:200]}")
    api_widersprueche = auftrag.get("api_widersprueche") or []
    if isinstance(api_widersprueche, list) and api_widersprueche:
        import json

        teile.extend([
            "",
            "## Deterministischer API-Abgleich (Code-Index ist massgeblich)",
            (
                "Scout-API-Aussagen mit einem belegten Widerspruch; "
                "nicht als bestehende Schnittstelle planen:"
            ),
            json.dumps(api_widersprueche[:10], ensure_ascii=False),
        ])
    bereits = auftrag.get("bereits_erfuellt")
    if bereits:
        teile.append("")
        teile.append("## Hinweis")
        teile.append("Scout meldet: Auftrag moeglicherweise bereits erfuellt.")
    teile.append("</scout_auftrag>")
    return "\n".join(teile)


def _format_target_api_evidence(state, explorer_ctx: dict | None) -> str:
    """Render current AST signatures for files named by this work item.

    The Scout excerpt is intentionally compact and can omit a relevant API.
    This deterministic block lets the Architect distinguish existing
    interfaces from methods it is proposing to add.
    """
    import re

    api_index = getattr(state, "api_index_cache", None) or {}
    if not isinstance(api_index, dict) or not api_index:
        return ""

    candidates: list[str] = []

    def add_path(value: object) -> None:
        if not isinstance(value, str):
            return
        normalized = value.strip().replace("\\", "/")
        if (
            normalized.startswith("/")
            or ".." in normalized.split("/")
            or not re.fullmatch(r"[A-Za-z0-9_./-]+", normalized)
        ):
            return
        if normalized.endswith(".py") and normalized not in candidates:
            candidates.append(normalized)

    fields = _extrahiere_op_felder(
        getattr(state, "aufgabe", ""),
        (getattr(state, "docs", None) or {}).get("status", ""),
    )
    for field_name in ("betroffene_dateien", "tests"):
        field_text = str(fields.get(field_name) or "")
        for match in re.findall(r"[A-Za-z0-9_./\\-]+\.py", field_text):
            add_path(match)

    scout_report = getattr(state, "scout_auftrag", None) or {}
    for item in scout_report.get("relevante_dateien", []):
        if isinstance(item, dict):
            add_path(item.get("pfad"))
    for path in (scout_report.get("api_auszug") or {}):
        add_path(path)
    scout_apis = scout_report.get("api_auszug") or {}
    if not isinstance(scout_apis, dict):
        scout_apis = {}

    if isinstance(explorer_ctx, dict):
        for item in explorer_ctx.get("key_files") or []:
            if isinstance(item, dict):
                add_path(item.get("file"))

    # Include direct in-repository imports of the task targets. This exposes
    # the interface and side-effect class of dependencies such as EventStore,
    # which Explorer may not list as a primary file.
    dependency_symbols: dict[str, set[str]] = {}
    for source_path in tuple(candidates):
        source_entry = api_index.get(source_path) or api_index.get(
            source_path.replace("/", "\\")
        )
        if not isinstance(source_entry, dict):
            continue
        for imported in source_entry.get("imports", []):
            if not isinstance(imported, dict):
                continue
            module = imported.get("from")
            if not isinstance(module, str) or not module.startswith("werkstatt."):
                plain_module = imported.get("import")
                module = plain_module if isinstance(plain_module, str) else ""
            if not isinstance(module, str) or not module.startswith("werkstatt."):
                continue
            dependency = module.replace(".", "/") + ".py"
            if dependency not in api_index and dependency.replace("/", "\\") not in api_index:
                continue
            add_path(dependency)
            names = imported.get("names") or []
            dependency_symbols.setdefault(dependency, set()).update(
                name for name in names if isinstance(name, str)
            )

    if not candidates:
        return ""

    lines = [
        "## Verifizierte aktuelle API-Signaturen (deterministischer AST-Index)",
        "Nur diese bestehenden Signaturen sind im Quellcode belegt. Ein",
        "nicht aufgefuehrtes API darf nicht als bestehend beschrieben werden.",
        "Neue APIs duerfen vorgeschlagen werden, muessen aber als neu markiert sein.",
        "Vergleiche Scout-Symbole mit der Signatur hier; bei Abweichung gilt der AST.",
    ]
    signature_budget = 64
    for path in candidates[:8]:
        entry = api_index.get(path)
        if entry is None:
            entry = api_index.get(path.replace("/", "\\"))
        lines.append(f"### {path}")
        if not isinstance(entry, dict):
            lines.append("(im aktuellen Python-AST-Index nicht vorhanden)")
            continue
        requested: object = next(
            (
                symbols
                for scout_path, symbols in scout_apis.items()
                if (
                    isinstance(scout_path, str)
                    and scout_path.strip().replace("\\", "/") == path
                )
            ),
            [],
        )
        requested_names: set[str] = set()
        explicitly_requested_names: set[str] = set()
        if isinstance(requested, (list, tuple)):
            for symbol in requested:
                if isinstance(symbol, str):
                    display_symbol = symbol.replace("\r", " ").replace("\n", " ")[:160]
                    qualified = display_symbol.split("(", 1)[0]
                    names = {
                        part for part in qualified.split(".")
                        if part and part.isidentifier()
                    }
                    requested_names.update(names)
                    explicitly_requested_names.update(names)
                    lines.append(f"Scout nennt: {display_symbol}")
        requested_names.update(dependency_symbols.get(path, set()))
        symbols = 0
        for function in entry.get("functions", []):
            if signature_budget <= 0:
                break
            if not isinstance(function, dict):
                continue
            if requested_names and function.get("name") not in requested_names:
                continue
            args = ", ".join(function.get("args", []))
            result = f" -> {function['return']}" if function.get("return") else ""
            effect = function.get("effects")
            effect_text = f" [effect: {effect}]" if effect else ""
            lines.append(f"def {function.get('name', '?')}({args}){result}{effect_text}")
            symbols += 1
            signature_budget -= 1
        for class_info in entry.get("classes", []):
            if signature_budget <= 0:
                break
            if not isinstance(class_info, dict):
                continue
            class_name = class_info.get("name", "?")
            method_names = {
                method.get("name") for method in class_info.get("methods", [])
                if isinstance(method, dict)
            }
            if requested_names and not (
                class_name in requested_names
                or method_names.intersection(requested_names)
            ):
                continue
            lines.append(f"class {class_name}:")
            for method in class_info.get("methods", []):
                if signature_budget <= 0:
                    break
                if not isinstance(method, dict):
                    continue
                # Imported classes are expanded to their public interface;
                # private helpers are implementation details and crowd out
                # the APIs the Architect must choose between.
                if (
                    str(method.get("name", "")).startswith("_")
                    and method.get("name") not in explicitly_requested_names
                ):
                    continue
                if (
                    requested_names
                    and class_name not in requested_names
                    and method.get("name") not in requested_names
                ):
                    continue
                args = ", ".join(method.get("args", []))
                result = f" -> {method['return']}" if method.get("return") else ""
                lines.append(
                    f"  def {method.get('name', '?')}({args}){result}"
                    f" [effect: {method.get('effects', 'unknown')}]"
                )
                symbols += 1
                signature_budget -= 1
        if not symbols:
            if requested_names:
                lines.append("(keines der vom Scout genannten Symbole im AST belegt)")
            else:
                lines.append("(keine Top-Level-Funktionen oder Klassen im AST-Index)")
        if signature_budget <= 0:
            lines.append("(Signaturauszug begrenzt; weitere APIs hier nicht aufgefuehrt)")
            break
    return "<verified_target_apis>\n" + "\n".join(lines) + "\n</verified_target_apis>"


def _pruefe_architect_api_referenzen(prosa: str, api_index: dict) -> list[str]:
    """Reject unproven existing API calls before the plan reaches the Builder.

    The AST block in the prompt is helpful context, not an enforcement
    boundary. This check treats code-shaped calls as existing interfaces only
    when the current AST index contains the symbol. An absent symbol is
    accepted only when the Architect explicitly labels it as a new API nearby.
    """
    import re

    from werkstatt.scout import _finde_api

    if not isinstance(prosa, str):
        return ["Architect-Antwort ist kein Text."]

    # Backticked identifiers are the Architect's explicit code/API references.
    # Also inspect dotted calls outside code spans so formatting cannot evade
    # the check. The system prompt requires new APIs to be marked explicitly.
    code_spans = list(re.finditer(r"`([^`]+)`", prosa))
    references: list[tuple[str, int, str]] = []
    call_pattern = re.compile(
        r"(?<![\w.])([A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*)\s*\("
    )
    for span in code_spans:
        for match in call_pattern.finditer(span.group(1)):
            references.append((match.group(1), span.start(1) + match.start(), span.group(1)))
    for match in re.finditer(
        r"(?<![\w.])([A-Z][A-Za-z0-9_]*\.[A-Za-z_]\w*)\s*\(", prosa
    ):
        item = (match.group(1), match.start(), prosa[max(0, match.start()-80):match.end()+80])
        if not any(symbol == item[0] and offset == item[1] for symbol, offset, _ in references):
            references.append(item)

    if references and (not isinstance(api_index, dict) or not api_index):
        return ["Der aktuelle AST-API-Index fehlt; Architect-Plan nicht belegbar."]

    missing: list[str] = []
    seen: set[str] = set()
    new_marker = re.compile(
        r"\b(?:neu(?:e|en|er|es)?|hinzuf(?:ue|ü)gen|implementier(?:en|t|e))\b",
        re.IGNORECASE,
    )
    builtin_calls = {
        "all", "any", "bool", "dict", "enumerate", "filter", "float",
        "getattr", "hasattr", "int", "isinstance", "iter", "len", "list",
        "map", "max", "min", "next", "open", "print", "range", "repr",
        "reversed", "round", "set", "sorted", "str", "sum", "tuple", "type",
        "zip",
    }
    common_container_methods = {
        "append", "clear", "copy", "count", "extend", "get", "index",
        "insert", "items", "keys", "pop", "remove", "setdefault", "sort",
        "update", "values",
    }
    for symbol, offset, context in references:
        short_name = symbol.rsplit(".", 1)[-1]
        if short_name in builtin_calls | {"if", "for", "while", "with", "except", "assert"}:
            continue
        parts = symbol.split(".")
        qualifier = parts[-2] if len(parts) > 1 else ""
        qualified_matches = [
            *_finde_api(api_index, symbol),
            *(_finde_api(api_index, ".".join(parts[-2:])) if len(parts) > 1 else []),
        ]
        qualifier_is_project_class = bool(
            qualifier and any(
                match.get("kind") == "class"
                for match in _finde_api(api_index, qualifier)
            )
        )
        matches = qualified_matches or (
            [] if qualifier_is_project_class else _finde_api(api_index, short_name)
        )
        if matches:
            section_start = prosa.rfind("## ", 0, offset)
            next_section = prosa.find("\n## ", offset)
            if section_start >= 0:
                section_end = next_section if next_section >= 0 else len(prosa)
                section = prosa[section_start:section_end]
            else:
                section = ""
            is_read_aggregate = bool(re.search(
                r"\baggregate_[a-z0-9_]+\b|\b(?:read.only|read-only|"
                r"read aggregator|leseaggregator|GET-handler)\b",
                section,
                re.IGNORECASE,
            ))
            unsafe_read_effects = sorted({
                str(match.get("effects", "unknown"))
                for match in matches
                if match.get("effects", "unknown") != "read"
            })
            if is_read_aggregate and unsafe_read_effects:
                missing.append(
                    f"{symbol} (Effekt {', '.join(unsafe_read_effects)} "
                    "in Read-Aggregator nicht als read belegt)"
                )
            continue
        if qualifier and short_name in common_container_methods:
            continue
        neighborhood = prosa[max(0, offset - 100):offset + len(context) + 100]
        if new_marker.search(neighborhood):
            continue
        if symbol not in seen:
            missing.append(symbol)
            seen.add(symbol)
    return missing


def _format_explorer_findings(f: dict) -> str:
    """M-WelleE: Explorer-Findings als Prompt-Block."""
    if not isinstance(f, dict) or not f:
        return "(keine)"
    lines = []
    for k, v in list(f.items())[:10]:
        if isinstance(v, list):
            v_str = ", ".join(str(x) for x in v[:5])
        elif isinstance(v, dict):
            v_str = str(v)[:100]
        else:
            v_str = str(v)
        lines.append(f"- {k}: {v_str}")
    return "\n".join(lines)


def audit(*args, **kwargs):
    """Late-Binding-Proxy fuer werkstatt.planner.audit."""
    from werkstatt.planner import audit as _orig
    return _orig(*args, **kwargs)


def _with_spinner(*args, **kwargs):
    """Late-Binding-Proxy fuer werkstatt.planner._with_spinner."""
    from werkstatt.planner import _with_spinner as _orig
    return _orig(*args, **kwargs)


def ask_llm(*args, **kwargs):
    """Late-Binding-Proxy fuer werkstatt.planner.ask_llm."""
    from werkstatt.planner import ask_llm as _orig
    return _orig(*args, **kwargs)


def _strip_xml_tags(*args, **kwargs):
    """Late-Binding-Proxy fuer werkstatt.planner._strip_xml_tags."""
    from werkstatt.planner import _strip_xml_tags as _orig
    return _orig(*args, **kwargs)


def _get_architect_model() -> str:
    """Late-Binding-Getter fuer werkstatt.planner._ARCHITECT_MODEL."""
    from werkstatt.planner import _ARCHITECT_MODEL
    return _ARCHITECT_MODEL


# OP-172 (2026-11-05): Architect ist ein Reasoning-Modell
# (deepseek-reasoner). Reasoning + Content teilen sich das
# max_tokens-Budget. Loop-Test-6 hat gezeigt: 55706 Zeichen
# Reasoning (~14000 Tokens) bei 16000 max_tokens -> Content
# bleibt leer, Architect failt mit leerem content.
# 32000 = Default fuer deepseek-reasoner. Reicht fuer 14K
# Reasoning + 18K Content.
ARCHITECT_MAX_TOKENS = 32000

ARCHITECT_SYSTEM = """Du bist ein elite Software-Architekt.
Beschreibe die Loesung in Prosa. KEIN JSON, KEIN Patch-Format.

Format (STRIKT einhalten):
  1. Was ist das Problem?
  2. Welche Datei(en) muessen geaendert werden?
  3. Wie sieht die Loesung aus?
     PRO DATEI EIN BLOCK. Innerhalb eines Blocks: EINE
     Funktion/Methode komplett (Signatur, Logik, Fehler,
     Rueckgabe) als zusammenhaengender Absatz. NICHT als
     nummerierte Schritte.
     Der Planner-Split schneidet die Prosa an Datei- und
     Funktionsgrenzen. Eine Task = ein reviewbares Interface.
     Beispiel GUT:
       "In app/foo.py: neue Funktion bar(x, y). Validiert
        x > 0, ruft helper(y), gibt Result zurueck. Bei
        Fehler: BarError."
     Beispiel SCHLECHT:
       "1. In bar(): validiere x. 2. In bar(): rufe
        helper(y). 3. In bar(): gib Result zurueck."
     Jede Funktion/Klasse ist EIN Block. Wenn eine Datei
     mehrere Funktionen hat: EIN Block pro Funktion.
  4. Welche Tests brauchen wir?

  5. Welche Dateien haengen voneinander ab? (PFLICHT)

     Pro Datei eine Zeile. Format EXAKT:
       - <pfad>: <dep-pfad>, <dep-pfad>
       - <pfad>: (keine)

     Beispiel:
       - werkstatt/state.py: (keine)
       - werkstatt/gates.py: (keine)
       - tests/test_gates.py: werkstatt/state.py, werkstatt/gates.py
       - docs/STATE-INVENTUR.md: werkstatt/state.py, tests/test_gates.py

     REGELN:
       - Jede Datei, die in Abschnitt 3 als '## <pfad>'-Block
         vorkommt, MUSS hier eine Zeile haben.
       - Unabhaengige Datei: explizit '(keine)' schreiben.
       - KEINE Wildcards, KEINE Prosa. Nur konkrete Pfade.
       - Wenn KEINE Datei von einer anderen abhaengt:
         eine einzelne Zeile '- (keine)'.

DEINE ROLLE IM LOOP (WICHTIG):
  - Explorer hat bereits geliefert: WO (Dateien, Zeilennummern,
    Ist-Zustand — siehe die Explorer-Bloecke im Kontext).
  - Scout hat bereits geliefert: WAS (Auftrag, API-Widersprueche
    — siehe den Scout-Block im Kontext).
  - Deine Aufgabe ist NUR: WIE. Welche Signatur, welche Logik,
    welche Integration.
  - Du hast keine Tools. Du misst NICHT. Du beschreibst.
  - Wenn Explorer+Scout leer sind, ist das ein Pipeline-Fehler
    (Contract-Violation), KEIN Auftrag zum Selbermessen.

REGELN:
  - Du lieferst Prosa. Du rufst keine Tools. Du baust nichts.
  - Code muss ruff-konform sein (E, F, I, SIM, RUF, BLE).
  - __all__ sortiert.
  - Kein `except Exception` ohne `# noqa: BLE001`.
  - Max line-length 100.
  - Keine unbenutzten Variablen (F841).

API-STABILITAET (WICHTIG):
  - Bestehende API NIE umbenennen (z.B. ApplierError bleibt ApplierError).
  - Bestehende Signaturen NIE aendern ohne Not.
  - Bestehende Rueckgabetypen NIE aendern.
  - Neue Features: ADDITIV (neue Methoden, neue Klassen), nicht ersetzend.

FROZEN DATACLASSES:
  - Wenn ein Parameter `frozen=True` ist: NICHT setattr() aufrufen.
  - Nutze dict/separate Struktur fuer Zusatz-Daten.

DATEI-UEBERSCHRIFTEN (PFLICHT fuer jede Datei):

Fuer JEDE Datei, die du aenderst, schreibe eine eigene
Ueberschrift im Format "## <voller-pfad>". Diese Ueberschrift
wird vom Builder genutzt, um den richtigen Abschnitt zu finden.

Beispiel:
  ## 3. Wie sieht die Loesung aus?

  ## apps/dashboard/routes_state.py
  Neue Funktion _section_timeline()...

  ## apps/dashboard/static/js/dashboard.js
  Neue Funktion renderTimeline()...

Regeln:
  - Ueberschrift EXAKT der Dateipfad, KEIN Backtick, KEIN "Datei:".
  - Format: "## <pfad>" (zwei Rauten, dann Pfad).
  - Fuer jede Datei ein eigener Block.
  - Der Builder sucht "## <pfad>", um den Abschnitt zu finden.
  - Wenn du eine Datei ohne "## <pfad>"-Ueberschrift beschreibst,
    findet der Builder sie NICHT.

WENN NUR EINE DATEI BETROFFEN IST:
  Beschreibe sie direkt, mit "## <pfad>"-Ueberschrift.

GROESSEN-ZIEL:
  Eine Funktion/Methode = 50-150 Zeilen Code. Zu klein
  (< 30 Zeilen) -> kein reviewbares Interface. Zu gross
  (> 200 Zeilen) -> Semantik-Verlust im Builder.

TESTS — BEDINGT IM SCOPE:
  DEFAULT: Tests sind OUT-OF-SCOPE. Beschreibe KEINE Test-Dateien,
  KEINE Aenderungen an Test-Dateien. Wenn deine Loesung Tests
  braucht: beschreibe nur, welche Faelle getestet werden sollten.

  AUSNAHME: Wenn der Auftrag oder der referenzierte OP explizit
  einen Test-Namen nennt (Pattern test_*, z.B. "test_insert_..."):
  DANN ist die Test-Datei IM SCOPE. Fuege einen eigenen Block
  "## tests/<pfad>" hinzu mit:
    - Test-Funktionsnamen (exakt wie im OP genannt)
    - Arrange/Act/Assert in Prosa
    - Welche DB-Zeilen/State nach dem Aufruf erwartet werden
  Der Builder braucht diesen Block, sonst kann er den Test nicht
  bauen. Beispiel: OP fordert "Neuer Test test_foo_bar" ->
  "## tests/unit/test_modul.py" mit test_foo_bar beschreiben.

MIGRATIONS-NUMMERN:
  - Wenn eine Migration noetig ist: pruefe data/migrations/.
  - Nimm die hoechste vorhandene Nummer +1.
  - Nummern-Kollision ist ein Review-Fail.
  - Nutze NIEMALS eine Nummer, die bereits als Datei existiert.

Antworte NUR mit diesem Prosa-Text. Kein Code, nur Beschreibung.

## KONSISTENZ BEI MULTI-TASK-PLAENEN (verbindlich)

Wenn ein Plan Code-Tasks (z.B. t1: `werkstatt/web/chat.py`) und Test-Tasks
(z.B. t4: `tests/test_chat_windows.py`) enthaelt, gelten:

1. API-Signaturen MUESSEN zwischen Code und Test identisch sein.
   Beispiel: Test ruft `wende_aktion_an(zustand, aktion)` -> Code baut
   GENAU 2 Parameter, nicht 3.

2. Dict-Keys MUESSEN zwischen Code und Test identisch sein.
   Beispiel: Test prueft `ergebnis["ziel"]` -> Code gibt Key "ziel"
   zurueck, NICHT "target" oder "raw".

3. Bei jeder Funktion, die ein Test prueft, MUSS der Code-Task die
   gleiche Signatur zeigen. Wenn unsicher: Signatur WOERTLICH in beiden
   Tasks nennen (`wende_aktion_an(zustand: dict, aktion: str)`).

4. Bei Test-Tasks: KEINE selbstwiderspruechlichen Assertions.
   Falsch: `assert set(x.keys()) == {a, b}` UND `assert x["c"] == ...`
   (impliziert c ist im dict, widerspricht a,b).
   Richtig: optionale Keys explizit ausnehmen:
   `assert set(x.keys()) - {c} == {a, b}`.

5. Wenn Code-Task und Test-Task in derselben Phase laufen, haengen
   sie zusammen: der Reviewer muss BEIDE genehmigen oder KEINEN.

## AUFRUFER-PFLICHT (verbindlich, ab 2026-11-07)

Wenn dein Plan eine NEUE Datei (Modul, Helper, Tool) erstellt,
MUSST du im Plan explizit eine der beiden Angaben machen:

(a) **Aufrufer:** "<bestehendes Modul>" ruft "<neue Datei>.<funktion>"
    ODER <neue Datei> wird in <bestehendes Modul> importiert.
(b) **Standalone:** "<neue Datei> ist ein eigenstaendiges
    User-Tool und wird NICHT von anderen Modulen importiert."

Ohne (a) oder (b) ist der Plan UNVOLLSTAENDIG. Grund: Loop-Test 8
(2026-11-07) zeigte, dass ein neues Tool (tools/contract_check.py)
gebaut wurde, aber niemand es rief — die Pruefung lief nie.
Live-Beleg: 64 Zeilen toter Code, nur von Tests importiert.

**Konkret im Plan:**
- Bei "neue Datei X.py anlegen" immer dazuschreiben, WER X.py ruft.
- Bei "neuer Helper in bestehender Datei" immer dazuschreiben, WER
  den Helper aufruft (nicht nur "wird von Test Y getestet").
- Wenn nur Tests rufen: das ist Dead-Code im Produktivpfad.

## DETERMINISTISCHER API-VERTRAG (PFLICHT)

- Verwende bestehende Projekt-APIs nur, wenn sie im aktuellen AST-Auszug
  belegt sind. Schreibe jeden API-Aufruf in Backticks, zum Beispiel
  `EventStore.append(...)`.
- Jede nicht vorhandene Funktion/Methode/Klasse muss im selben Abschnitt
  ausdruecklich als NEU markiert sein (z.B. "neue Methode
  `Projector.backfill(...)`"). Der Builder darf neue APIs nur bauen, wenn
  sie im Architect-Plan als neu markiert und einem betroffenen Datei-Block
  zugeordnet sind.
- Der Loop prueft codeartige Aufrufe nach deiner Antwort gegen den aktuellen
  AST-Index einschliesslich belegbarer Lese-/Schreibwirkung. Ein nicht
  belegter Aufruf ohne NEU-Markierung oder ein Schreib-API in einem
  Read-Aggregator verwirft den Plan vor Planner-Split, Plan-Gate und Builder.
  Der Architect erhaelt den Befund fuer eine gezielte Korrektur.
- Behaupte niemals, ein im AST fehlendes API sei vorhanden. Wenn der AST-Auszug
  fehlt oder eine Signatur nicht sicher zugeordnet werden kann, markiere die
  Schnittstelle als offen und plane zuerst den tatsaechlichen Vertrag.

## GOLD: SCOUT-KONTEXT
Du bekommst im User-Content:
- "SCOUT-AUFTRAG" (vorformuliert).
- "VERFUEGBARE APIS (aus Code-Index)".

Nutze die APIs aus "VERFUEGBARE APIS" -- NICHT die aus der Aufgabe.
Wenn die Aufgabe eine API nennt, die nicht im API-Auszug steht:
  Nenne sie NICHT. Nutze die aehnlichste echte API.
Beispiel: Aufgabe sagt "read_events". API-Auszug hat
"list_recent_assessments". Nutze list_recent_assessments.
"""


_BUILDER_SCHNITTSTELLE = """## DER BUILDER (Schnittstelle)
- Modell: deepseek-flash.
- Input: eine Zieldatei + dein Abschnitt fuer diese Datei.
- Output: JSON-Patch mit old_string (aus Datei) + new_string (deine Beschreibung).
- Grenzen: keine Tools, keine API-Raterei, keine Imports ohne explizite Nennung.
- Du musst liefern: "## <pfad>", Interface (Signatur), Logik, Integration, Imports.
"""

_ARCHITECT_SCHNITTSTELLE = """## DER ARCHITECT (Schnittstelle)
- Liefert: Prosa mit "## <pfad>", Interface, Logik, Integration.
- Plant modular: welche Datei, welche Klasse, welcher Datenfluss.
- Modell: deepseek-v4-pro (Thinking, hoher Effort).
"""

_REVIEWER_SCHNITTSTELLE = """## DER REVIEWER (Schnittstelle)
- Prueft: bricht der Code? Task erfuellt? Bestehende Aufrufe erhalten?
- HIGH-Bug wenn: bestehender Aufruf entfernt, Funktion ueberschrieben, API erfunden.
"""


def _architect_system_with_builder() -> str:
    """GOLD: ARCHITECT_SYSTEM + _BUILDER_SCHNITTSTELLE."""
    return ARCHITECT_SYSTEM + "\n\n" + _BUILDER_SCHNITTSTELLE


def _planner_system(aufgabe: str, explorer_ctx: dict | None = None, state=None) -> str:
    """M-376: Explorer-Dateien ZUERST (Lost-in-the-Middle).

    Goldstandard: Relevante Information an den Anfang des
    Kontexts. Die gemessenen Dateien sind die wichtigste
    Information — sie stehen VOR PLANNER_SYSTEM.
    """
    parts: list[str] = []

    # OP-385: Wenn scout_auftrag gesetzt ist, ist das die EINZIGE
    # Quelle fuer den Architect. Explorer-Rohdaten (AST-Block,
    # explorer_findings, scout_api_auszug, measured_files) kommen
    # dann NICHT mehr rein. Grund: Live 2026-11-09, 100.000 user_len
    # truncation durch 4 parallele Quellen (OP-385).
    _hat_scout_auftrag = bool(
        state is not None
        and getattr(state, "scout_auftrag", None)
    )

    # AST-Info (verkabelt 2026-11-03): Struktur der key_files aus
    # state.api_index_cache. Wird von run_architect befuellt.
    if (not _hat_scout_auftrag) and state is not None and explorer_ctx is not None:
        _api_idx = state.api_index_cache or {}
        _kf = explorer_ctx.get("key_files") or []
        # OP-137: key_files haben "file", nicht "pfad"/"path".
        # Sortiere nach confidence (high -> medium -> low -> default).
        # Sonst sieht der Architect bei >10 Dateien zufaellig 10
        # medium und verpasst eine high-confidence-Datei.
        _CONF_RANK = {"high": 0, "medium": 1, "low": 2}

        def _conf_key(_kf_entry):
            _c = ((_kf_entry.get("confidence") or "medium").lower()
                  if isinstance(_kf_entry, dict) else "medium")
            return _CONF_RANK.get(_c, 3)

        _kf_sorted = sorted(_kf, key=_conf_key)
        _kf_paths: list[str] = []
        for _f in _kf_sorted:
            if isinstance(_f, dict):
                _p = (_f.get("file")
                      or _f.get("pfad")
                      or _f.get("path") or "")
            else:
                _p = str(_f)
            if _p:
                _kf_paths.append(_p)
        if _api_idx and _kf_paths:
            _ast_lines = ["## DATEI-STRUKTUR (AST)"]
            for _p in _kf_paths[:10]:
                _info = _api_idx.get(_p)
                if not _info:
                    continue
                _ast_lines.append(f"### {_p}")
                _alls = _info.get("all") or []
                if _alls:
                    _ast_lines.append(f"__all__: {', '.join(_alls)}")
                for _fn in _info.get("functions", [])[:20]:
                    _args = ", ".join(_fn.get("args", []))
                    _ret = _fn.get("return") or ""
                    _ast_lines.append(f"  def {_fn.get('name','?')}({_args}){(' -> ' + _ret) if _ret else ''}")
                for _cls in _info.get("classes", [])[:10]:
                    _ast_lines.append(f"  class {_cls.get('name','?')}")
                    for _m in _cls.get("methods", [])[:10]:
                        _margs = ", ".join(_m.get("args", []))
                        _ast_lines.append(f"    def {_m.get('name','?')}({_margs})")
            if len(_ast_lines) > 1:
                parts.append("\n".join(_ast_lines))

    # === M-Welle-I: OP-SPEZIFIKATION ZUERST (maschinenlesbar) ===
    # Live-Beleg 2026-11-02: Architect plante 5 Dateien statt 2, weil
    # er die 'Nicht-Ziele' aus STATUS.md nie gesehen hat. Der Block
    # verhindert Lueckenfuellen mit Kreativitaet.
    _op_felder = {}
    if state is not None:
        try:
            _op_felder = _extrahiere_op_felder(
                aufgabe, (state.docs or {}).get("status", "")
            )
        except Exception:
            _op_felder = {}
    _op_block = _format_op_felder_for_prompt(_op_felder)
    if _op_block:
        parts.append(_op_block.rstrip())

# M-446 (2026-11-05): kein Skills-Metadata im Architect-Prompt.

    # OP-385: Scout-Auftrag als einzige Kontext-Quelle (wenn gesetzt).
    if _hat_scout_auftrag:
        _sa_str = _format_scout_auftrag(state.scout_auftrag)
        if _sa_str:
            parts.append(_sa_str)

    # Keep the compact Scout summary, but independently expose exact AST
    # signatures for the files this OP and the Scout actually named.
    _target_apis = (
        _format_target_api_evidence(state, explorer_ctx)
        if _hat_scout_auftrag else ""
    )
    if _target_apis:
        parts.append(_target_apis)

    # === M-Welle-I: EXPLORER-FINDINGS + SCOUT-API (Welle E + D3 komplett) ===
    # OP-385: Fallback-Pfad — nur wenn scout_auftrag leer/nicht gesetzt.
    if (not _hat_scout_auftrag) and state is not None:
        _exf = state.explorer_findings or {}
        if _exf:
            try:
                _exf_str = _format_explorer_findings(_exf)
                if _exf_str and _exf_str != "(keine)":
                    parts.append(
                        f"<explorer_findings>\n{_exf_str}\n</explorer_findings>"
                    )
            except Exception:
                pass
        _scout_apis = state.scout_api_auszug or {}
        if _scout_apis:
            try:
                _sa_str = _format_scout_apis_arch(_scout_apis)
                if _sa_str:
                    parts.append(
                        f"<scout_api_auszug>\n{_sa_str}\n</scout_api_auszug>"
                    )
            except Exception:
                pass

    # === K32: MIGRATIONSSTAND ZUERST (hoechste Prioritaet) ===
    # Der Architect darf Migrationsnummern NICHT raten.
    _mig_ctx = None
    if isinstance(explorer_ctx, dict):
        _mig_ctx = explorer_ctx.get("migrations")
    if isinstance(_mig_ctx, dict) and _mig_ctx.get("hoechste"):
        parts.append(
            "<migrationsstand pflicht=\"true\">\n"
            f"Hoechste belegte Migrationsnummer: {_mig_ctx['hoechste']}\n"
            f"Naechste freie Nummer: {_mig_ctx['naechste']}\n"
            f"VERBOTEN (belegt): {', '.join(n + '_*' for n in _mig_ctx.get('alle', [])[-5:])}\n"
            "Verwende fuer neue Migrationen NUR die naechste freie Nummer.\n"
            "Kollisionen fuehren zu Review-Fail und Loop-Abbruch.\n"
            "</migrationsstand>"
        )

    # === M-376: GEMESSENE DATEIEN ZUERST (hoechste Prioritaet) ===
    # OP-385: Fallback-Pfad — nur wenn scout_auftrag leer.
    if (not _hat_scout_auftrag) and isinstance(explorer_ctx, dict):
        _key = explorer_ctx.get("key_files") or []
        _files = [
            k.get("file") for k in _key
            if isinstance(k, dict) and k.get("file")
        ]
        if _files:
            _files_str = "\n".join(f"  - {f}" for f in _files)
            parts.append(
                "<measured_files>\n"
                f"Der Explorer hat {len(_files)} Datei(en) mit Fehlern "
                f"gemessen (deterministisch, nicht geraten):\n"
                f"{_files_str}\n"
                "</measured_files>"
            )
            parts.append(
                "<measured_files_hinweis>\n"
                f"Der Explorer hat {len(_files)} Datei(en) gemessen. "
                "Diese sind KONTEXT, keine Aufgabenliste.\n"
                "Wenn die Aufgabe explizit Funktionen oder Dateien nennt: "
                "halte dich an die Aufgabe.\n"
                "Nur wenn die Aufgabe keine Dateien nennt: waehle aus "
                "diesen Dateien.\n"
                "</measured_files_hinweis>"
            )
            # GOLD 2026-10-30: Datei-Inhalte der gemessenen Dateien.
            # Der Architect muss den Ist-Zustand kennen, sonst plant
            # er Aenderungen, die schon erledigt sind.
            _previews = []
            for _k in _key[:5]:
                if not isinstance(_k, dict):
                    continue
                _pf = _k.get("file", "")
                _pv = _k.get("preview", "")
                if _pf and _pv:
                    _previews.append(
                        f'<datei_inhalt datei="{_pf}">\n'
                        f'{_pv[:4000]}\n'
                        f'</datei_inhalt>'
                    )
            if _previews:
                parts.append(
                    "<ist_zustand>\n"
                    "Aktueller Inhalt der genannten Dateien:\n"
                    + "\n\n".join(_previews)
                    + "\n</ist_zustand>"
                )

        # M-446 (2026-11-05): Fallback-Hinweis entfernt.
        # "Nutze <tools> (grep, read_file)" war ein DSML-Trigger.
        # Wenn keine Dateien da sind, greift OP-136a (Contract-
        # Violation) bereits vor diesem Code. Architect soll NIE
        # zum Messen aufgefordert werden (Explorer liefert WO).

    # === GOLD: Architect-Modus IMMER (nicht nur bei "architect") ===
    # FIX 2026-10-30: bis hier wurde `parts` gebaut, aber am Ende
    # verworfen (Bug: alter if-True-Zweig gab nur _arch_parts zurueck).
    # Jetzt: `parts` (Migrationsstand + measured_files + pflicht/hinweis)
    # werden VOR ARCHITECT_SYSTEM gefuehrt. Sonst bleibt K32/M-376/M-405
    # toter Code.
    parts.append(ARCHITECT_SYSTEM)
    return "\n\n".join(parts)




# =====================================================================
# Prototyp v2 (2026-11-01): Strukturierter Architect-Docs-Kontext.
# Ziel: 34801-Z.-User-Prompt auf ~8000 Z. reduzieren, davon 29289 Z.
# ROADMAP. Reducer behalten die Struktur (Sektionen, Header), kuerzen
# den Inhalt. Aktiv nur bei WERKSTATT_ARCHITECT_PROMPT=v2.
# =====================================================================


def _reduce_entry(text: str, max_chars: int = 700) -> str:
    """AGENTS.md: nur '## Zweck' + '## Struktur' behalten."""
    if not text:
        return ""
    parts = []
    for section in ("Zweck", "Struktur"):
        marker = f"## {section}"
        start = text.find(marker)
        if start < 0:
            continue
        rest = text[start + len(marker):]
        nxt = rest.find("\n## ")
        body = rest if nxt < 0 else rest[:nxt]
        parts.append(f"## {section}{body}".rstrip())
    result = "\n\n".join(parts) if parts else text[:max_chars]
    return result[:max_chars]


def _reduce_status(text: str) -> str:
    """STATUS.md: nur '## Offene Punkte' + Inhalt, unveraendert."""
    if not text:
        return ""
    marker = "## Offene Punkte"
    start = text.find(marker)
    if start < 0:
        return text
    rest = text[start:]
    nxt = rest[len(marker):].find("\n## ")
    return rest if nxt < 0 else rest[:len(marker) + nxt]


def _reduce_roadmap(text: str, max_chars: int = 800) -> str:
    """ROADMAP.md: nur Zeilen mit '## Phase' + Status-Icons behalten."""
    if not text:
        return ""
    lines = []
    for ln in text.splitlines():
        stripped = ln.strip()
        if stripped.startswith(("## Phase", "### Phase")):
            lines.append(stripped)
    result = "\n".join(lines)
    return result[:max_chars]


def _build_selbst_check_block() -> str:
    """Strukturierter Selbst-Check vor dem Senden (Prototyp v2)."""
    return (
        "## SELBST-CHECK (vor dem Senden)\n"
        "- Jede genannte API steht in VERFUEGBARE APIS.\n"
        "- Jede genannte Migrationsnummer ist die naechste freie.\n"
        "- Ausgabe-Format eingehalten: '## <pfad>'-Ueberschriften, "
        "Interface / Logik / Integration / Imports.\n"
        "- Keine Datei genannt, die nicht im Kontext steht.\n"
        "- Keine Zahl geschaetzt, nur aus MESSWERTE oder 'nicht gemessen'.\n"
    )


def _reduce_architecture(text: str, max_chars: int = 3400) -> str:
    """ARCHITECTURE.md: kompakte Ist-Architektur fuer den Architect."""
    if not text or max_chars <= 0:
        return ""

    wanted = {
        "1. Produktarchitektur": 1000,
        "1.5 Ausfuehrung": 1000,
        "4. Verifikation": 600,
        "6. Doku-Vertrag": 500,
    }
    sections: dict[str, list[str]] = {}
    title: str | None = None
    current: list[str] = []
    for line in text.splitlines():
        if line.startswith("## "):
            if title in wanted:
                sections[title] = current
            title = line[3:].strip()
            current = [line]
        elif title in wanted:
            current.append(line)
    if title in wanted:
        sections[title] = current

    parts: list[str] = []
    for section_title, limit in wanted.items():
        lines = sections.get(section_title)
        if not lines:
            continue
        block = "\n".join(lines).strip()
        if len(block) > limit:
            marker = "\n[Architekturauszug gekuerzt]"
            block = block[: max(0, limit - len(marker))].rstrip() + marker
        parts.append(block)
    return "\n\n".join(parts)[:max_chars]


def build_architect_docs_section_v2(docs: dict) -> str:
    """Strukturierter Docs-Kontext fuer den Architect (Prototyp v2).

    Ersetzt den alten '--- entry ---'-Stil durch einen begrenzten Kontext aus
    Entry, offenen OPs, Roadmap und implementierter Architektur. Die aktuelle
    Progress-Historie wird separat und ebenfalls begrenzt uebergeben.
    """
    if not docs:
        return ""
    parts: list[str] = []

    entry = _reduce_entry(docs.get("entry", ""), max_chars=700)
    if entry:
        parts.append("### PROJEKT-ENTRY (Zweck + Struktur)\n" + entry)

    status = _reduce_status(docs.get("status", ""))
    if status:
        parts.append("### PROJEKT-STATUS (offene Punkte)\n" + status)

    roadmap = _reduce_roadmap(docs.get("roadmap", ""), max_chars=800)
    if roadmap:
        parts.append("### PROJEKT-ROADMAP (nur Phasen-Header)\n" + roadmap)

    architecture = _reduce_architecture(docs.get("architecture", ""))
    if architecture:
        parts.append(
            "### PROJEKT-ARCHITEKTUR (implementierter Ist-Zustand)\n"
            + architecture
        )

    return "\n\n".join(parts)


def run_architect(
    state, aufgabe: str, user_content: str, api_key: str,
    explorer_ctx: dict | None,
) -> bool:
    """Ruft den Architect-LLM-Call (Fix AZ Stufe 10, 2026-10-31).

    Baut den Prompt aus _planner_system + _BUILDER_SCHNITTSTELLE.
    Setzt state.architect_prosa bei Erfolg. Rueckgabe: ok.
    """
    pd = state.project_dir
    pn = state.project_name

    # AST-Info: einmal berechnen, in state cachen. Wird auch vom
    # Builder gelesen. Laufzeit ~0.5-2s (210 Dateien).
    try:
        if not getattr(state, "api_index_cache", None):
            from werkstatt.scout import _baue_api_index
            state.api_index_cache = _baue_api_index(pd)
    except Exception:  # Cache ist optional
        pass

    # M-446 + Registry-Pilot (2026-11-05): Architect laedt keine Skills.
    # Single Source of Truth: werkstatt/rollen.py.
    from werkstatt.rollen import ROLLEN
    _arch_rolle = ROLLEN["architect"]
    _arch_skill_list = _arch_rolle.lade_skills([])
    if _arch_skill_list:
        raise RuntimeError(
            f"M-446-Verstoss: Architect hat {len(_arch_skill_list)} Skills, "
            f"erwartet 0. Siehe ROLLEN['architect'] in rollen.py."
        )
    state.architect_skills_block = ""

    _scout_auftrag = getattr(state, "scout_auftrag", None)
    _arch_user_content = user_content
    if _scout_auftrag:
        if (
            not isinstance(_scout_auftrag, dict)
            or not isinstance(_scout_auftrag.get("auftrag_prosa"), str)
            or not _scout_auftrag["auftrag_prosa"].strip()
        ):
            audit("planner_scout_json_fehler",
                  {"grund": "auftrag_prosa_fehlt"}, pd, pn)
            return False
        # OP-385/OP-396: Der Scout bleibt die einzige Quelle fuer
        # Code-/Explorer-Fakten. Kompakte Laufhistorie (Fortschritt,
        # Fehler und Gate-Feedback) wird getrennt uebergeben, damit der
        # Architect abgeschlossene Arbeit nicht wiederholt.
        _execution_context = getattr(
            state, "architect_execution_context", "",
        )
        _arch_user_content = (
            str(_execution_context)[:12000]
            if isinstance(_execution_context, str) else ""
        )

    _arch_sys_base = _planner_system(aufgabe, explorer_ctx, state)
    _arch_skills_block = state.architect_skills_block or ""
    _arch_sys = (
        (_arch_skills_block + "\n\n" if _arch_skills_block else "")
        + _arch_sys_base + "\n\n" + _BUILDER_SCHNITTSTELLE
    )
    _korrekturhinweis = ""
    for _versuch in range(2):
        _sys_prompt = _arch_sys + _korrekturhinweis
        _arch_reply = _with_spinner(
            "Architect",
            lambda _prompt=_sys_prompt: ask_llm(
                api_key, _prompt, _arch_user_content,
                model=_get_architect_model(),
                temperature=0.2, max_tokens=ARCHITECT_MAX_TOKENS,
                aufgabe="architect", heartbeat=False, state=state,
            ),
        )
        if not _arch_reply.ok:
            audit("planner_architect_llm_fehler",
                  {"fehler": _arch_reply.error, "versuch": _versuch + 1}, pd, pn)
            return False
        _arch_prosa = _strip_xml_tags(_arch_reply.content.strip())
        if len(_arch_prosa.strip()) < 50:
            audit("planner_architect_prosa_zu_kurz",
                  {"len": len(_arch_prosa),
                   "raw_prefix": _arch_reply.content[:200]}, pd, pn)
            return False

        _api_befunde = _pruefe_architect_api_referenzen(
            _arch_prosa, getattr(state, "api_index_cache", {}) or {},
        )
        if not _api_befunde:
            audit("planner_architect_ok",
                  {"prosa_len": len(_arch_prosa),
                   "api_preflight": "bestanden",
                   "korrekturversuche": _versuch}, pd, pn)
            state.architect_prosa = _arch_prosa
            return True

        audit("planner_plan_abgelehnt", {
            "quelle": "architect_api_preflight",
            "versuch": _versuch + 1,
            "befunde": _api_befunde[:20],
        }, pd, pn)
        if _versuch == 0:
            _korrekturhinweis = (
                "\n\n## Deterministischer API-Preflight: PLAN KORRIGIEREN\n"
                "Der vorherige Entwurf wurde vor dem Builder verworfen. "
                "Diese codeartigen API-Aufrufe sind im aktuellen AST nicht "
                "belegt:\n"
                + "\n".join(f"- {item}" for item in _api_befunde[:20])
                + "\nEntferne sie, ersetze sie durch belegte APIs oder markiere "
                "die tatsaechlich neu zu implementierende API im passenden "
                "Datei-Abschnitt ausdruecklich als NEU. Gib den vollstaendig "
                "korrigierten Plan erneut aus.\n"
            )
    return False


__all__ = [
    'ARCHITECT_SYSTEM',
    '_BUILDER_SCHNITTSTELLE',
    '_architect_system_with_builder',
    '_build_selbst_check_block',
    '_planner_system',
    '_reduce_entry',
    '_reduce_roadmap',
    '_reduce_status',
    'build_architect_docs_section_v2',
    'run_architect',
]
