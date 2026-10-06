# Working context and persistent memory

The supplied architecture essay was used as a design prompt, not as a verified benchmark or redistributed source. Its universal savings/cache-hit claims are not measurements of this runtime.

Implemented here:

- A reproducible proposal-only system prefix with a stable hash across queries.
- A bounded source/memory slice and a separate dynamic query tail. Budgets are UTF-8 bytes, not model tokens.
- Explicit on-demand source-note ADD / UPDATE / NOOP. Updates supersede retained previous revisions; no automatic physical deletion or fact promotion.
- A source-bound Python AST signature map that never executes inspected code. This is Python AST, not Tree-sitter or a multi-language repository map.

```sh
python app.py consolidate --case demo
python app.py context --case demo --query "find release policy"
python app.py map-code --folder ./selected-code
```

The Go CPU ranker supplies lexical relevance. Vector search, MMR, PageRank, model inference, measured prefix caching and automatic asynchronous consolidation are not implemented. Semantic relevance, utility, cache hit rate and token savings remain UNKNOWN. The active slice is reconstructible from persistent records; it is not the persistent substrate itself.
