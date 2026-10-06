# Measured evidence

Generated from the evaluation JSON. Do not edit this projection by hand.

Run: 2026-10-06T21:17:47.426179+00:00. Environment: Windows, Python 3.14.7, SQLite 3.50.4.

Result: **32/32 fixture scenarios passed**. This is not a production task-success rate.

Source commit at run: `e121eaa9b515fb2ca13f51d40a1d0abea80d42a6`. Exact tested source bytes are bound by the JSON source hash map.

| Scenario | Outcome | Elapsed ms |
|---|---|---:|
| test_approval_denial_and_positive_control | PASS | 790.248 |
| test_artifact_tamper_detected_on_replay | PASS | 80.047 |
| test_cancellation_survives_restart | PASS | 83.478 |
| test_capsule_topology_dictionary_and_projection | PASS | 53.150 |
| test_case_isolation_and_source_spelling | PASS | 109.446 |
| test_cloud_feed_destination_boundary | PASS | 55.264 |
| test_cloud_spider_then_case_hydration | PASS | 121.486 |
| test_concurrent_workers_commit_one_artifact | PASS | 375.084 |
| test_context_prefix_budget_and_memory_supersession | PASS | 99.806 |
| test_cpu_reranker_feedback_is_case_query_and_source_scoped | PASS | 133.332 |
| test_duplicate_request_conflict_and_replay | PASS | 79.192 |
| test_end_to_end_source_bound_artifact | PASS | 80.423 |
| test_http_origin_token_boundary_and_ui_action | PASS | 669.243 |
| test_hydrate_no_network_and_explicit_frame | PASS | 75.989 |
| test_invalid_inputs_and_duplicate_sources | PASS | 42.573 |
| test_local_feed_then_hydration | PASS | 76.336 |
| test_no_context_abstains | PASS | 69.751 |
| test_payload_and_tool_tamper_denied | PASS | 76.630 |
| test_process_kill_after_commit_replays_without_duplicate | PASS | 255.368 |
| test_process_kill_before_commit_rolls_back | PASS | 267.042 |
| test_python_ast_map_does_not_execute_source | PASS | 48.461 |
| test_qos_token_bucket_burst_and_refill | PASS | 42.010 |
| test_real_go_math_frame_and_decimal_precision | PASS | 99.499 |
| test_real_go_topology_frame_from_explicit_links | PASS | 100.828 |
| test_receipt_tamper_detected | PASS | 82.652 |
| test_scoped_dictionary_routes_and_revision_revokes_approval | PASS | 83.356 |
| test_source_change_invalidates_old_approval | PASS | 108.413 |
| test_stateless_worker_has_no_cross_call_context | PASS | 80.975 |
| test_untrusted_source_is_not_authority | PASS | 75.965 |
| test_utf8_unicode_roundtrip_without_normalization | PASS | 82.568 |
| test_view_reads_one_snapshot_during_concurrent_write | PASS | 66.114 |
| test_worker_capacity_backpressure | PASS | 53.891 |

Times include fixture setup, execution and cleanup; subprocess and HTTP scenarios are not retrieval latency benchmarks.

Provider calls: 0. Provider cost: $0. Semantic accuracy: UNKNOWN. Human usability: UNKNOWN. Independent review: UNKNOWN.

Real OS-process termination was exercised. Power failure and distributed effects were not. Receipt hash checking does not provide a signature or external anchor.

Report receipt hash: `2cd8a68e22f4205a7d2a9e56090ef26d3f6aad221fbee805e5ce91fb0ff23b5f`.
