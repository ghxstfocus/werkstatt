"""Doku-Aufraeumen: STATUS.md-Struktur-Regeln (OP-XXX)."""
import re
from pathlib import Path


def _s():
    return Path("docs/STATUS.md").read_text(encoding="utf-8")


def test_keine_op_header_im_auto_log():
    """Zwischen '## Erledigt (Auto-Log)' und '## Delete-Zone'
    darf kein '### OP-'-Header stehen — offene OPs gehoeren nach
    '## Offene Punkte', erledigte in die Delete-Zone."""
    s = _s()
    al = re.search(r'^## Erledigt \(Auto-Log\)$', s, re.MULTILINE)
    dz = re.search(r'^## Delete-Zone$', s, re.MULTILINE)
    assert al and dz, "Struktur-Anker fehlt"
    zwischen = s[al.end():dz.start()]
    treffer = re.findall(r'^### OP-[0-9a-z]+:', zwischen, re.MULTILINE)
    assert not treffer, (
        f"{len(treffer)} OP-Header im Auto-Log-Bereich: {treffer[:5]}"
    )


def test_auto_log_eintraege_format():
    """Auto-Log-Eintraege: '- YYYY-MM-DD | OP-NNN | status | beschreibung'."""
    s = _s()
    al = re.search(r'^## Erledigt \(Auto-Log\)$', s, re.MULTILINE)
    dz = re.search(r'^## Delete-Zone$', s, re.MULTILINE)
    assert al and dz
    zwischen = s[al.end():dz.start()]
    zeilen = [z for z in zwischen.splitlines() if z.strip().startswith("- ")]
    for z in zeilen:
        if "|" not in z:
            continue  # freie Linien ignorieren
        # Muss mit YYYY-MM-DD | OP-NNN beginnen
        assert re.match(r'- \d{4}-\d{2}-\d{2} \| OP-', z), (
            f"Auto-Log-Zeile falsches Format: {z[:100]}"
        )


def test_delete_zone_eintraege_format():
    """Delete-Zone-Eintraege: '- YYYY-MM-DD | OP-NNN | status | ...'."""
    s = _s()
    dz = re.search(r'^## Delete-Zone$', s, re.MULTILINE)
    assert dz
    danach = s[dz.end():]
    zeilen = [z for z in danach.splitlines() if z.strip().startswith("- ")]
    if not zeilen:
        return  # keine Eintraege ist OK
    for z in zeilen[:50]:  # erste 50 reichen
        if "|" not in z:
            continue
        assert re.match(r'- \d{4}-\d{2}-\d{2} \| OP-', z), (
            f"Delete-Zone-Zeile falsches Format: {z[:100]}"
        )


def test_offene_punkte_hat_nur_open_ops():
    """Alle '### OP-'-Header im Offene-Punkte-Bereich sind open/partial."""
    s = _s()
    op_header = re.search(r'^## Offene Punkte$', s, re.MULTILINE)
    sub_header = re.search(r'^## Sub-OPs', s, re.MULTILINE)
    assert op_header and sub_header
    zwischen = s[op_header.end():sub_header.start()]

    # Alle OP-Bloecke finden
    re.findall(
        r'^### (OP-[0-9a-z]+):.*?(?=\n### OP-|\Z)',
        zwischen, re.MULTILINE | re.DOTALL,
    )
    # Wir muessen den Block-Inhalt mit Status prüfen, nicht nur IDs.
    matches = list(re.finditer(
        r'^### (OP-[0-9a-z]+):.*?(?=\n### OP-|\Z)',
        zwischen, re.MULTILINE | re.DOTALL,
    ))
    for m in matches:
        oid = m.group(1)
        status_m = re.search(r'\*\*Status:\*\*\s*(\w+)', m.group(0))
        assert status_m, f"Status fehlt in {oid}"
        assert status_m.group(1) in ("open", "partial"), (
            f"{oid} hat Status '{status_m.group(1)}' — gehoert nicht nach Offene Punkte"
        )
