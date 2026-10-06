# Measured evidence

Generated from the evaluation JSON. Do not edit this projection by hand.

Run: 2026-10-06T21:14:17.885497+00:00. Environment: Windows, Python 3.14.7, SQLite 3.50.4.

Result: **32/32 fixture scenarios passed**. This is not a production task-success rate.

Source commit at run: `aa293d5867fdd47eb31ea72045dcf480eafe3e2f`. Exact tested source bytes are bound by the JSON source hash map.

| Scenario | Outcome | Elapsed ms |
|---|---|---:|
| test_approval_denial_and_positive_control | PASS | 98.958 |
| test_artifact_tamper_detected_on_replay | PASS | 121.237 |
| test_cancellation_survives_restart | PASS | 154.907 |
| test_capsule_topology_dictionary_and_projection | PASS | 67.339 |
| test_case_isolation_and_source_spelling | PASS | 162.606 |
| test_cloud_feed_destination_boundary | PASS | 65.610 |
| test_cloud_spider_then_case_hydration | PASS | 220.580 |
| test_concurrent_workers_commit_one_artifact | PASS | 451.149 |
| test_context_prefix_budget_and_memory_supersession | PASS | 110.061 |
| test_cpu_reranker_feedback_is_case_query_and_source_scoped | PASS | 196.560 |
| test_duplicate_request_conflict_and_replay | PASS | 95.882 |
| test_end_to_end_source_bound_artifact | PASS | 94.750 |
| test_http_origin_token_boundary_and_ui_action | PASS | 691.460 |
| test_hydrate_no_network_and_explicit_frame | PASS | 88.005 |
| test_invalid_inputs_and_duplicate_sources | PASS | 55.054 |
| test_local_feed_then_hydration | PASS | 91.260 |
| test_no_context_abstains | PASS | 142.270 |
| test_payload_and_tool_tamper_denied | PASS | 117.452 |
| test_process_kill_after_commit_replays_without_duplicate | PASS | 335.251 |
| test_process_kill_before_commit_rolls_back | PASS | 325.823 |
| test_python_ast_map_does_not_execute_source | PASS | 75.708 |
| test_qos_token_bucket_burst_and_refill | PASS | 56.779 |
| test_real_go_math_frame_and_decimal_precision | PASS | 812.249 |
| test_real_go_topology_frame_from_explicit_links | PASS | 195.152 |
| test_receipt_tamper_detected | PASS | 153.333 |
| test_scoped_dictionary_routes_and_revision_revokes_approval | PASS | 120.515 |
| test_source_change_invalidates_old_approval | PASS | 161.936 |
| test_stateless_worker_has_no_cross_call_context | PASS | 110.473 |
| test_untrusted_source_is_not_authority | PASS | 139.385 |
| test_utf8_unicode_roundtrip_without_normalization | PASS | 127.803 |
| test_view_reads_one_snapshot_during_concurrent_write | PASS | 79.869 |
| test_worker_capacity_backpressure | PASS | 86.439 |

Times include fixture setup, execution and cleanup; subprocess and HTTP scenarios are not retrieval latency benchmarks.

Provider calls: 0. Provider cost: $0. Semantic accuracy: UNKNOWN. Human usability: UNKNOWN. Independent review: UNKNOWN.

Real OS-process termination was exercised. Power failure and distributed effects were not. Receipt hash checking does not provide a signature or external anchor.

Report receipt hash: `044686a78e34d6395fc04480e2fc817b7478b76cbe09463dd5c4fd91819b83f2`.
