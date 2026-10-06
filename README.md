# New4 Base Runtime

**A small local-first work environment: one conversation surface, many workflows, case-scoped context, and stateless workers.** A zookeeper routes English requests through an onion parser, CPU search/reranking, exact math or recorded graph routes. Local notes and selected cloud/corpus feeds hydrate the same work capsule. Review a result before creating a durable local artifact.

By **Arif Anil Dondurmaci**. AI-assisted implementation; this demonstrates bounded behavior, not unaided coding proficiency or production adoption. Repository text is English and UTF-8. Published examples are synthetic. Locally imported notes/corpus data stay in the ignored `.state/` folder. No private transcripts, credentials, customer data or infrastructure inventory are published.

## Run

Python 3.11+ and Go 1.22+, both standard libraries. No Python/Go packages, API keys, model downloads or paid services. `serve` builds the Go worker from this repository when needed.

```sh
python app.py evaluate
python app.py serve
go test ./...
```

Open the loopback URL printed by `serve`. In case `demo`, enter **Find release reviewer rollback**, choose **Take me there**, then **Find my context**. Review, choose **Approve this result**, then **Create local artifact**. Restart with the same database to continue. `Run.ps1` / `run.sh` start the same app. Its database `.state/runtime.sqlite` is ignored by Git.

**Add a note** accepts actual local text. `[[source-id]]` records a directed relation. **Define a word** routes a personal term through its stated case-scoped meaning. Source or definition changes require re-preparation and reapproval. **Your capsule** exposes dictionary, graph, source-bound word index, worker/provider agents and engineering/QA lenses. Export the work folder as versioned UTF-8 JSON.

Try **calculate 12.50 + 30 EUR** for exact integer minor-unit addition. Try **route from alpha to beta** after adding `alpha` with `[[beta]]` and a source `beta`. No recorded path produces an abstention, not an invented link.

## On-demand dual feeding

```sh
python app.py feed-local --folder ./notes --case project-a
python app.py feed-cloud --url https://docs.python.org/3/library/json.html --case research-a
python app.py feed-alexandria --url http://127.0.0.1:8080 --query zookeeper --case corpus-a
python app.py define --case project-a --term launchgate --meaning "release checklist"
python app.py capsule --case project-a
python app.py scan
```

Set the local corpus URL to your own compatible service; `8080` is an example. The adapter consumes `/api/fastwikitaxi` with a bounded query. Local folders accept selected UTF-8 `.txt`/`.md` files. Cloud crawl respects robots, same-origin boundaries, budgets and sensitive-content holds, retaining up to 120 words/page. No background crawl or private GitHub credentials.

## Worker, zone and frame

| Role | Zone | Implemented work |
|---|---|---|
| Python zookeeper | Durable control and context | SQLite, import, hydrate, approval, feedback, capsule |
| Stateless Go worker | Language, search, math, topology | Unicode parser, English rules, CPU BM25, feedback, exact sums, BFS |
| Provider agents | Tool adapters | Registered local Python and Go; not cloud models |
| LLM room | Future proposal-only boundary | Architecture contract; no model adapter connected |
| Engineering / QA lenses | Architecture and evidence | Shared case projections and actual checks; not independent semantic reviewers |

The semantic index combines lexical postings and explicit definitions, without embeddings. BM25, title boost and clipped feedback are explainable retrieval scores, never semantic confidence. Feedback applies only to the same case, query and source bytes. Workers start, process one bounded request and exit.

`contracts/room.json` records Room, Board, Work, `n1 auth`, `0auth`, `ownerauth`, context/LLM quality, utility and QoS. Sources/workers cannot approve effects. Local-session approval is not OAuth or verified identity. Realmdoor denotes this package's loopback gateway; micro OS denotes application-level coordination, not a kernel or distro.

## Linux / WSL

With Python and Go installed, run the same commands. A Windows Go host can cross-build the Linux amd64 worker with `python scripts/build_linux.py`; then run `python3 app.py evaluate` inside Linux/WSL over the checkout. Cross-compilation is not runtime acceptance. [WSL evidence](evidence/wsl-eval.json) records an actual dated run. This package does not install/configure a distro.

For an explicitly scripted demo (including a simulated local operator approval):

```sh
python app.py demo
python app.py verify
python -m unittest discover -s tests -v
```

Evaluation exits nonzero on failure. Its JSON includes individual scenario outcomes, elapsed wall time, Python/SQLite/OS versions, exact source hashes, a receipt hash, and explicit unmeasured fields. [Local measurement](evidence/local-eval.json) is a dated run; re-run on your machine. GitHub Actions runs the same suite and uploads a fresh report.
Go's [measurement](evidence/go-eval.json) records separately executed parser, decimal, graph, ranking and tool-denial tests. CI covers Python 3.11/3.14 on Windows/Linux with Go 1.22.

## What you can inspect

| View | Question it answers | Artifact |
|---|---|---|
| Product | Can I complete a task and understand the next step? | Local HMI and [walkthrough](docs/WALKTHROUGH.md) |
| PoW — Proof of Work | What actually executes, and what was exercised? | Runtime, [evaluation](evidence/local-eval.json), tests, CI |
| QoW — Quality of Work | Which failure and success cases pass? What remains unknown? | Per-case results and [limitations](docs/LIMITATIONS.md) |
| GoW — Governance of Work | What authorizes an effect, and how is its history retained? | Payload-bound approval, policy, receipt chain |
| Design | What are the invariants and crash boundaries? | [Design contract](contracts/design.json), [architecture](docs/ARCHITECTURE.md) |
| Research | Which ideas remain hypotheses? | [Hypotheses](contracts/hypotheses.json) |
| Machine | Can a consumer navigate the same workflow? | `/api/state`, schemas, CLI JSON, [claims](contracts/claims.json) |

PoW/QoW/GoW are repository-local working definitions. They are not an industry standard, certification, or an aggregate self-awarded quality score. The one workflow has several projections; projections do not create additional authorities.

## Measured behavior and scope

The suite exercises real SQLite, Go worker requests, abrupt process termination before/after commit, six concurrent workers, replay, source/definition revisions, cancellation, mutation detection, Unicode, case isolation, local/cloud hydration, dictionary routing, feedback ranking, capsule closure and HTTP boundaries. **No live LLM, desktop automation, email delivery, model accuracy benchmark or external-user usability study is claimed.**

The local effect is an artifact row in the **same SQLite transaction** as the terminal state and receipt. This deliberately closes the local effect/state gap. Extending it to email or a remote API would require a different effect contract; this result does not establish distributed exactly-once execution.

## Role relevance

[Context and memory](docs/CONTEXT_MEMORY.md) separates a budgeted working slice from source-linked persistent notes, with an on-demand maintenance loop and a Python AST code map.

[Engineering map](docs/ENGINEERING_MAP.md) connects application work, foundations, agent-assisted engineering and product judgment. [Reference ledger](research/references.json) records what was actually read and how it was used.

[Design review](docs/DESIGN_REVIEW.md) maps the selected system-design reference to implemented mechanisms and open scaling boundaries.

This is a small demonstration of the product/runtime boundary described in Anthropic's [Product Engineer, Computer Use](https://job-boards.greenhouse.io/anthropic/jobs/5238637008) role: end-to-end delivery, agent harness reliability, tool boundaries, instrumentation, and turning a fuzzy task into a reviewable flow. It is not affiliated with Anthropic and does not demonstrate every qualification in that role. In particular, external-user delivery and production-scale experience remain unproven here.

The earlier public [Agent Runtime Recovery Lab](https://github.com/afimeth/agent-runtime-recovery-lab) documents a dispatch uncertainty window. This fresh implementation explores a different, explicitly narrower effect boundary and adds an integrated user flow, source-bound approvals, actual process-kill tests, and machine-readable claims. No code was copied from private repositories.

SQLite's [atomic commit documentation](https://www.sqlite.org/atomiccommit.html) and [WAL documentation](https://www.sqlite.org/wal.html) explain the database mechanisms and their assumptions. Process termination in this lab is not a power-loss or storage-controller test.
