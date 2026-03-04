import os

import easyocr
import numpy as np
from PIL import Image

reader = easyocr.Reader(['cs', 'en'], gpu=False)

base = r"c:\!Projects\Glider Exam\Source\otazky teorie 2025-4-20260304T104641Z-3-001\otazky teorie 2025-4"
output_path = r"c:\!Projects\Glider Exam\extracted_teorie_ocr.txt"

subjects = sorted(os.listdir(base))

with open(output_path, "w", encoding="utf-8") as out:
    for subject in subjects:
        subject_dir = os.path.join(base, subject)
        if not os.path.isdir(subject_dir):
            continue
        
        out.write(f"\n{'='*60}\n")
        out.write(f"{subject.upper()}\n")
        out.write(f"{'='*60}\n\n")
        print(f"\nProcessing: {subject}")
        
        jpgs = sorted([f for f in os.listdir(subject_dir) if f.lower().endswith('.jpg')])
        for jpg in jpgs:
            jpg_path = os.path.join(subject_dir, jpg)
            print(f"  OCR: {jpg}", flush=True)
            try:
                # Use PIL to read (handles Unicode paths), then convert to numpy
                img = Image.open(jpg_path)
                img_np = np.array(img)
                results = reader.readtext(img_np, detail=0, paragraph=True)
                out.write(f"--- {jpg} ---\n")
                for line in results:
                    out.write(line + "\n")
                out.write("\n")
                out.flush()
            except Exception as e:
                print(f"  ERROR: {e}")
                out.write(f"--- {jpg} --- ERROR: {e}\n\n")

print(f"\nDone! Output: {output_path}")
sz = os.path.getsize(output_path)
print(f"Size: {sz} bytes")
