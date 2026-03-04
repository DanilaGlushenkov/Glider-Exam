import fitz
import os
import zipfile
import xml.etree.ElementTree as ET

OUTPUT_DIR = r"c:\!Projects\Glider Exam"

def extract_pdf(path):
    doc = fitz.open(path)
    text = ""
    for page in doc:
        text += page.get_text() + "\n"
    doc.close()
    return text

def extract_odt(path):
    """Extract text from ODT file (zipped XML)."""
    text_parts = []
    with zipfile.ZipFile(path, 'r') as z:
        with z.open('content.xml') as f:
            tree = ET.parse(f)
            root = tree.getroot()
            # Get all text content
            for elem in root.iter():
                if elem.text:
                    text_parts.append(elem.text)
                if elem.tail:
                    text_parts.append(elem.tail)
    return "\n".join(text_parts)

def extract_doc_raw(path):
    """Try to extract readable text from old .doc binary format."""
    with open(path, 'rb') as f:
        raw = f.read()
    # Try to decode as much text as possible
    # Old .doc files have text in various encodings
    text_parts = []
    current = []
    for byte in raw:
        if 32 <= byte <= 126 or byte in (10, 13, 9):
            current.append(chr(byte))
        elif byte >= 128:
            # Try to handle as windows-1250 (Czech encoding)
            try:
                current.append(bytes([byte]).decode('windows-1250'))
            except:
                if current:
                    text_parts.append(''.join(current))
                    current = []
        else:
            if current:
                text_parts.append(''.join(current))
                current = []
    if current:
        text_parts.append(''.join(current))
    
    # Filter out very short fragments (binary noise)
    meaningful = [t for t in text_parts if len(t) > 10]
    return '\n'.join(meaningful)

# ===== EXTRACT PDFs from otazky vzor =====
print("=" * 60)
print("EXTRACTING: otazky vzor (PDF sample questions)")
print("=" * 60)

vzor_dir = os.path.join(OUTPUT_DIR, r"Source\otazky vzor-20260304T104642Z-3-001\otazky vzor")
vzor_text = ""
for f in sorted(os.listdir(vzor_dir)):
    if f.endswith('.pdf'):
        print(f"  Processing: {f}")
        text = extract_pdf(os.path.join(vzor_dir, f))
        vzor_text += f"\n{'='*60}\n{f}\n{'='*60}\n{text}\n"

with open(os.path.join(OUTPUT_DIR, "extracted_vzor.txt"), "w", encoding="utf-8") as out:
    out.write(vzor_text)
print(f"  => extracted_vzor.txt ({len(vzor_text)} chars)")

# ===== EXTRACT PDF from otazky pracovni =====
print("\n" + "=" * 60)
print("EXTRACTING: otazky pracovni z podhoran (PDF + ODT)")
print("=" * 60)

prac_dir = os.path.join(OUTPUT_DIR, r"Source\otazky pracovni z podhoran-20260304T104641Z-3-001\otazky pracovni z podhoran")
prac_text = ""

pdf_path = os.path.join(prac_dir, "2-4. KOMUNIKACE.pdf")
print(f"  Processing: 2-4. KOMUNIKACE.pdf")
prac_text += extract_pdf(pdf_path)

odt_path = os.path.join(prac_dir, "Pilotky - SPL.odt")
print(f"  Processing: Pilotky - SPL.odt")
prac_text += "\n\n=== Pilotky - SPL.odt ===\n"
prac_text += extract_odt(odt_path)

with open(os.path.join(OUTPUT_DIR, "extracted_pracovni.txt"), "w", encoding="utf-8") as out:
    out.write(prac_text)
print(f"  => extracted_pracovni.txt ({len(prac_text)} chars)")

# ===== EXTRACT .doc from od milose =====
print("\n" + "=" * 60)
print("EXTRACTING: od milose (.doc files)")
print("=" * 60)

milos_dir = os.path.join(OUTPUT_DIR, r"Source\od milose-20260304T104639Z-3-001\od milose")
milos_text = ""
for f in sorted(os.listdir(milos_dir)):
    if f.endswith('.doc'):
        print(f"  Processing: {f}")
        text = extract_doc_raw(os.path.join(milos_dir, f))
        milos_text += f"\n{'='*60}\n{f}\n{'='*60}\n{text}\n"

with open(os.path.join(OUTPUT_DIR, "extracted_milos.txt"), "w", encoding="utf-8") as out:
    out.write(milos_text)
print(f"  => extracted_milos.txt ({len(milos_text)} chars)")

print("\n\nDONE! All text extracted.")
print(f"Files created in: {OUTPUT_DIR}")
