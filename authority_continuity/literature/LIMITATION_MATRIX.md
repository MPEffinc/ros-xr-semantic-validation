# Limitation Matrix

Column "Author-stated limitation" contains **only** what the authors wrote (quotes / section / page).
Our observations are in a separate column and labeled. Resolution status is as of 2026-09-29.

| Source | Author-stated limitation / future work (verbatim or exact paraphrase, location) | Resolved by later work? | Our observation (not an author claim) | Residual question relevant here |
|---|---|---|---|---|
| P1 HORUS 2025 | No Limitations section. Sec. V p.7: future work on "Heterogeneous Robot Teams", "Advanced Control and Collaboration: Implementing more complex trajectory-planning tools, multi-operator functionality, and AI copilot systems", "3D Mapping". | Multi-operator functionality: addressed by the same authors in P2 (2026) and `horus_ros2` leases. | ROS 1 system; security delegated to Tailscale VPN. (AUTHOR text p.3) | none stated by authors |
| P2 Multi-op HORUS 2026 | No Limitations section. Sec. V-A p.6: headset floor-height calibration issue. Sec. IV p.4: study "simulation-based". Sec. VI p.8: shared and private modes "complementary". | Not applicable; no follow-up citing P2 found. | HYPOTHESIS: lease semantics after release/expiry/disconnect for already-dispatched goals are unspecified in the paper; implementation behavior: see audit F1–F8 (SOURCE_CONFIRMED). | Whether lease end must stop or may continue accepted work is **undefined by the authors** — not an author-stated limitation. |
| HORUS code docs (`horus_ros2`) | `README.md:292` roadmap "In progress": "Harden lease telemetry/observability, tune TTL policies, and extend regression coverage for repeated join/rejoin contention scenarios." `bridge_config.yaml:28-30` "# Security (for future implementation)" `enable_authentication: false`, `enable_encryption: false`. | No (HEAD unchanged). | Authentication is explicitly deferred by the maintainers (doc text), so unauthenticated clients are a *known, acknowledged* gap, not a discovery. | — |
| P3 SROS2 enclaves / DDS-Security / ACP | 182 "Future Work" L114 (tooling for contexts/enclaves); 182 Concerns L243-294 (multiple namespaces per context, node-vs-participant permission mismatch, composition, containers); 181 L326-331 permissions "staticky provisioned", remapping "at least at design time". | sros2 docs now document CRLs (linked before start); runtime reload NOT_VERIFIED. | Identity granularity = participant ⇒ one bridge = one principal (SOURCE_CONFIRMED from doc). | Per-operator identity behind a bridge is out of SROS2's model by design. |
| P4 ROS 2 Actions | Design doc states no limitation on ownership/disconnect; it simply defines none. | — | SOURCE_CONFIRMED: no goal ownership; no auto-cancel on client death (rcl/rclcpp Jazzy). | Lease-to-goal linkage must be built by the application. |
| P5 Xia et al. ICRA 2025 | No Limitations section. Sec. IV-A-2 p.3: enclave expiry cannot be updated after distribution; updating SROS 2 files "requires restarting nodes". Sec. VI mitigations: hide internal APIs, bind enclaves to nodes, message-level authentication. | Citing papers (abstracts) do not resolve runtime revocation. | Their "no per-message origin authentication" finding applies generically to a shared bridge publisher. | — |
| P6 ROSec | NOT_VERIFIED (closed access). | — | Out of scope (memory isolation). | — |
| P7 Salimi et al. JSA 2025 | Preprint Sec. V pp.7-8: scalability of ABAC; comparison with SROS2 RBAC; combine with trust management. Sec. IV p.7: "unintended messages published on the fabric". Sec. III-1 p.4 requirement: access "can be revoked at any time" (no mechanism presented). | NGAC (DCAS 2026) addresses latency only (abstract). | HYPOTHESIS: an exclusive lock + per-message authorization would, if extended with revocation, cover *future* commands; in-flight tasks untreated in the preprint. | In-flight handling on revocation is not addressed (observation). |
| P8 MoveIt Servo | Tutorial documents collision/singularity scaling (L40-41); no stated limitation about multi-operator use. | — | SOURCE_CONFIRMED: timeout 0.1 s halts *streaming* commands when they stop; no sender identity. | Timeout only helps if the stream actually stops at the robot. |
| Zong et al. SOSE 2019 | p.373: "expanding the coverage of the access control method to cover more functionality and different types of robots." | — | Revocation stops "further accesses" only (p.372). | In-flight work after revocation untreated (observation). |

## Cross-cut summary

1. **No author** of P1/P2/P5/P6/P7 states a limitation about authority transfer versus already
   accepted or executing robot work. Any such claim is therefore *ours* (HYPOTHESIS / SOURCE_CONFIRMED
   code behavior), not a documented open problem.
2. The HORUS maintainers explicitly defer authentication ("for future implementation") — this makes
   unauthenticated-client findings acknowledged implementation status, not a research gap.
3. General mechanisms exist for each fragment: per-future-request revocation (Zong; P7 acquire/release),
   participant authentication (P3), goal-level cancel by UUID (P4), stream timeouts (P8, ros2_control).
   What no source found combines is the *policy* "lease end ⇒ terminate or keep specific accepted goals"
   — whether that combination is a method gap or an implementation gap is decided in PHASE 5–7.
4. Archived internal prior work (`../../Deprecated/AUTHORIZATION_CONTINUITY_RESULTS.md` §G) already
   listed most of these collisions in August 2026 (PRIOR_INTERNAL).
