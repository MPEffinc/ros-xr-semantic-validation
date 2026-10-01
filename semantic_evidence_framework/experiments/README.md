# Experiments

- Each pilot gets `<id>/PROTOCOL.md`. The protocol is written and committed **before** any outcome is
  observed. It declares:
  - the protected condition and the allowed transitions;
  - the oracle;
  - the cause and the injection point;
  - the attacker or trust boundary;
  - the comparison defenses;
  - the normal controls;
  - the trial count and runtime estimate;
  - the expand/exclude rules.
- Synthetic inputs test ROS-side consumption only.
- Raw output goes to `../results/raw/<id>/`, which is ignored. Its location, run conditions and sha256
  are recorded in `../results/<id>_MANIFEST.md`.
