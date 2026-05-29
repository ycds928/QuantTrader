from pathlib import Path

p = Path("docs/exam/高项-gemini-案例计算扩展版.html")
s = p.read_text(encoding="utf-8")
print("exists", p.exists())
print("size", p.stat().st_size)
for term in [
    "案例分析与计算题扩展版",
    "找错改错万能句",
    "常见错误标准答案",
    "计算题公式总表",
    "挣值题四步法",
    "网络图题四步法",
    "CV=EV-AC",
    "TCPI",
    "需求跟踪矩阵",
    "变更控制",
]:
    print(term, term in s)
