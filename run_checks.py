#!/usr/bin/env python3
"""
run_checks.py - reproduces every number and query result quoted in the report.

    pip install rdflib owlrl
    python run_checks.py            # prints everything
    python run_checks.py --json results.json

It reads streaming_catalogue.ttl and queries.rq from the same folder.
Author: Aayush Sharda (Reg. No. 235890136) - CSE 4007 Semantic Web, Case 2C
"""
import json
import re
import sys
from pathlib import Path

import owlrl
from rdflib import RDF, RDFS, XSD, Graph, Literal, Namespace, URIRef

HERE = Path(__file__).resolve().parent
TTL = HERE / "streaming_catalogue.ttl"
RQ = HERE / "queries.rq"
SV = Namespace("https://example.org/streaming/vocab#")
EX = Namespace("https://example.org/streaming/id/")


def load():
    g = Graph()
    g.parse(TTL, format="turtle")
    return g


def rdfs_closure(g):
    """Copy of g plus everything RDFS entails (no axiomatic triples)."""
    c = Graph()
    for t in g:
        c.add(t)
    owlrl.DeductiveClosure(owlrl.RDFS_Semantics, axiomatic_triples=False,
                           datatype_axioms=False).expand(c)
    return c


def short(term):
    if isinstance(term, URIRef):
        return str(term).replace(str(EX), "ex:").replace(str(SV), "sv:")
    return str(term)


def read_queries():
    text = RQ.read_text()
    parts = re.split(r"(?m)^# (Q\d+)\. ", text)
    out = {}
    for i in range(1, len(parts), 2):
        qid, rest = parts[i], parts[i + 1]
        lines = rest.split("\n")
        title, j = lines[0].strip(), 1
        while j < len(lines) and lines[j].startswith("#") and not lines[j].startswith("# ---"):
            line = lines[j].lstrip("# ").strip()
            if not line.startswith("Expected:"):
                title += " " + line
            j += 1
        body = "\n".join(lines[j:])
        body = re.sub(r"(?m)^#.*$", "", body).strip()
        out[qid] = {"title": title, "text": body}
    return out


def run(g, text):
    res = g.query(text)
    if res.type == "ASK":
        return {"ask": bool(res.askAnswer)}
    vars_ = [str(v) for v in res.vars]
    rows = [[short(r[v]) if r[v] is not None else "" for v in res.vars] for r in res]
    return {"vars": vars_, "rows": rows}


def main():
    out = {}
    raw = load()
    closed = rdfs_closure(raw)

    # ---- counts -------------------------------------------------------
    vocab = [t for t in raw if str(t[0]).startswith(str(SV))]
    classes = set(raw.subjects(RDF.type, RDFS.Class))
    props = set(raw.subjects(RDF.type, RDF.Property))
    individuals = {s for s, o in raw.subject_objects(RDF.type) if o in classes}
    lit_counts = {}
    ill_typed = []
    for s, p, o in raw:
        if isinstance(o, Literal) and o.datatype:
            k = str(o.datatype).split("#")[-1]
            lit_counts[k] = lit_counts.get(k, 0) + 1
            if o.value is None:
                ill_typed.append((str(s), str(p), str(o)))
    terms = {n for s, p, o in raw for n in (s, o) if isinstance(n, URIRef)
             and (str(n).startswith(str(EX)) or str(n).startswith(str(SV)))}
    untyped = [str(t) for t in terms if (t, RDF.type, None) not in raw]
    inferred = set(closed) - set(raw)
    app = {t for t in inferred if t[1] == RDF.type and isinstance(t[2], URIRef)
           and str(t[2]).startswith(str(SV))}
    out["counts"] = {
        "explicit": len(raw), "vocabulary": len(vocab), "data": len(raw) - len(vocab),
        "classes": len(classes), "properties": len(props),
        "object_properties": len([p for p in props if str(raw.value(p, RDFS.range)).startswith(str(SV))]),
        "data_properties": len([p for p in props if str(raw.value(p, RDFS.range)).startswith(str(XSD))]),
        "individuals": len(individuals), "typed_literals": lit_counts,
        "ill_typed_literals": ill_typed, "untyped_terms": untyped,
        "closure": len(closed), "inferred": len(inferred),
        "inferred_application": len(app), "inferred_housekeeping": len(inferred) - len(app),
    }

    # ---- domain/range audit ---------------------------------------------
    def sv_types(g, x):
        return {o for o in g.objects(x, RDF.type) if str(o).startswith(str(SV))}

    def subclosure(classes_):
        res, changed = set(classes_), True
        while changed:
            changed = False
            for c in list(res):
                for sup in raw.objects(c, RDFS.subClassOf):
                    if sup not in res:
                        res.add(sup)
                        changed = True
        return res

    unexpected = []
    for x in individuals:
        if sv_types(closed, x) != subclosure(sv_types(raw, x)):
            unexpected.append(str(x))
    out["audit_unexpected_types"] = unexpected

    # ---- queries (inference off / on) -----------------------------------
    queries = read_queries()
    out["queries"] = {}
    for qid, q in queries.items():
        out["queries"][qid] = {"title": q["title"], "text": q["text"],
                               "off": run(raw, q["text"]), "on": run(closed, q["text"])}
    q9 = queries["Q9"]["text"].replace("sv:CreativeWork", "sv:PeriodRecord")
    out["periodrecord_off_on"] = [len(run(raw, q9)["rows"]), len(run(closed, q9)["rows"])]

    # ---- mutation tests: do the checks really catch mistakes? -------------
    def count(g, qid):
        r = run(g, queries[qid]["text"])
        return r["ask"] if "ask" in r else len(r["rows"])

    muts = {}
    g = load(); a = EX.Availability_IN_Riverline
    g.remove((a, SV.endDate, None)); g.add((a, SV.endDate, Literal("2027-02-28", datatype=XSD.date)))
    muts["M1"] = count(g, "Q10")
    g = load(); a = EX.Availability_SG_LastSignal
    g.remove((a, SV.availabilityStatus, None)); g.add((a, SV.availabilityStatus, EX.Active))
    muts["M2"] = count(g, "Q11")
    g = load(); g.add((EX.Riverline, SV.startDate, Literal("2026-01-01", datatype=XSD.date)))
    muts["M3"] = count(rdfs_closure(g), "Q12")
    g = load(); g.add((EX.Licence_IN_Riverline, SV.territory, EX.DevRao))
    muts["M4"] = (EX.DevRao, RDF.type, SV.Territory) in rdfs_closure(g)
    out["mutations"] = muts

    # ---- print ------------------------------------------------------------
    c = out["counts"]
    print("TRIPLES  explicit=%d (vocabulary %d + data %d) | RDFS closure=%d | inferred=%d "
          "(application-level %d, housekeeping %d)" % (c["explicit"], c["vocabulary"], c["data"],
          c["closure"], c["inferred"], c["inferred_application"], c["inferred_housekeeping"]))
    print("TERMS    classes=%d properties=%d (object %d, data %d) individuals=%d"
          % (c["classes"], c["properties"], c["object_properties"], c["data_properties"], c["individuals"]))
    print("LITERALS", c["typed_literals"], "ill-typed:", c["ill_typed_literals"], "untyped terms:", c["untyped_terms"])
    print("AUDIT    unexpected inferred types:", unexpected)
    for qid, r in out["queries"].items():
        print("\n%s  %s" % (qid, r["title"]))
        for mode in ("off", "on"):
            d = r[mode]
            if "ask" in d:
                print("  inference %-3s -> %s" % (mode, d["ask"]))
            else:
                print("  inference %-3s -> %d rows" % (mode, len(d["rows"])))
                if mode == "on":
                    for row in d["rows"]:
                        print("      ", " | ".join(row))
    print("\nPeriodRecord instances, inference off/on:", out["periodrecord_off_on"])
    print("MUTATION TESTS (deliberate errors in in-memory copies; the file is never changed)")
    print("  M1 availability ends after its licence      -> Q10 rows:", muts["M1"])
    print("  M2 expired record marked Active             -> Q11 rows:", muts["M2"])
    print("  M3 start date put on a film                 -> Q12 ASK :", muts["M3"])
    print("  M4 licence territory points at a person     -> person inferred as Territory (silent):", muts["M4"])

    if "--json" in sys.argv:
        path = Path(sys.argv[sys.argv.index("--json") + 1])
        path.write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
