#!/usr/bin/env python3
"""3つのMarkdownを1つのPDFに統合する。日本語フォント(IPAGothic)対応。"""
import datetime
import markdown
from weasyprint import HTML

DOCS = [
    ("session_handoff.md",        "1. プロジェクト引き継ぎメモ"),
    ("slide_design_handbook.md",  "2. スライド設計ハンドブック"),
    ("design_judgment_layer.md",  "3. デザイン判断レイヤー仕様"),
]
TITLE = "提案書生成エージェント 設計ドキュメント集"
DATE = datetime.date.today().isoformat()

md = markdown.Markdown(extensions=["tables", "fenced_code", "toc", "sane_lists"])

sections = []
for path, heading in DOCS:
    with open(path, encoding="utf-8") as f:
        body = f.read()
    html_body = md.convert(body)
    md.reset()
    sections.append(
        f'<section class="doc"><div class="doc-label">{heading}</div>{html_body}</section>'
    )

cover = f"""
<section class="cover">
  <h1>{TITLE}</h1>
  <p class="sub">設計の意図 → 原則 → 具体仕様</p>
  <ul class="toc">
    {''.join(f'<li>{h}</li>' for _, h in DOCS)}
  </ul>
  <p class="date">生成日: {DATE}</p>
</section>
"""

css = """
@page {
  size: A4; margin: 18mm 16mm 20mm 16mm;
  @bottom-center { content: counter(page) " / " counter(pages);
                   font-size: 9pt; color: #888; }
}
@page :first { @bottom-center { content: ""; } }
* { font-family: "IPAGothic", "IPAPGothic", sans-serif; }
body { color: #1a1a1a; font-size: 10pt; line-height: 1.7; }
.cover { text-align: center; padding-top: 70mm; page-break-after: always; }
.cover h1 { font-size: 24pt; border: none; margin-bottom: 6mm; }
.cover .sub { color: #555; font-size: 12pt; }
.cover .toc { list-style: none; padding: 0; margin: 20mm auto 0; display: inline-block; text-align: left; }
.cover .toc li { font-size: 12pt; margin: 3mm 0; color: #333; }
.cover .date { margin-top: 30mm; color: #888; font-size: 9pt; }
.doc { page-break-before: always; }
.doc-label { font-size: 9pt; color: #fff; background: #2c3e50;
             padding: 2mm 4mm; border-radius: 2px; display: inline-block; margin-bottom: 5mm; }
h1 { font-size: 18pt; border-bottom: 2px solid #2c3e50; padding-bottom: 2mm; margin-top: 8mm; }
h2 { font-size: 14pt; color: #2c3e50; border-bottom: 1px solid #ccc; padding-bottom: 1mm; margin-top: 7mm; }
h3 { font-size: 11.5pt; color: #34495e; margin-top: 5mm; }
h4 { font-size: 10.5pt; color: #555; }
p, li { font-size: 10pt; }
table { border-collapse: collapse; width: 100%; margin: 3mm 0; font-size: 8.7pt; }
th, td { border: 1px solid #bbb; padding: 1.6mm 2.2mm; text-align: left; vertical-align: top; }
th { background: #eef2f5; font-weight: bold; }
tr:nth-child(even) td { background: #f8f9fa; }
code { background: #f0f0f0; padding: 0.3mm 1mm; border-radius: 2px; font-size: 8.7pt;
       font-family: "IPAGothic", monospace; }
pre { background: #f6f8fa; border: 1px solid #ddd; border-radius: 3px; padding: 3mm;
      font-size: 8.3pt; line-height: 1.45; white-space: pre-wrap; word-break: break-all; page-break-inside: avoid; }
pre code { background: none; padding: 0; }
blockquote { border-left: 3px solid #2c3e50; margin: 3mm 0; padding: 1mm 4mm;
             background: #f7f9fb; color: #333; }
strong { color: #c0392b; }
hr { border: none; border-top: 1px solid #ddd; margin: 5mm 0; }
"""

html = f"<!doctype html><html><head><meta charset='utf-8'><style>{css}</style></head><body>{cover}{''.join(sections)}</body></html>"

out = "proposal_agent_design_docs.pdf"
HTML(string=html).write_pdf(out)
print("wrote", out)
