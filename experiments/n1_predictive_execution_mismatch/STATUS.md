# Status

| Step | Status | Commit | Result |
|---|---|---|---|
| 1 Problem definition | DONE | `dab2b4db0df06d559a2caac8b5520e7fc04ed93e` | N1 structure and H0/H1 fixed before any run |
| 2 Simulation setup + protocol freeze | DONE | `9b5dde8e8f5345802f0ffd7ed78e514be6986bda` | UR5 Gazebo+ros2_control+MoveIt Servo up; mechanisms A/C/D/E/F verified in smoke; 10 conditions × 5 seeds, predictors P0/PA/PB/PC/PD, B offline; rules frozen |
| 3 Formal campaign + naive mismatch | DONE | `371bd4d32e9f97a59b51578ade697db8edab309c` | 50/50 valid; P0 misleads 6.6–10 s per 10 s trial, max error up to 31 cm (D) |
| 4 Existing combinations | DONE | (this commit) | PD 0.00 s misleading in all conditions at B0 (h 0.25/0.5); residual cells: PD E/B2 0.14 s, PC nominal 0.14–0.18 s; B1 → freeze 100 % |
