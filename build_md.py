"""
Build comprehensive SPL question list in Markdown from all extracted sources.
"""
import os
import re

OUTPUT = r"c:\!Projects\Glider Exam\SPL_Otazky.md"

# ============================================================
# HELPER: Parse questions from text with pattern: number. question\n a) ... b) ... c) ... d) ...
# ============================================================
def parse_questions_from_text(text, source_label):
    """Parse numbered questions with a/b/c/d options from extracted text."""
    questions = []
    
    # Normalize line breaks
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    
    # Split into lines for processing
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
        
        # Check for new question: starts with number followed by . or )
        q_match = re.match(r'^(\d+)\.\s+(.+)', stripped)
        if q_match:
            flush_question()
            current_q_num = int(q_match.group(1))
            rest = q_match.group(2)
            # Check if options start on the same line
            opt_match = re.match(r'^(.+?)\s+a\)\s+(.+)', rest)
            if opt_match:
                current_q_text = opt_match.group(1)
                # Parse inline options
                inline_opts = re.split(r'\s+([a-d])\)\s+', rest)
                if len(inline_opts) > 1:
                    current_q_text = inline_opts[0]
                    for i in range(1, len(inline_opts)-1, 2):
                        current_options.append((inline_opts[i], inline_opts[i+1].strip()))
                else:
                    current_q_text = opt_match.group(1)
                    current_option_letter = 'a'
                    current_option_text = opt_match.group(2)
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


def format_question_md(q, global_num=None):
    """Format a single question as Markdown."""
    lines = []
    prefix = f"**{global_num}.** " if global_num else f"**{q['num']}.** "
    lines.append(f"{prefix}{q['text']}")
    lines.append("")
    for letter, text in q['options']:
        lines.append(f"   {letter}) {text}")
    lines.append("")
    return "\n".join(lines)


# ============================================================
# MAIN: Read all extracted sources and build MD
# ============================================================

BASE = r"c:\!Projects\Glider Exam"

md_parts = []
md_parts.append("# SPL Zkušební otázky — Kompletní seznam")
md_parts.append("")
md_parts.append("Komplexní sbírka otázek pro teoretickou zkoušku SPL (Sailplane Pilot Licence).")
md_parts.append("")
md_parts.append("**Zdroje:**")
md_parts.append("- `otázky vzor` — vzorové testy (PDF): Aerodynamika, Letadla, Meteorologie, Navigace, Předpisy, Spojovací předpisy")
md_parts.append("- `Pilotky - SPL` — otázky SPL (ODT): Letecký zákon, Základy letu, Letové výkony, Lidská výkonnost, Meteorologie, Navigace, Provozní postupy, Všeobecné znalosti")
md_parts.append("- `Komunikace` — otázky z komunikace (PDF)")
md_parts.append("- `otázky teorie 2025-4` — aktualizované otázky 2025 (OCR ze skenů)")
md_parts.append("")
md_parts.append("---")
md_parts.append("")
md_parts.append("## Obsah")
md_parts.append("")

# Define section mapping from vzor PDFs
vzor_sections = {
    'Aerodynamika.pdf': 'Aerodynamika a mechanika letu',
    'Letadla.pdf': 'Všeobecné znalosti letadel',
    'Meteorologie.pdf': 'Meteorologie',
    'Navigace.pdf': 'Navigace',
    'Predpisy.pdf': 'Letecké předpisy',
    'SpojPredpisy.pdf': 'Spojovací předpisy',
}

# ============================================================
# PART 1: Parse otazky vzor PDFs
# ============================================================
print("Reading vzor PDF text...")
with open(os.path.join(BASE, "extracted_vzor.txt"), "r", encoding="utf-8") as f:
    vzor_text = f.read()

# Split by section markers
section_pattern = re.compile(r'={60}\n(.+?\.pdf)\n={60}')
splits = section_pattern.split(vzor_text)

vzor_data = {}
i = 1
while i < len(splits) - 1:
    filename = splits[i].strip()
    content = splits[i + 1]
    vzor_data[filename] = content
    i += 2

# ============================================================
# PART 2: Parse Pilotky SPL (ODT)
# ============================================================
print("Reading pracovni text...")
with open(os.path.join(BASE, "extracted_pracovni.txt"), "r", encoding="utf-8") as f:
    prac_text = f.read()

# Split into KOMUNIKACE and Pilotky sections
odt_marker = "=== Pilotky - SPL.odt ==="
if odt_marker in prac_text:
    komunikace_text = prac_text[:prac_text.index(odt_marker)]
    pilotky_text = prac_text[prac_text.index(odt_marker) + len(odt_marker):]
else:
    komunikace_text = prac_text
    pilotky_text = ""

# ============================================================
# PART 3: Read OCR text
# ============================================================
print("Reading OCR text...")
ocr_path = os.path.join(BASE, "extracted_teorie_ocr.txt")
ocr_text = ""
if os.path.exists(ocr_path):
    with open(ocr_path, "r", encoding="utf-8") as f:
        ocr_text = f.read()

# ============================================================
# BUILD MARKDOWN — Section by section
# ============================================================

toc_entries = []
all_sections = []
global_q_count = 0

# === SECTION ORDER ===
section_order = [
    ("aerodynamika", "Aerodynamika a mechanika letu", "Aerodynamika.pdf"),
    ("letadla", "Všeobecné znalosti letadel", "Letadla.pdf"),
    ("meteorologie", "Meteorologie", "Meteorologie.pdf"),
    ("navigace", "Navigace", "Navigace.pdf"),
    ("predpisy", "Letecké předpisy", "Predpisy.pdf"),
    ("spoj_predpisy", "Spojovací předpisy", "SpojPredpisy.pdf"),
    ("komunikace", "Komunikace", None),
    ("letovy_zakon", "Letecký zákon a postupy ATZ (Pilotky SPL)", None),
    ("letove_vykony", "Letové výkony a plánování", None),
    ("lidska_vykonnost", "Lidská výkonnost", None),
    ("provozni_postupy", "Provozní postupy", None),
]

# Helper: split Pilotky ODT into sub-sections
pilotky_sections = {}
if pilotky_text:
    # The ODT has section headers like "LETECKÝ ZÁKON A POSTUPY ATZ", "ZÁKLADY LETU", etc.
    sec_pattern = re.compile(
        r'(LETECK[ÝY] Z[ÁA]KON.*?|Z[ÁA]KLADY LETU.*?|LETOV[ÉE] V[ÝY]KONY.*?|'
        r'LIDSK[ÁA] V[ÝY]KONNOST.*?|METEOROLOGIE.*?|NAVIGACE.*?|'
        r'PROVOZN[ÍI] POSTUPY.*?|V[ŠS]EOBECN[ÉE] ZNALOSTI.*?)'
        r'\s*\n',
        re.IGNORECASE
    )
    parts = sec_pattern.split(pilotky_text)
    j = 1
    while j < len(parts) - 1:
        header = parts[j].strip().upper()
        body = parts[j + 1]
        pilotky_sections[header] = body
        j += 2


print(f"\nBuilding Markdown...")
print(f"Vzor sections: {list(vzor_data.keys())}")
print(f"Pilotky sections: {list(pilotky_sections.keys())}")

# Build each section
for anchor, title, vzor_file in section_order:
    section_lines = []
    section_lines.append(f"## {title}")
    section_lines.append("")
    
    questions = []
    
    # Add questions from vzor PDF
    if vzor_file and vzor_file in vzor_data:
        pdf_qs = parse_questions_from_text(vzor_data[vzor_file], f"vzor/{vzor_file}")
        questions.extend(pdf_qs)
        section_lines.append(f"*Zdroj: vzorové testy — {len(pdf_qs)} otázek*")
        section_lines.append("")
    
    # Add questions from Pilotky ODT (matching sections)
    pilotky_key = None
    for k in pilotky_sections:
        if title.upper().startswith(k[:15]) or k.startswith(title.upper()[:15]):
            pilotky_key = k
            break
    
    if pilotky_key:
        pil_qs = parse_questions_from_text(pilotky_sections[pilotky_key], f"pilotky/{pilotky_key}")
        if pil_qs:
            section_lines.append(f"*Zdroj: Pilotky SPL — {len(pil_qs)} otázek*")
            section_lines.append("")
            questions.extend(pil_qs)
    
    # Add from komunikace
    if anchor == "komunikace":
        kom_qs = parse_questions_from_text(komunikace_text, "komunikace")
        questions.extend(kom_qs)
        section_lines.append(f"*Zdroj: Komunikace — {len(kom_qs)} otázek*")
        section_lines.append("")
    
    # Add Pilotky letecky zakon
    if anchor == "letovy_zakon":
        for k in pilotky_sections:
            if "ZÁKON" in k or "ZAKON" in k:
                pil_qs = parse_questions_from_text(pilotky_sections[k], f"pilotky/{k}")
                questions.extend(pil_qs)
                section_lines.append(f"*Zdroj: Pilotky SPL — {len(pil_qs)} otázek*")
                section_lines.append("")
                break
    
    if not questions:
        continue
    
    # Number and format questions
    for q in questions:
        global_q_count += 1
        section_lines.append(format_question_md(q, q['num']))
    
    toc_entries.append((anchor, title, len(questions)))
    all_sections.append("\n".join(section_lines))

# ============================================================
# APPEND OCR questions as a separate reference section
# ============================================================
if ocr_text.strip():
    ocr_section_lines = []
    ocr_section_lines.append("## Otázky teorie 2025 (OCR ze skenů)")
    ocr_section_lines.append("")
    ocr_section_lines.append("*Následující otázky byly extrahovány OCR ze skenovaných obrázků.*")
    ocr_section_lines.append("*Kvalita textu může být nižší — doporučujeme ověřit oproti originálním skenům.*")
    ocr_section_lines.append("")
    
    # Split by subject headers
    ocr_secs = re.split(r'={60}\n(.+?)\n={60}', ocr_text)
    j = 1
    while j < len(ocr_secs) - 1:
        subj = ocr_secs[j].strip()
        body = ocr_secs[j + 1].strip()
        if body:
            ocr_section_lines.append(f"### {subj}")
            ocr_section_lines.append("")
            # Clean up page markers
            body = re.sub(r'--- \d+.*?\.jpg ---', '', body)
            ocr_section_lines.append(body)
            ocr_section_lines.append("")
        j += 2
    
    toc_entries.append(("ocr_2025", "Otázky teorie 2025 (OCR)", 0))
    all_sections.append("\n".join(ocr_section_lines))

# ============================================================
# Assemble TOC
# ============================================================
toc_lines = []
total_qs = 0
for anchor, title, count in toc_entries:
    count_str = f" ({count} otázek)" if count > 0 else ""
    toc_lines.append(f"- [{title}](#{anchor}){count_str}")
    total_qs += count

md_parts.append(f"**Celkem: {total_qs}+ otázek**")
md_parts.append("")
md_parts.extend(toc_lines)
md_parts.append("")
md_parts.append("---")
md_parts.append("")

# Add all sections
for sec in all_sections:
    md_parts.append(sec)
    md_parts.append("")
    md_parts.append("---")
    md_parts.append("")

# Write output
final_md = "\n".join(md_parts)
with open(OUTPUT, "w", encoding="utf-8") as f:
    f.write(final_md)

print(f"\n{'='*60}")
print(f"DONE: {OUTPUT}")
print(f"Total questions parsed: {total_qs}+")
print(f"File size: {os.path.getsize(OUTPUT)} bytes")
print(f"{'='*60}")
