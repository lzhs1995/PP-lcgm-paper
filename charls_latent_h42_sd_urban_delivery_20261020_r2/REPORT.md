# CHARLS H4.2: Baseline urban-status difference in the SD moderation path

Recorded: 2026-10-20T18:22:10.592532+00:00

**Four complete moderation inferences and complete H4 remain unfinished.** This packet reports one CHARLS absolute contact-frequency SD × baseline urban-status working family. It does not complete the original CFPS four moderation paths, and it is not a causal or threshold claim.

## What was actually estimated

- Twenty conditional working MI members (N=2,689; 438 communities), plus MI01 independent start B: 21 Mplus calls, 134 transformed parameters per known-class member.
- The actual input uses `KNOWNCLASS=cg(c4=0 c4=1)`, where C4 is the urban-status grouping variable; C3 remains an ordinary education control. All 21 saved INP files were independently parsed against TECH1 and the saved parameter transforms.
- The independent readback checked 2,814 parameters, full robust covariance matrices, legality geometry, and the 20-member Rubin pool. The original model/output hashes are unchanged. No new full-family calls were made during this semantic correction.
- The working MI is conditional and does not prove MAR or exact congeniality with the nonlinear latent-interaction model. The shared structure is a known-class representation; it is not an unrestricted multi-group model.

## Primary result

| contrast | estimate | 95% conditional MI interval | p |
|---|---:|---:|---:|
| urban-status group 1 − group 0: SX×IZ → SY | -0.092216 | [-0.405227, 0.220796] | 0.563655 |

The interval crosses zero. The planned 12-test Bonferroni value is 1.000. A difference between group-specific stars would not be a group-difference test.

## Semantic correction and calibration

The first candidate packet was held because its prose still said education, its community diagnostic read C3 rather than C4, and its parameter-label sidecar inherited six education labels. The corrected audit reads the actual NAMES/USEVARIABLES/KNOWNCLASS blocks and TECH1 for every member. The correct C4 group counts are 1,692 and 997; the number of communities containing both urban groups is 0. The earlier value 249 was the C3 diagnostic and is not a城乡 result. The parameter transform and saved estimates/VCOV remain unchanged.

Four additional **MI01-only** calibration calls were then completed in a separate isolated directory: ordinary 15-point parent, C4 known-class 15-point parent, and C4 7-point A/B checks. All four calls were usable. Parent equivalence and both 7-to-15 comparisons passed the frozen LL/parameter/SE/VCOV tolerances; the A/B 7-point start comparison also passed. This calibrates the representation and quadrature behavior for the same urban MI01 data. It does not convert the 20-member working MI into a fully congenial imputation analysis.

## Reproduction boundary

The public verifier reads the saved aggregate matrices and performs no Mplus call. Participant DAT/RDS/MIDS files and individual scores are excluded. Re-estimation requires a new isolated Windows run and the original licensed Mplus installation. The original CFPS manuscript and failed CFPS specifications are preserved; they were not rerun here.

The actual executed MI source is included separately from historical generator code. Runtime recovery records distinguish a transient missing async acknowledgement, a rejected duplicate MI submission protected by an existing MIDS file, and pre-engine template errors. “No duplicate computation” must not be read as “no duplicate submission.”

## Status

This is a corrected and calibration-supported CHARLS SD×urban-status evidence packet. It is not a completion certificate for four moderation families or full H4. Remaining CHARLS H4.2 resource/indicator families and the original CFPS mechanism work require separate contracts.
