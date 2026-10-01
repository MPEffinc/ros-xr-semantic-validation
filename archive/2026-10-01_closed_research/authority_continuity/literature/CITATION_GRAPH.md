# Citation Graph (verified edges only)

An edge `X → Y` means *X's reference list contains Y*, confirmed in X's full text (or in the stated
index). Edges not confirmed this way are not drawn. Access date 2026-09-29.

## HORUS line

```text
2025  P1 HORUS (arXiv:2506.02622)
        ▲
        │ ref [9]  (confirmed in 2606.07013v1 full text)
2026  P2 Multi-operator HORUS (arXiv:2606.07013)          ── forward citations: none found
        ▲                                                    (Semantic Scholar: []; OpenAlex: 0)
        │
2026  Baek et al., arXiv:2602.23694 → P1 as ref [23]       (confirmed in 2602.23694v3 PDF; passing mention)
```

P1 forward citations (Semantic Scholar citations endpoint): exactly {P2, 2602.23694}. OpenAlex: 0
(lagging). Google Scholar: HTTP 403 → NOT_VERIFIED. Checked and **not** citing P1: 2605.16432,
2604.03730, 2602.23404 (grep of PDFs).

Relevant backward edges of P2 (numbers as printed): [10] Rule & Forlizzi HRI 2012; [11] Musić & Hirche
2017; [12] Miyauchi et al. IROS 2023; [16] Noohi et al. IROS 2015 (dynamic authority distribution);
[17] Liu et al. EMBC 2015; [18] Lu et al. IJCAS 2017; [19] Fern et al. NASA MOMU 2018. **No ROS/robot
security reference** in P1 or P2.

## ROS security line

```text
2014 Toris et al. (rosauth) ◀── P5 Xia et al. ICRA 2025 [37]
2016 Dieber et al. IROS     ◀── P5 [38]      ◀── P7 Salimi et al. JSA 2025 (VoR refs, Crossref)
2016 White et al. SROS      ◀── P5 [39]      ◀── P7
2018 Kim et al. arXiv:1809.09566 ◀── P5 [42]
2022 Mayoral-Vilches et al. SROS2 ◀── P5 [17] (printed with a wrong title) ◀── P7
2022 Deng et al. CCS        ◀── P5 [49]      ◀── P6 ROSec (Crossref refs)
```

Forward citations (Semantic Scholar / OpenAlex; relevance judged from abstracts only):
- P5 → cited by 7 (S2) / 4 (OpenAlex): DoS via DDS discovery (DATE 2026), SERA (IEEE Access 2026),
  surveys, anomaly detection. None addresses in-flight revocation or multi-operator authority.
- P6 → cited by 2 (S2) / 4 (OpenAlex): surveys, SERA, QoS. None relevant.
- P7 → S2 does not index the DOI; OpenAlex 4: ROS 2 survey (ACM 2026), mining multi-robot blockchain
  (PPNA 2026), NGAC authorization for multi-robot (DCAS 2026), swarm trajectory coordination (MATEC
  2026). NGAC abstract: latency-focused; no revocation/in-flight handling mentioned.

## Cross-line edges

**None found.** Neither HORUS paper cites any ROS security work, and no ROS security paper found cites
either HORUS paper. The two lines are connected in this project only by *our* hypothesis — not by the
literature. Design documents (P3, P4) and code (P8, P9) are not citation nodes.
