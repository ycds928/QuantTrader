from pathlib import Path

p = Path("docs/exam/高项-gemini-案例计算论文扩展版.html")
s = p.read_text(encoding="utf-8")
print("exists", p.exists())
print("size", p.stat().st_size)
for term in [
    "论文范文模块",
    "论信息系统项目的交付绩效域管理",
    "智慧门急诊与互联网医院一体化平台",
    "摘要：",
    "一篇范文多题改写模板",
    "风险管理/不确定性绩效域",
    "医疗项目加分点",
    "近 5 年论文题型趋势",
]:
    print(term, term in s)
