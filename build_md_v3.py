"""
Build comprehensive SPL question list in Markdown from all extracted sources.
v3 - Filters out answer keys that were being parsed as questions.
v3.1 - Deduplicates questions across sources per category.
"""
from __future__ import annotations

import json
import os
import re
import unicodedata

OUTPUT = r"c:\!Projects\Glider Exam\SPL_Otazky.md"
ANSWER_KEY_OUTPUT = r"c:\!Projects\Glider Exam\answer_keys.json"
BASE = r"c:\!Projects\Glider Exam"

# Lower number = higher priority (preferred when deduplicating)
SOURCE_PRIORITY: dict[str, int] = {"vzor": 0, "komunikace": 1, "pilotky": 2}


def _normalize_for_dedup(text: str) -> str:
    """Normalize text for duplicate comparison.

    Strips accents, collapses whitespace, lowercases.
    """
    text = re.sub(r"\s+", " ", text.strip().lower())
    text = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in text if unicodedata.category(ch) != "Mn")


def _get_source_priority(source_label: str) -> int:
    """Return numeric priority for a source label (lower = better)."""
    for prefix, priority in SOURCE_PRIORITY.items():
        if source_label.startswith(prefix):
            return priority
    return 99


def deduplicate_questions(questions: list[dict]) -> tuple[list[dict], int]:
    """Deduplicate questions by normalized text.

    For each group of duplicates, keeps the version from the
    highest-priority source (vzor > komunikace > pilotky).
    Returns (deduplicated list, number of duplicates removed).
    """
    best: dict[str, dict] = {}
    for question in questions:
        norm = _normalize_for_dedup(question["text"])
        if norm not in best:
            best[norm] = question
        elif _get_source_priority(question["source"]) < _get_source_priority(
            best[norm]["source"]
        ):
            best[norm] = question

    seen: set[str] = set()
    result: list[dict] = []
    for question in questions:
        norm = _normalize_for_dedup(question["text"])
        if norm not in seen:
            seen.add(norm)
            result.append(best[norm])

    removed = len(questions) - len(result)
    return result, removed


def is_answer_key_line(text):
    """Check if a line is just an answer key (e.g. 'b' or 'a,c' or 'a, b, c')."""
    t = text.strip()
    # Single letter
    if re.match(r'^[a-d]$', t):
        return True
    # Comma-separated letters like "a,c" or "a, b, c"
    if re.match(r'^[a-d](\s*,\s*[a-d])+$', t):
        return True
    return False


def remove_answer_blocks(text):
    """Remove blocks of consecutive answer-key lines from source text.
    An answer block is 5+ consecutive lines matching 'NUM. LETTER' pattern."""
    lines = text.split('\n')
    # First pass: mark answer-key lines
    is_answer = [False] * len(lines)
    for i, line in enumerate(lines):
        s = line.strip()
        if re.match(r'^\d+\.\s+[a-d](\s*,\s*[a-d])*\s*$', s):
            is_answer[i] = True
    
    # Second pass: find runs of 5+ consecutive answer lines and mark for removal
    remove = [False] * len(lines)
    run_start = None
    run_count = 0
    for i in range(len(lines)):
        if is_answer[i]:
            if run_start is None:
                run_start = i
            run_count += 1
        else:
            if run_count >= 5:
                for j in range(run_start, run_start + run_count):
                    remove[j] = True
            run_start = None
            run_count = 0
    if run_count >= 5:
        for j in range(run_start, run_start + run_count):
            remove[j] = True
    
    return '\n'.join(line for i, line in enumerate(lines) if not remove[i])


def parse_questions_from_text(text, source_label):
    """Parse numbered questions with a/b/c/d options from extracted text."""
    # First remove answer key blocks
    text = remove_answer_blocks(text)
    
    questions = []
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    lines = text.split('\n')

    current_q_num = None
    current_q_text = ""
    current_options = []
    current_option_letter = None
    current_option_text = ""

    def flush_question():
        nonlocal current_q_num, current_q_text, current_options, current_option_letter, current_option_text
        if current_option_letter and current_option_text.strip():
            current_options.append((current_option_letter, current_option_text.strip()))
        
        q_text = current_q_text.strip()
        
        # Filter out garbage:
        # - answer keys (single letter or comma-separated letters)
        # - empty questions
        # - page numbers or markers
        if current_q_num is not None and q_text:
            if not is_answer_key_line(q_text) and len(q_text) > 3:
                questions.append({
                    'num': current_q_num,
                    'text': q_text,
                    'options': current_options,
                    'source': source_label
                })
        
        current_q_num = None
        current_q_text = ""
        current_options = []
        current_option_letter = None
        current_option_text = ""

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # Skip page markers
        if re.match(r'^\d+$', stripped) and len(stripped) <= 3:
            continue
        if re.match(r'^[MP]\s*-\s*pilot', stripped, re.IGNORECASE):
            continue
        if re.match(r'^[MP]$', stripped):
            continue

        # New question
        q_match = re.match(r'^(\d+)\.\s+(.+)', stripped)
        if q_match:
            flush_question()
            current_q_num = int(q_match.group(1))
            rest = q_match.group(2)

            # Check if it's an answer-key line (e.g. "1. b")
            if is_answer_key_line(rest):
                current_q_text = rest  # will be filtered in flush
                continue

            # Check for inline options
            inline_match = re.match(r'^(.+?)\s+a\)\s+(.+)', rest)
            if inline_match:
                parts = re.split(r'\s+([a-d])\)\s+', rest)
                if len(parts) >= 3:
                    current_q_text = parts[0].strip()
                    for k in range(1, len(parts) - 1, 2):
                        current_options.append((parts[k], parts[k + 1].strip()))
                else:
                    current_q_text = inline_match.group(1)
                    current_option_letter = 'a'
                    current_option_text = inline_match.group(2)
            else:
                current_q_text = rest
            continue

        # Option line
        opt_match = re.match(r'^([a-d])\)\s*(.*)', stripped)
        if opt_match and current_q_num is not None:
            if current_option_letter and current_option_text.strip():
                current_options.append((current_option_letter, current_option_text.strip()))
            current_option_letter = opt_match.group(1)
            current_option_text = opt_match.group(2)
            continue

        # Continuation text
        if current_q_num is not None:
            if current_option_letter:
                current_option_text += " " + stripped
            else:
                current_q_text += " " + stripped

    flush_question()
    return questions


def format_question_md(q):
    """Format a single question as Markdown."""
    lines = []
    lines.append(f"**{q['num']}.** {q['text']}")
    lines.append("")
    for letter, text in q['options']:
        lines.append(f"   {letter}) {text}")
    if q['options']:
        lines.append("")
    return "\n".join(lines)


# ============================================================
# READ ALL SOURCES
# ============================================================
print("Čtu vzorové PDF...")
with open(os.path.join(BASE, "extracted_vzor.txt"), "r", encoding="utf-8") as f:
    vzor_text = f.read()

print("Čtu pracovní otázky...")
with open(os.path.join(BASE, "extracted_pracovni.txt"), "r", encoding="utf-8") as f:
    prac_text = f.read()

print("Čtu OCR text...")
ocr_path = os.path.join(BASE, "extracted_teorie_ocr.txt")
ocr_text = ""
if os.path.exists(ocr_path):
    with open(ocr_path, "r", encoding="utf-8") as f:
        ocr_text = f.read()

# ============================================================
# PARSE VZOR PDFs
# ============================================================
section_pattern = re.compile(r'={60}\n(.+?\.pdf)\n={60}')
splits = section_pattern.split(vzor_text)
vzor_data = {}
i = 1
while i < len(splits) - 1:
    vzor_data[splits[i].strip()] = splits[i + 1]
    i += 2

# ============================================================
# PARSE PILOTKY ODT
# ============================================================
odt_marker = "=== Pilotky - SPL.odt ==="
if odt_marker in prac_text:
    komunikace_pdf_text = prac_text[:prac_text.index(odt_marker)]
    pilotky_text = prac_text[prac_text.index(odt_marker) + len(odt_marker):]
else:
    komunikace_pdf_text = prac_text
    pilotky_text = ""

PILOTKY_HEADERS = [
    'LETECKÝ ZÁKON A POSTUPY ATZ',
    'LIDSKÁ VÝKONNOST',
    'METEOROLOGIE',
    'KOMUNIKACE',
    'ZÁKLADY LETU',
    'NAVIGACE',
    'PROVOZNÍ POSTUPY',
    'VÝKONY A PLÁNOVÁNÍ',
    'VŠEOBECNÁ ZNALOST LETADEL',
]

pilotky_sections = {}
for header in PILOTKY_HEADERS:
    start = pilotky_text.find(header)
    if start < 0:
        continue
    start_content = start + len(header)
    end = len(pilotky_text)
    for next_header in PILOTKY_HEADERS:
        if next_header == header:
            continue
        pos = pilotky_text.find(next_header, start_content)
        if 0 < pos < end:
            end = pos
    pilotky_sections[header] = pilotky_text[start_content:end]

# ============================================================
# PARSE OCR sections
# ============================================================
ocr_sections = {}
if ocr_text:
    ocr_splits = re.split(r'={60}\n(.+?)\n={60}', ocr_text)
    j = 1
    while j < len(ocr_splits) - 1:
        ocr_sections[ocr_splits[j].strip()] = ocr_splits[j + 1]
        j += 2

# ============================================================
# SECTION DEFINITIONS
# ============================================================
SECTIONS = [
    ("aerodynamika", "Aerodynamika a mechanika letu",
     "Aerodynamika.pdf", None, None),
    ("zaklady-letu", "Základy letu",
     None, "ZÁKLADY LETU", "ZÁKLADY LETU"),
    ("letadla", "Všeobecné znalosti letadel",
     "Letadla.pdf", "VŠEOBECNÁ ZNALOST LETADEL", "VSEOBECNE ZNALOSTI LETADEL"),
    ("letove-vykony", "Letové výkony a plánování",
     None, "VÝKONY A PLÁNOVÁNÍ", "LETOVÉ VÝKONY A PLÁNOVÁNÍ"),
    ("meteorologie", "Meteorologie",
     "Meteorologie.pdf", "METEOROLOGIE", "METEOROLOGIE"),
    ("navigace", "Navigace",
     "Navigace.pdf", "NAVIGACE", "NAVIGACE"),
    ("predpisy", "Letecké předpisy",
     "Predpisy.pdf", "LETECKÝ ZÁKON A POSTUPY ATZ", "LETECKE PREDPISY"),
    ("provozni-postupy", "Provozní postupy",
     None, "PROVOZNÍ POSTUPY", "PROVOZNÍ POSTUPY"),
    ("lidska-vykonnost", "Lidská výkonnost",
     None, "LIDSKÁ VÝKONNOST", "LIDSKA VYKONNOST"),
    ("komunikace", "Komunikace a spojovací předpisy",
     "SpojPredpisy.pdf", "KOMUNIKACE", None),
]

# ============================================================
# PARSE ANSWER KEYS FROM VZOR for mapping
# ============================================================
print("\nČtu odpovědi z vzor...")
from parsers.answer_key_parser import parse_answer_keys as _parse_ak

vzor_answer_map = _parse_ak(os.path.join(BASE, "extracted_vzor.txt"))
print(f"  Načteno {len(vzor_answer_map)} odpovědí.")

# ============================================================
# BUILD MARKDOWN
# ============================================================
print("\nSestavuji Markdown (s deduplicací)...")

md = []
md.append("# SPL Zkušební otázky — Kompletní seznam\n")
md.append("Komplexní sbírka otázek pro teoretickou zkoušku SPL (Sailplane Pilot Licence).\n")
md.append("**Zdroje (sloučeno a deduplikováno):**")
md.append("- `otázky vzor` — vzorové testy (PDF): Aerodynamika, Letadla, Meteorologie, Navigace, Předpisy, Spojovací předpisy")
md.append("- `Pilotky - SPL` — otázky SPL (ODT): Letecký zákon, Základy letu, Letové výkony, Lidská výkonnost, Meteorologie, Navigace, Provozní postupy, Komunikace, Všeobecné znalosti letadel")
md.append("- `2-4. KOMUNIKACE` — otázky z komunikace (PDF)")
md.append("- `otázky teorie 2025-4` — aktualizované otázky 2025 (OCR ze skenů)\n")
md.append("---\n")

toc_idx = len(md)
md.append("## Obsah\n")
md.append("TOC_PLACEHOLDER\n")
md.append("---\n")

toc_entries = []
total_qs = 0
total_removed = 0
unified_answer_keys: dict[str, str] = {}  # new_id -> answer letter(s)

for anchor, title, vzor_key, pilotky_key, ocr_key in SECTIONS:
    section_md = []
    section_md.append(f"## {title} " + "{" + f"#{anchor}" + "}" + "\n")
    sources_info = []
    all_questions: list[dict] = []

    # 1) Vzor PDF (highest priority)
    if vzor_key and vzor_key in vzor_data:
        qs = parse_questions_from_text(vzor_data[vzor_key], f"vzor/{vzor_key}")
        if qs:
            sources_info.append(f"vzorové testy `{vzor_key}` — {len(qs)} otázek")
            all_questions.extend(qs)

    # 2) Komunikace PDF
    if anchor == "komunikace" and komunikace_pdf_text:
        qs = parse_questions_from_text(komunikace_pdf_text, "komunikace/PDF")
        if qs:
            sources_info.append(f"komunikace PDF — {len(qs)} otázek")
            all_questions.extend(qs)

    # 3) Pilotky ODT (lowest priority)
    if pilotky_key and pilotky_key in pilotky_sections:
        qs = parse_questions_from_text(pilotky_sections[pilotky_key], f"pilotky/{pilotky_key}")
        if qs:
            sources_info.append(f"Pilotky SPL `{pilotky_key}` — {len(qs)} otázek")
            all_questions.extend(qs)

    if not all_questions:
        continue

    # --- DEDUPLICATE ---
    raw_count = len(all_questions)
    all_questions, removed = deduplicate_questions(all_questions)
    total_removed += removed

    # Renumber sequentially and build answer key mapping
    for idx, question in enumerate(all_questions, 1):
        question["original_num"] = question["num"]
        question["num"] = idx

        # Map answer key from vzor source
        new_id = f"{anchor}/{idx}"
        if question["source"].startswith("vzor/"):
            pdf_name = question["source"].split("/", 1)[1]  # e.g. "Aerodynamika.pdf"
            stem = pdf_name.replace(".pdf", "")
            old_vzor_id = f"vzor/{stem}/{question['original_num']}"
            answer = vzor_answer_map.get(old_vzor_id)
            if answer:
                unified_answer_keys[new_id] = answer

    # Section header with dedup stats
    if removed > 0:
        section_md.append(
            f"*{len(all_questions)} unikátních otázek "
            f"(z celkových {raw_count}, odstraněno {removed} duplikátů)*  "
        )
    else:
        section_md.append(f"*{len(all_questions)} otázek*  ")
    section_md.append("")

    # Flat list — no sub-source headers
    for question in all_questions:
        section_md.append(format_question_md(question))

    count = len(all_questions)
    total_qs += count
    toc_entries.append((anchor, title, count))
    md.append("\n".join(section_md))
    md.append("\n---\n")

# ============================================================
# OCR section (raw reference)
# ============================================================
if ocr_sections:
    ocr_md = []
    ocr_md.append("## Otázky teorie 2025 — OCR ze skenů\n")
    ocr_md.append("*Následující otázky byly extrahovány OCR ze skenovaných obrázků (2025-4).*  ")
    ocr_md.append("*Kvalita textu může být nižší — doporučujeme ověřit oproti originálním skenům.*\n")

    for subj_name, subj_text in ocr_sections.items():
        body = subj_text.strip()
        body = re.sub(r'---\s*\d+.*?\.jpg\s*---', '', body)
        if body.strip():
            ocr_md.append(f"### {subj_name}\n")
            ocr_md.append(f"```\n{body.strip()}\n```\n")

    toc_entries.append(("ocr-2025", "Otázky teorie 2025 — OCR ze skenů", 0))
    md.append("\n".join(ocr_md))
    md.append("\n---\n")

# ============================================================
# Fill TOC
# ============================================================
toc_lines = []
toc_lines.append(f"**Celkem: {total_qs} unikátních otázek (odstraněno {total_removed} duplikátů)**\n")
for anchor, title, count in toc_entries:
    suffix = f" ({count} otázek)" if count > 0 else ""
    toc_lines.append(f"- [{title}](#{anchor}){suffix}")
toc_lines.append("")

md[toc_idx + 1] = "\n".join(toc_lines)

# ============================================================
# WRITE MARKDOWN
# ============================================================
final = "\n".join(md)
with open(OUTPUT, "w", encoding="utf-8") as f:
    f.write(final)

# ============================================================
# WRITE ANSWER KEYS JSON
# ============================================================
with open(ANSWER_KEY_OUTPUT, "w", encoding="utf-8") as f:
    json.dump(unified_answer_keys, f, ensure_ascii=False, indent=2)

print(f"\n{'='*60}")
print(f"HOTOVO: {OUTPUT}")
print(f"Odpovědi: {ANSWER_KEY_OUTPUT} ({len(unified_answer_keys)} klíčů)")
print(f"Celkem unikátních otázek: {total_qs}")
print(f"Odstraněno duplikátů: {total_removed}")
print(f"Velikost souboru: {os.path.getsize(OUTPUT):,} bytes")
for anchor, title, count in toc_entries:
    print(f"  {title}: {count}")
print(f"{'='*60}")
