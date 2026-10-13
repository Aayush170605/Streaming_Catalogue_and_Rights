# Streaming Catalogue and Rights (Case 2C)

CSE 4007 Semantic Web - Aayush Sharda (Reg. No. 235890136)

An RDFS vocabulary and a 311-triple knowledge graph, in Turtle, for a fictional streaming
service. It represents films, a series with episodes, contributors and their roles, genres,
languages, regional licences and availability periods - as linked resources, not plain text.
Creative works are kept separate from licences and availability events.

## Files

| File | What it is |
|---|---|
| `streaming_catalogue.ttl` | The submission graph: Part A = RDFS vocabulary (`sv:`), Part B = sample data (`ex:`) |
| `queries.rq` | 12 SPARQL 1.1 queries: a size count, 8 competency questions (Q9 doubles as the inference demo) and 3 validation checks |
| `run_checks.py` | Reproduces every count and query result quoted in the report (Python, `rdflib` + `owlrl`) |
| `make_figures.py` | Draws the vocabulary diagram and the two subgraphs from the Turtle file (needs Graphviz) |
| `figures/` | The generated diagrams used in the report |
| Report (`.docx`) | Modelling decisions, evidence, limitations, full Turtle and queries as appendices |

## Namespaces

| Prefix | IRI | Used for |
|---|---|---|
| `sv:` | `https://example.org/streaming/vocab#` | classes and properties (the vocabulary) |
| `ex:` | `https://example.org/streaming/id/` | individuals (the catalogue data) |

`example.org` is reserved for documentation and examples (RFC 2606), so these IRIs cannot clash
with a real site.

## The model in one picture

```
CreativeWork (Film | Series | Episode)  <-- LanguageVersion  <-- Licence  <-- AvailabilityEvent
      |                                     (language,            (versions +      (period actually
      +-- Contribution (person + role)       runtime)              territory +      offered, status,
      +-- Genre                                                    rights period)   as-of date)
```

* 15 classes, 16 properties (11 object, 5 data), 44 individuals.
* A title carries only genre and credits. Rights hang off the versions, never off the title.
* `Licence` and `AvailabilityEvent` are both `sv:PeriodRecord`, so one `startDate`/`endDate` pair serves both.
* Dates are `xsd:date`, runtimes `xsd:duration`, episode numbers `xsd:integer`.
* Status (`ex:Active` / `ex:Expired`) is a snapshot with an `asOfDate`; the dates remain the source of truth.

## Run the checks

```
pip install rdflib owlrl
python run_checks.py
```

Headline numbers: 311 explicit triples (130 vocabulary + 181 data), RDFS closure 618, Q9
returns 0 rows without inference and 6 with it, and the three validation queries (Q10, Q11,
Q12) report no violations. The script also breaks the data on purpose in
memory (M1-M4) to show that the checks catch real errors; the file itself is never changed.

## Load it into GraphDB

1. Workbench -> Setup -> Repositories -> Create new repository, ruleset **RDFS (optimized)**.
2. Import -> Upload RDF files -> `streaming_catalogue.ttl`, into the default graph.
3. SPARQL tab: paste one query from `queries.rq` at a time. Switch "Include inferred data in
   results" off and on to see Q9 go from 0 to 6 rows.
4. Explore -> Visual graph: start from `https://example.org/streaming/id/Riverline`.

The triple count with inference on will differ from the 618 reported by `owlrl`, because
different RDFS implementations materialise different housekeeping triples. The explicit count
(311) is the same everywhere. Menu names may differ slightly between GraphDB versions.

Protégé is an OWL editor. It can open the file for browsing, but because the vocabulary is plain
RDFS (`rdf:Property`, not `owl:ObjectProperty`), properties may be listed differently there.

## Typical changes (for the demonstration)

* **New language version**: add an `sv:LanguageVersion` (copy `ex:Riverline_HI`), then list it
  under a licence with `sv:licensedVersion`.
* **New territory**: add an `sv:Territory`, then a licence and an availability event for it.
* **Extend a licence**: change `sv:endDate`; re-run Q10 to confirm the availability still fits.
* **Change the reference date**: edit the date in Q7 and the `sv:asOfDate` values; re-run Q11.
* **Add a credit**: add an `sv:Contribution` with `sv:contributionWork`, `sv:contributor`, `sv:role`.
