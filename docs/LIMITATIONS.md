# Limitations

- The planner is lexical overlap and exact text extraction. It is not an LLM or semantic-confidence scorer. A matching word does not establish relevance or truth.
- Behavioral evaluation uses synthetic fixtures. Local/cloud/corpus ingestion observations are separate evidence; no private source content is published.
- The effect is a local artifact stored in the workflow database. No browser/desktop automation, email, web submission, or remote API adapter exists.
- Process-kill tests use actual OS processes. Power failure, disk/controller failure, network filesystems, distributed coordination and production load are unmeasured.
- SQLite write serialization is not a high-throughput distributed architecture. The concurrency fixture uses six local workers.
- The HTTP server binds to loopback. Host, Origin and session token checks address the tested browser boundary. A privileged local program can obtain the session token; local operator labels are not authenticated identity.
- Hash-linked receipts detect tested retained-record mutations. They are not signatures, external anchors, independent validation, or protection against a privileged database rewrite.
- A source can contain harmful or incorrect text. Showing that text for review is intentional; the fixture proves it cannot authorize an effect by itself. It does not prove general prompt-injection resistance in an LLM.
- User research, accessibility audit, external-user delivery, adoption, model/provider performance, independent review and semantic accuracy are UNKNOWN.
- Provider calls and provider cost are zero for this fixture. Engineering time, machine energy, opportunity cost and production ROI are not measured.
- This is an AI-assisted educational implementation under Arif Anil Dondurmaci's direction. It does not prove unaided proficiency, professional tenure or every qualification in a hiring role.
- There is no affiliation, endorsement, acceptance, or employment relationship with Anthropic or OpenAI.
- Case isolation is a context boundary, not multi-user authentication. Privileged local programs can inspect the database and obtain a local session.
- Public destination checks are not an OS network sandbox or proven DNS-rebinding defense. Only explicitly selected trusted public origins are in scope.
- The semantic index combines exact words, spans and scoped definitions. No embeddings or calibrated semantic confidence exist. Retrieval scores are not truth scores.
- Work folders may contain locally imported private content and are excluded from the public repository.
