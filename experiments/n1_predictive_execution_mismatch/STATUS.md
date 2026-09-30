# Status

| Step | Status | Commit | Result |
|---|---|---|---|
| 1 Problem definition | DONE | `dab2b4db0df06d559a2caac8b5520e7fc04ed93e` | N1 structure and H0/H1 fixed before any run |
| 2 Simulation setup + protocol freeze | DONE | `9b5dde8e8f5345802f0ffd7ed78e514be6986bda` | UR5 Gazebo+ros2_control+MoveIt Servo up; mechanisms A/C/D/E/F verified in smoke; 10 conditions × 5 seeds, predictors P0/PA/PB/PC/PD, B offline; rules frozen |
| 3 Formal campaign + naive mismatch | DONE | (this commit) | 50/50 valid; P0 misleads 6.6–10 s per 10 s trial, max error up to 31 cm (D) |
