from __future__ import annotations

from pathlib import Path

src = Path(r"C:\Users\smm527\Desktop\高项-gemini.html")
out_dir = Path("docs/exam")
out_dir.mkdir(parents=True, exist_ok=True)
print("exists", src.exists())
if src.exists():
    text = src.read_text(encoding="utf-8", errors="replace")
    print("size", src.stat().st_size)
    print("chars", len(text))
    print("title?", text[:500].replace("\n", " ")[:500])
    (out_dir / "gaoxiang_gemini_source.html").write_text(text, encoding="utf-8")
    print((out_dir / "gaoxiang_gemini_source.html").resolve())
