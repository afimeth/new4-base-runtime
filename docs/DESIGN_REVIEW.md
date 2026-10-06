# Design review: a small system with explicit scaling boundaries

Reference: [liquidslr/system-design-notes](https://github.com/liquidslr/system-design-notes), inspected at commit `9d8388721e7231442763ad37398b8d82224aa68f`. Its design framework, rate-limiter and crawler notes were read as review prompts. The repository describes notes on Alex Xu's books, not independently validated runtime results. GitHub reported no license metadata at inspection; no upstream text, diagrams or code are redistributed here.

| Review question | New4 Base decision | Implemented evidence | Remaining boundary |
|---|---|---|---|
| What is the initial scope? | One local operator, named cases, bounded on-demand work | Runtime/HMI and room contract | No millions-of-users claim |
| Where is durable state? | One SQLite substrate; artifact and state share a transaction | Two real process-kill scenarios | No separate remote effect sink |
| Where is request admission? | Loopback gateway, token/origin guard, local token bucket | HTTP boundary and burst/refill cases | No distributed rate limit or DoS proof |
| How do workers avoid overload? | Four process slots; explicit retry signal; three-second runtime timeout | Worker capacity denial/positive control | Same process only; no durable distributed queue |
| How does crawler traversal work? | Explicit seed, small FIFO frontier, same-origin public reads, robots and byte/page budgets | Feed fixture and optional live source capture | Frontier is in-memory per invocation, not resumable distributed crawl |
| What gets cached? | Only locally built worker binary, keyed by source bytes | Worker build adapter | Retrieval cache remains a hypothesis |
| How is search represented? | Exact source spans, scoped definitions, CPU BM25 and explicit feedback | Dictionary/ranker/capsule cases | No embeddings or semantic calibration |
| What crosses a service boundary? | Typed JSON proposal request/response | Python-to-Go integration cases | Logical process boundary, not container isolation |
| How are views kept consistent? | UI, graph, dictionary and work folder derive from the case substrate | Capsule closure and source binding | No distributed replicas or CRDT claims |

This mapping is the author's engineering assessment, not an endorsement by the reference author. The runtime does not add a CDN, sharding, Redis or Kubernetes simply because a larger-system example uses them. Such changes require a measured workload and a new effect/storage contract.
