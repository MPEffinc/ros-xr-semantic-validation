| Case | Goal | B0_stock | B1_existing_primitives |
|---|---|---|---|
| C1_normal | PG1 | PASS 5 | PASS 5 |
| C1_normal | PG2 | PASS 5 | PASS 5 |
| C2_release_executing | PG3-cont | PASS 5 | FAIL 5 |
| C2_release_executing | PG3-stop | FAIL 5 | PASS 5 |
| C2_release_executing | PG4 | FAIL 5 | PASS 5 |
| C3_ttl_expiry_executing | PG3-cont | PASS 5 | FAIL 5 |
| C3_ttl_expiry_executing | PG3-stop | FAIL 5 | PASS 5 |
| C3_ttl_expiry_executing | PG4 | FAIL 5 | PASS 5 |
| C4_disconnect_reconnect | PG2-reconnect | PASS 5 | N/A 5 |
| C4_disconnect_reconnect | PG3-cont | PASS 5 | FAIL 5 |
| C4_disconnect_reconnect | PG3-stop | FAIL 5 | PASS 5 |
| C5F_handoff_back_to_back | PG2 | FAIL 25 | PASS 25 |
| C5F_handoff_back_to_back | PG6 | PASS 25 | PASS 25 |
| C5_handoff | PG2 | FAIL 5 | PASS 5 |
| C5_handoff | PG6 | PASS 5 | PASS 5 |
| C6_catalog_change_during_lease | PG1 | PASS 5 | PASS 5 |
| C6_catalog_change_during_lease | PG5 | FAIL 5 | PASS 5 |
| C7_teleop_stream_after_release | PG4 | FAIL 5 | PASS 5 |
