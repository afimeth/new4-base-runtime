# Measured evidence

Generated from the evaluation JSON. Do not edit this projection by hand.

Run: 2026-10-07T08:16:21.290644+00:00. Environment: Windows, Python 3.14.7, SQLite 3.50.4.

Result: **34/34 fixture scenarios passed**. This is not a production task-success rate.

Source commit at run: `45467204e4edefa754aee613aa6692e3048aee95`. Exact tested source bytes are bound by the JSON source hash map.

| Scenario | Outcome | Elapsed ms |
|---|---|---:|
| test_approval_denial_and_positive_control | PASS | 101.217 |
| test_artifact_tamper_detected_on_replay | PASS | 80.389 |
| test_cancellation_survives_restart | PASS | 86.287 |
| test_capsule_topology_dictionary_and_projection | PASS | 52.564 |
| test_case_isolation_and_source_spelling | PASS | 106.287 |
| test_cloud_feed_destination_boundary | PASS | 69.155 |
| test_cloud_spider_then_case_hydration | PASS | 133.846 |
| test_concurrent_workers_commit_one_artifact | PASS | 430.537 |
| test_context_prefix_budget_and_memory_supersession | PASS | 101.888 |
| test_cpu_reranker_feedback_is_case_query_and_source_scoped | PASS | 136.455 |
| test_duplicate_request_conflict_and_replay | PASS | 79.274 |
| test_end_to_end_source_bound_artifact | PASS | 82.482 |
| test_http_origin_token_boundary_and_ui_action | PASS | 665.831 |
| test_hydrate_no_network_and_explicit_frame | PASS | 71.254 |
| test_invalid_inputs_and_duplicate_sources | PASS | 48.567 |
| test_local_feed_then_hydration | PASS | 106.609 |
| test_no_context_abstains | PASS | 73.543 |
| test_payload_and_tool_tamper_denied | PASS | 79.412 |
| test_process_kill_after_commit_replays_without_duplicate | PASS | 351.619 |
| test_process_kill_before_commit_rolls_back | PASS | 267.779 |
| test_project_map_approval_hold_ready_and_source_change | PASS | 147.094 |
| test_project_map_done_counts_and_receipt_links | PASS | 83.956 |
| test_python_ast_map_does_not_execute_source | PASS | 52.679 |
| test_qos_token_bucket_burst_and_refill | PASS | 43.489 |
| test_real_go_math_frame_and_decimal_precision | PASS | 95.292 |
| test_real_go_topology_frame_from_explicit_links | PASS | 97.438 |
| test_receipt_tamper_detected | PASS | 79.080 |
| test_scoped_dictionary_routes_and_revision_revokes_approval | PASS | 83.530 |
| test_source_change_invalidates_old_approval | PASS | 114.617 |
| test_stateless_worker_has_no_cross_call_context | PASS | 81.855 |
| test_untrusted_source_is_not_authority | PASS | 74.836 |
| test_utf8_unicode_roundtrip_without_normalization | PASS | 87.564 |
| test_view_reads_one_snapshot_during_concurrent_write | PASS | 65.824 |
| test_worker_capacity_backpressure | PASS | 60.781 |

Times include fixture setup, execution and cleanup; subprocess and HTTP scenarios are not retrieval latency benchmarks.

Provider calls: 0. Provider cost: $0. Semantic accuracy: UNKNOWN. Human usability: UNKNOWN. Independent review: UNKNOWN.

Real OS-process termination was exercised. Power failure and distributed effects were not. Receipt hash checking does not provide a signature or external anchor.

Report receipt hash: `6550da1bab592d07f03ee361807d89338c59d6643b5bc867b72072a82151d3d2`.
