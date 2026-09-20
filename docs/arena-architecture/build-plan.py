"""Embed locally rendered PlantUML diagrams into the standalone HTML."""
from pathlib import Path
import html
import re
root = Path(__file__).resolve().parent
template = (root / "plan.template.html").read_text()
def diagram(match):
    name, kind, title, caption = match.group(1).split("|", 3)
    svg = (root / f"{name}.svg").read_text()
    svg = svg[svg.index("<svg"):]
    svg = svg.replace('preserveAspectRatio="none"', 'preserveAspectRatio="xMidYMid meet"')
    svg = svg.replace("<svg ", f'<svg role="img" aria-label="{html.escape(title, quote=True)}" ', 1)
    ids = re.findall(r'\bid="([^"]+)"', svg)
    for old_id in ids:
        new_id = name + "-" + old_id
        svg = svg.replace('id="' + old_id + '"', 'id="' + new_id + '"')
        svg = svg.replace('url(#' + old_id + ')', 'url(#' + new_id + ')')
        svg = svg.replace('href="#' + old_id + '"', 'href="#' + new_id + '"')
    return f'''<figure class="diagram" id="diagram-{name}">
<figcaption class="diagram-head"><div><span class="diagram-type">{html.escape(kind)}</span><strong class="diagram-title">{html.escape(title)}</strong></div><div class="diagram-actions"><button type="button" data-action="fit">Уместить</button><button type="button" data-action="native">1:1</button><button type="button" data-action="expand">Развернуть ↗</button><a href="arena-architecture/{name}.puml" download>PlantUML</a><a href="arena-architecture/{name}.svg" download>SVG</a></div></figcaption>
<div class="diagram-viewport"><div class="diagram-canvas">{svg}</div></div><div class="diagram-caption">{html.escape(caption)}</div></figure>'''
output = re.sub(r"@@diagram:([^@]+)@@", diagram, template)
assert "@@diagram:" not in output
target = root.parent / "arena-architecture-review.html"
target.write_text(output)
(root.parent / "arena-integration-plan.html").write_text(output)
print(str(target) + ": " + str(len(output.encode())) + " bytes")
