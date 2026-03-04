"""
Build comprehensive SPL question list in Markdown from all extracted sources.
v2 - Improved Pilotky section detection and question parsing.
"""
import os
import re

OUTPUT = r"c:\!Projects\Glider Exam\SPL_Otazky.md"
BASE = r"c:\!Projects\Glider Exam"


def parse_questions_from_text(text, source_label):
    """Parse numbered questions with a/b/c/d options from extracted text."""
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
        if current_q_num is not None and current_q_text.strip():
            questions.append({
                'num': current_q_num,
                'text': current_q_text.strip(),
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

        # Skip page markers like "2", "M - pilot", "P - pilot" at start of pages
        if re.match(r'^\d+$', stripped) and len(stripped) <= 3:
            continue
        if re.match(r'^[MP]\s*-\s*pilot', stripped, re.IGNORECASE):
            continue
        if re.match(r'^[MP]$', stripped):
            continue

        # Check for new question: number. text
        q_match = re.match(r'^(\d+)\.\s+(.+)', stripped)
        if q_match:
            flush_question()
            current_q_num = int(q_match.group(1))
            rest = q_match.group(2)

            # Check if options start inline: "question text a) opt1 b) opt2..."
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

        # Check for option line: a) b) c) d)
        opt_match = re.match(r'^([a-d])\)\s*(.*)', stripped)
        if opt_match and current_q_num is not None:
            if current_option_letter and current_option_text.strip():
                current_options.append((current_option_letter, current_option_text.strip()))
            current_option_letter = opt_match.group(1)
            current_option_text = opt_match.group(2)
            continue

        # Continuation of current context
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
    lines.append("")
    return "\n".join(lines)


# ============================================================
# READ ALL SOURCES
# ============================================================
print("Reading vzor PDF text...")
with open(os.path.join(BASE, "extracted_vzor.txt"), "r", encoding="utf-8") as f:
    vzor_text = f.read()

print("Reading pracovni text...")
with open(os.path.join(BASE, "extracted_pracovni.txt"), "r", encoding="utf-8") as f:
    prac_text = f.read()

print("Reading OCR text...")
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
# PARSE PILOTKY ODT — use exact known headers
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
for idx_h, header in enumerate(PILOTKY_HEADERS):
    start = pilotky_text.find(header)
    if start < 0:
        continue
    start += len(header)
    # Find the next header
    end = len(pilotky_text)
    for next_header in PILOTKY_HEADERS:
        if next_header == header:
            continue
        pos = pilotky_text.find(next_header, start)
        if 0 < pos < end:
            end = pos
    pilotky_sections[header] = pilotky_text[start:end]

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
# DEFINE output sections
# ============================================================
# (anchor_id, display_title, vzor_pdf_key, pilotky_key, ocr_key)
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
# BUILD MARKDOWN
# ============================================================
print("\nBuilding Markdown...")

md = []
md.append("# SPL Zkušební otázky — Kompletní seznam\n")
md.append("Komplexní sbírka otázek pro teoretickou zkoušku SPL (Sailplane Pilot Licence).\n")
md.append("**Zdroje:**")
md.append("- `otázky vzor` — vzorové testy (PDF): Aerodynamika, Letadla, Meteorologie, Navigace, Předpisy, Spojovací předpisy")
md.append("- `Pilotky - SPL` — otázky SPL (ODT): Letecký zákon, Základy letu, Letové výkony, Lidská výkonnost, Meteorologie, Navigace, Provozní postupy, Komunikace, Všeobecné znalosti letadel")
md.append("- `2-4. KOMUNIKACE` — otázky z komunikace (PDF)")
md.append("- `otázky teorie 2025-4` — aktualizované otázky 2025 (OCR ze skenů)\n")
md.append("---\n")

# ============================================================
# TABLE OF CONTENTS (placeholder — fill after processing)
# ============================================================
toc_placeholder_idx = len(md)
md.append("## Obsah\n")
md.append("TOC_PLACEHOLDER\n")
md.append("---\n")

toc_entries = []
total_qs = 0

for anchor, title, vzor_key, pilotky_key, ocr_key in SECTIONS:
    section_md = []
    section_md.append(f"## {title}\n")
    sources_info = []
    all_questions = []

    # 1) Vzor PDF questions
    if vzor_key and vzor_key in vzor_data:
        qs = parse_questions_from_text(vzor_data[vzor_key], f"vzor/{vzor_key}")
        if qs:
            sources_info.append(f"vzorové testy `{vzor_key}` — {len(qs)} otázek")
            all_questions.extend(qs)

    # 2) Komunikace PDF (only for komunikace section)
    if anchor == "komunikace" and komunikace_pdf_text:
        qs = parse_questions_from_text(komunikace_pdf_text, "komunikace/PDF")
        if qs:
            sources_info.append(f"komunikace PDF — {len(qs)} otázek")
            all_questions.extend(qs)

    # 3) Pilotky ODT
    if pilotky_key and pilotky_key in pilotky_sections:
        qs = parse_questions_from_text(pilotky_sections[pilotky_key], f"pilotky/{pilotky_key}")
        if qs:
            sources_info.append(f"Pilotky SPL `{pilotky_key}` — {len(qs)} otázek")
            all_questions.extend(qs)

    if not all_questions:
        continue

    # Write source info
    for s in sources_info:
        section_md.append(f"*Zdroj: {s}*  ")
    section_md.append("")

    # Separate questions by source, with sub-headers
    current_source = None
    for q in all_questions:
        if q['source'] != current_source:
            current_source = q['source']
            section_md.append(f"### Zdroj: {current_source}\n")
        section_md.append(format_question_md(q))

    count = len(all_questions)
    total_qs += count
    toc_entries.append((anchor, title, count))
    md.append("\n".join(section_md))
    md.append("\n---\n")

# ============================================================
# OCR section (reference)
# ============================================================
if ocr_sections:
    ocr_md = []
    ocr_md.append("## Otázky teorie 2025 — OCR ze skenů\n")
    ocr_md.append("*Následující otázky byly extrahovány OCR ze skenovaných obrázků (2025-4).*  ")
    ocr_md.append("*Kvalita textu může být nižší — doporučujeme ověřit oproti originálním skenům v adresáři `Source/otazky teorie 2025-4`.*\n")

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
toc_lines.append(f"**Celkem: ~{total_qs} otázek**\n")
for anchor, title, count in toc_entries:
    suffix = f" ({count} otázek)" if count > 0 else ""
    toc_lines.append(f"- [{title}](#{anchor}){suffix}")
toc_lines.append("")

md[toc_placeholder_idx + 1] = "\n".join(toc_lines)

# ============================================================
# WRITE
# ============================================================
final = "\n".join(md)
with open(OUTPUT, "w", encoding="utf-8") as f:
    f.write(final)

print(f"\n{'='*60}")
print(f"HOTOVO: {OUTPUT}")
print(f"Celkem otázek: ~{total_qs}")
print(f"Velikost souboru: {os.path.getsize(OUTPUT):,} bytes")
for anchor, title, count in toc_entries:
    print(f"  {title}: {count}")
print(f"{'='*60}")
