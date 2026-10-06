# Computation, representation and measurable bounds

Reference: Boaz Barak's [Introduction to Theoretical Computer Science](https://introtcs.org/public/). The index and selected representation, code/data and running-time chapters were inspected. This is an original engineering mapping, not reproduced textbook material, course completion or formal verification.

## Representation before interpretation

The [representation chapter](https://introtcs.org/public/lec_02_representation.html) separates the requested input/output function from the program implementing it. Here, a tool contract maps a typed request to `Success(result)` or `Hold(error_code)`. The onion parser retains exact source spelling and Unicode code-point spans; lookup forms are separate. A representation or shared word does not establish a shared meaning.

For money addition, inputs are bounded decimal amounts with an explicit USD/EUR currency, and the result is integer minor units. That narrow specification permits exact decimal addition; it does not specify exchange rates, financial policy or arbitrary real-number arithmetic.

## Code and data at the boundary

The [code/data chapter](https://introtcs.org/public/lec_04_code_and_data.html) supplies a useful review question: which representations are interpreted as programs? In this runtime, source text, graph labels, memory notes and model-shaped proposals remain data. Only the registered Go operations and Python control methods execute. The AST map parses Python source without executing it. Logical tool admission is still distinct from an OS sandbox.

## Running-time model versus stopwatch result

The [running-time chapter](https://introtcs.org/public/lec_11_running_time.html) motivates stating the input size and computational model. The following bounds are an inspection of this repository's implementation, not a benchmark claim:

| Mechanism | Input model | Work / limit |
|---|---|---|
| Onion token scan | C Unicode code points | Linear scan; utterance capped at 2,000 code points |
| CPU ranker | C candidate text size, D documents, Q query terms | Token counting plus D×Q scoring and D log D sorting; at most 32 candidates |
| Directed route | V nodes, E recorded edges, h returned hops | BFS traversal plus neighbor sorting and this implementation's O(h²) path reconstruction; V≤1,000, E≤4,000 |
| Context allocation | Selected serialized source bytes | Explicit UTF-8 byte budget; not a model token estimate |
| Gateway / workers | Admitted local requests | Token-bucket admission, four process slots, bounded payloads and timeout |

A timeout is an operational bound, not a proof of algorithmic efficiency. Fixture elapsed times include setup/cleanup and do not establish a production SLO. Tests and hash-linked receipts are evidence for exercised cases; they are not mathematical proofs of every possible input or independent semantic validation.

The source page declares CC BY-NC-ND 4.0. This repository links and attributes the textbook; it does not bundle its chapters, diagrams, code or a modified edition.
