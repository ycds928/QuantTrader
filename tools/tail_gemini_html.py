from pathlib import Path

s = Path("docs/exam/gaoxiang_gemini_source.html").read_text(encoding="utf-8")
print(s[-2000:])
