# A reviewer walkthrough

1. Run `python app.py evaluate`. Read the case list and source hashes in the JSON report. Failing cases produce a nonzero exit code.
2. Run `python app.py serve` and open its printed loopback URL.
3. Create a request with `Find release reviewer rollback`. Choose Find my context. Read the extracted policy and its source hash.
4. Approve the displayed draft, then create the local artifact. Watch the task become DONE and the receipt timeline grow.
5. Stop and restart the server. The task and artifact remain in `.state/runtime.sqlite`.
6. Run `python app.py verify`. Compare the chain head and event count with the UI. They are views of the same records.
7. Read the two process-kill scenarios in `tests/test_workflow.py`. One interrupts a transaction; the other loses the acknowledgment after commit. The retry behavior differs by the committed state.

The demo case includes synthetic documents; other cases use your imported notes or feeds. Add a note, define a scoped term, inspect onion/ranking details and export a capsule. Changed-source and adversarial scenarios are exercised through the runtime test adapter. No hidden external effect occurs.

Review questions: Where does the effect happen? What exactly was approved? How is stale context handled? What changes if the sink moves to a remote service? Which hypothesis would you test first with real users?
