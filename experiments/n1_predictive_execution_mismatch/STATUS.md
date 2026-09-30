# Status

| Step | Status | Commit | Result |
|---|---|---|---|
| 1 Problem definition | DONE | `dab2b4db0df06d559a2caac8b5520e7fc04ed93e` | N1 structure and H0/H1 fixed before any run |
| 2 Simulation setup + protocol freeze | DONE | `9b5dde8e8f5345802f0ffd7ed78e514be6986bda` | UR5 Gazebo+ros2_control+MoveIt Servo up; mechanisms A/C/D/E/F verified in smoke; 10 conditions × 5 seeds, predictors P0/PA/PB/PC/PD, B offline; rules frozen |
| 3 Formal campaign + naive mismatch | DONE | `371bd4d32e9f97a59b51578ade697db8edab309c` | 50/50 valid; P0 misleads 6.6–10 s per 10 s trial, max error up to 31 cm (D) |
| 4 Existing combinations | DONE | `21a2ec5164ac3d0398c41a56cdc399aa13f3ce77` | PD 0.00 s misleading in all conditions at B0 (h 0.25/0.5); residual cells: PD E/B2 0.14 s, PC nominal 0.14–0.18 s; B1 → freeze 100 % |
| 5 Ablations | DONE | (this commit) | residuals: R1 in-flight input (fixed by PD), R2 silent smoothing (E/B2 0.14 s; final-command velocity removes it in PC), R3 collision scaling (flag+bound), R4 stale feedback (freeze vs mislead); no structural failure |
