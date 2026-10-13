"""
make_figures.py - draws the vocabulary diagram and the two subgraphs used in the report
directly from streaming_catalogue.ttl, so every arrow is a triple in the file.

    pip install rdflib        (and install Graphviz so that the `dot` command works)
    python make_figures.py    # writes PNG + DOT files into ./figures

Author: Aayush Sharda (Reg. No. 235890136) - CSE 4007 Semantic Web, Case 2C
"""
import html
import subprocess
from pathlib import Path
from rdflib import Graph, Literal, URIRef, RDF, RDFS, XSD, Namespace
SV = Namespace("https://example.org/streaming/vocab#")
EX = Namespace("https://example.org/streaming/id/")
HERE = Path(__file__).resolve().parent
g = Graph(); g.parse(HERE / "streaming_catalogue.ttl", format="turtle")
OUT = str(HERE / "figures") + "/"
(HERE / "figures").mkdir(exist_ok=True)
FONT = "Carlito"

PAL = {  # fill, border
  "work":   ("#DCEBFA", "#0070C0"),
  "credit": ("#E1F0DE", "#3B8A3E"),
  "version":("#E9E2F5", "#6B4FA3"),
  "licence":("#FDEBD3", "#D9822B"),
  "avail":  ("#FBE0DE", "#C0504D"),
  "ref":    ("#EDEDED", "#7F7F7F"),
}
def local(u):
    s = str(u)
    for pre, ns in (("sv:", str(SV)), ("ex:", str(EX))):
        if s.startswith(ns): return s[len(ns):]
    return s
def kind_of(u):
    types = {local(o) for o in g.objects(u, RDF.type)}
    if types & {"Film","Series","Episode"}: return "work"
    if "Contribution" in types: return "credit"
    if "LanguageVersion" in types: return "version"
    if "Licence" in types: return "licence"
    if "AvailabilityEvent" in types: return "avail"
    return "ref"
def cls_of(u):
    for o in g.objects(u, RDF.type): return local(o)
def inode(u, label_override=None):
    k = kind_of(u); fill, border = PAL[k]
    name = html.escape(label_override or local(u))
    c = html.escape(cls_of(u))
    return (f'"{local(u)}" [shape=box, style="rounded,filled", fillcolor="{fill}", color="{border}", penwidth=1.2, '
            f'label=<<FONT POINT-SIZE="10"><B>{name}</B></FONT><BR/><FONT POINT-SIZE="7.5" COLOR="#555555"><I>{c}</I></FONT>>];')
def lit_node(nid, lit):
    dt = {XSD.date:"xsd:date", XSD.duration:"xsd:duration", XSD.integer:"xsd:integer"}.get(lit.datatype, "")
    return (f'"{nid}" [shape=box, style="filled,dashed", fillcolor="#FFFFFF", color="#888888", '
            f'label=<<FONT POINT-SIZE="8.5" FACE="DejaVu Sans Mono">{html.escape(str(lit))}</FONT><BR/><FONT POINT-SIZE="7" COLOR="#777777">{dt}</FONT>>];')
HEAD = f'''digraph G {{
  graph [fontname="{FONT}", rankdir=TB, nodesep=0.22, ranksep=0.55, pad=0.12, dpi=300, bgcolor="white", compound=true, newrank=true];
  node  [fontname="{FONT}"];
  edge  [fontname="{FONT}", fontsize=8, color="#666666", fontcolor="#333333", arrowsize=0.7];
'''
def render(name, dot):
    open(OUT+name+".dot","w").write(dot)
    subprocess.run(["dot","-Tpng",OUT+name+".dot","-o",OUT+name+".png"], check=True)

# ---------------- Figure: Riverline rights chain (instance subgraph) ----------------
def inode_lits(u, props):
    """Resource box with its typed-literal triples listed as rows underneath."""
    k = kind_of(u); fill, border = PAL[k]
    rows = ""
    for p in props:
        for o in g.objects(u, p):
            dt = {XSD.date: "xsd:date", XSD.duration: "xsd:duration", XSD.integer: "xsd:integer"}[o.datatype]
            rows += (f'<TR><TD ALIGN="LEFT"><FONT POINT-SIZE="8" FACE="DejaVu Sans Mono">{local(p)}</FONT></TD>'
                     f'<TD ALIGN="LEFT"><FONT POINT-SIZE="8" FACE="DejaVu Sans Mono">{html.escape(str(o))}</FONT>'
                     f'<FONT POINT-SIZE="7" COLOR="#777777"> ^^{dt}</FONT></TD></TR>')
    head = (f'<TR><TD COLSPAN="2" BORDER="0"><FONT POINT-SIZE="10"><B>{html.escape(local(u))}</B></FONT><BR/>'
            f'<FONT POINT-SIZE="7.5" COLOR="#555555"><I>{html.escape(cls_of(u))}</I></FONT></TD></TR>')
    body = (f'<TABLE BORDER="1" COLOR="{border}" BGCOLOR="{fill}" CELLBORDER="0" CELLSPACING="0" CELLPADDING="3" STYLE="rounded">'
            f'{head}{"<HR/>" + rows if rows else ""}</TABLE>')
    return f'"{local(u)}" [shape=plain, label=<{body}>];'
nodes_by_cluster = {
 "Availability layer (what the platform offers)": ["Availability_IN_Riverline", "Active"],
 "Licence layer (the legal right)": ["Licence_IN_Riverline", "India"],
 "Version layer": ["Riverline_EN","English","Riverline_HI","Hindi"],
 "Creative work layer (the title)": ["Riverline","Drama"],
}
lit_props = {"Availability_IN_Riverline":[SV.startDate, SV.endDate, SV.asOfDate],
             "Licence_IN_Riverline":[SV.startDate, SV.endDate],
             "Riverline_EN":[SV.runtime], "Riverline_HI":[SV.runtime]}
ids = {n: EX[n] for c in nodes_by_cluster.values() for n in c}
cluster_style = {0:("#FBE0DE","#C0504D"),1:("#FDEBD3","#D9822B"),2:("#E9E2F5","#6B4FA3"),3:("#DCEBFA","#0070C0")}
dot = HEAD
for ci, (label, members) in enumerate(nodes_by_cluster.items()):
    fill, border = cluster_style[ci]
    dot += f'  subgraph cluster_{ci} {{ label=<<B>{html.escape(label)}</B>>; labeljust=l; fontsize=9.5; style="rounded,dashed"; color="{border}"; penwidth=1.0; bgcolor="{fill}33";\n    {{ rank=same;\n'
    for m in members:
        dot += "      " + (inode_lits(ids[m], lit_props[m]) if m in lit_props else inode(ids[m])) + "\n"
    dot += "    }\n  }\n"
real = []
for s_, p_, o_ in g:
    if isinstance(o_, URIRef) and s_ in ids.values() and o_ in ids.values() and p_ in {SV.underLicence, SV.availabilityStatus, SV.licensedVersion, SV.territory, SV.isVersionOf, SV.inLanguage, SV.hasGenre}:
        real.append((local(s_), local(o_), local(p_)))
for s_, o_, p_ in sorted(real):
    dot += f'  "{s_}" -> "{o_}" [label="{p_}"];\n'
dot += "}\n"
render("subgraph_riverline", dot)
print("riverline edges:", len(real), "| literal rows:", sum(len(list(g.objects(ids[m], p))) for m in lit_props for p in lit_props[m]))

# ---------------- Figure: Maya Sen's three credits ----------------
maya = EX.MayaSen
credits = sorted({s for s in g.subjects(SV.contributor, maya)})
dot = HEAD.replace("rankdir=TB", "rankdir=LR").replace("ranksep=0.55","ranksep=0.9")
dot += "  " + inode(maya) + "\n"
all_edges = []
for c in credits:
    dot += "  " + inode(c) + "\n"
    all_edges.append((local(c), local(maya), "contributor"))
    for p in (SV.contributionWork, SV.role):
        for o in g.objects(c, p):
            dot += "  " + inode(o) + "\n"
            all_edges.append((local(c), local(o), local(p)))
dot += "  { rank=same; " + " ".join(f'"{local(c)}";' for c in credits) + " }\n"
for s,o,p in all_edges:
    dot += f'  "{s}" -> "{o}" [label="{p}"];\n'
dot += "}\n"
# dedupe node lines (roles / works appear once each already)
render("subgraph_mayasen", dot)
print("maya credits:", [local(c) for c in credits], "edges", len(all_edges))

# ---------------- Figure: schema diagram (classes, object props, data props) ----------------
classes = sorted({s for s in g.subjects(RDF.type, RDFS.Class)}, key=local)
layer_of = {"CreativeWork":"work","Film":"work","Series":"work","Episode":"work",
            "Contribution":"credit","LanguageVersion":"version","PeriodRecord":"licence","Licence":"licence",
            "AvailabilityEvent":"avail"}
def schema_node(c):
    k = layer_of.get(local(c), "ref"); fill, border = PAL[k]
    dprops = []
    for p in g.subjects(RDFS.domain, c):
        r = g.value(p, RDFS.range)
        if r is not None and str(r).startswith(str(XSD)):
            dprops.append((local(p), "xsd:"+str(r).split("#")[-1]))
    rows = "".join(f'<TR><TD ALIGN="LEFT"><FONT POINT-SIZE="8" FACE="DejaVu Sans Mono">{html.escape(n)}</FONT></TD><TD ALIGN="LEFT"><FONT POINT-SIZE="7" COLOR="#555555">{html.escape(t)}</FONT></TD></TR>' for n,t in sorted(dprops))
    body = f'<TABLE BORDER="1" COLOR="{border}" BGCOLOR="{fill}" CELLBORDER="0" CELLSPACING="0" CELLPADDING="3" STYLE="rounded"><TR><TD COLSPAN="2" BORDER="0"><FONT POINT-SIZE="10"><B>{html.escape(local(c))}</B></FONT></TD></TR>'
    if rows: body += '<HR/>' + rows
    body += '</TABLE>'
    return f'  "{local(c)}" [shape=plain, label=<{body}>];\n'
dot = f'''digraph S {{
  graph [fontname="{FONT}", rankdir=TB, nodesep=0.25, ranksep=0.55, pad=0.12, dpi=300, bgcolor="white", splines=true];
  node  [fontname="{FONT}"];
  edge  [fontname="{FONT}", fontsize=8, color="#666666", fontcolor="#333333", arrowsize=0.7];
'''
for c in classes: dot += schema_node(c)
objp = [p for p in g.subjects(RDF.type, RDF.Property) if str(g.value(p, RDFS.range)).startswith(str(SV))]
for p in sorted(objp, key=local):
    d, r = g.value(p, RDFS.domain), g.value(p, RDFS.range)
    dot += f'  "{local(d)}" -> "{local(r)}" [label="{local(p)}"];\n'
for s,o in g.subject_objects(RDFS.subClassOf):
    dot += f'  "{local(s)}" -> "{local(o)}" [arrowhead=empty, style=dashed, color="#0070C0"];\n'
dot += "}\n"
render("schema", dot)
print("object props:", len(objp))
