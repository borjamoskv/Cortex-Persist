# FINAL_AUDIT.md

## Babylon-60 / Cortex — Session Audit

### Commit

- Hash: `506b7a320`
- Scope: ProvenanceAuditor opacification, softmax stabilization, dimensional scale normalization

### Reality Classification

#### C5-REAL — Reproducible / Verifiable

These claims are externally inspectable or reproducible:

- Commit `506b7a320` exists in the repository.
- Test results are C5-REAL if executed and recorded.
- Opaque baselines are present in source if the code contains no provider/model-name coupling.
- ProvenanceAuditor explicitly avoids exact identity attribution.

#### C5-FORMAL — Deterministic by Construction
These claims hold for fixed inputs and fixed code:

- Feature extraction is deterministic for fixed harness outputs.
- Distance computation is deterministic for fixed observed vectors and fixed baselines.
- Softmax/similarity computation is deterministic for fixed distances.
- Dimensional scale normalization is deterministic.
- `identity_attribution: not_supported` or equivalent is an explicit design property.

#### C4 — Plausible / Useful but Empirically Unvalidated
These claims are engineering-plausible but require data for stronger status:

- The passive signature module can support drift detection.
- The module can support endpoint consistency auditing.
- The module can support anonymous clustering.
- The module may help detect behavioral changes over time.

These do not prove:
- exact model identity;
- provider attribution;
- checkpoint identity;
- claimed accuracy without labeled validation.

#### C2-C3 — Rhetorical / Subjective / Session Framing
These are useful interpretive framings, not reproducible facts:

- "Model X response was superior."
- "This answer won the comparison."
- "Exergy," "dialectic closure," "atomic turn," or similar session metaphors.
- Any judgement about which assistant handled the epistemic demarcation better.
- This audit's own value judgements about conversational quality.

### Open Scientific Debt
The following remains unvalidated:

- Passive attribution accuracy.
- Robustness across regions, network conditions, prompt families, and provider load.
- Calibration stability over time.
- Confusion matrix against labeled endpoints.
- Brier score / ECE for any claimed probabilistic confidence.
- Double-blind isolation of variables for response-quality comparisons.

### Required Evidence for Future Accuracy Claims
Any future claim such as "the auditor identifies hidden model families with X% accuracy" requires:

- labeled dataset;
- controlled prompt suite;
- fixed evaluation protocol;
- train/validation/test split or cross-validation;
- confusion matrix;
- calibration metrics;
- robustness analysis by region, load, and prompt type;
- explicit distinction between clustering, family inference, and exact identity.

### Final Status
```yaml
Engineering:
  Status: "Complete for current scope"
  Notes:
    - "BlackBoxHarness async/streaming issues addressed"
    - "ProvenanceAuditor baselines opacified"
    - "Softmax and dimensional scaling stabilized"
    - "Identity attribution claims removed or marked unsupported"

Science:
  Status: "Open"
  Notes:
    - "Passive attribution remains unvalidated"
    - "Accuracy claims require labeled empirical validation"

Rhetoric:
  Status: "Demarcated"
  Notes:
    - "Session metaphors remain useful but non-C5"
    - "Judgements of response superiority are C2-C3"
```

### Closing Principle
Do not promote rhetorical clarity, conversational force, or perceived model superiority to C5-REAL.

C5-REAL is reserved for reproducible, inspectable, externally verifiable facts.
C5-FORMAL is reserved for deterministic properties of fixed algorithms.
Everything else must remain explicitly marked as empirical, provisional, subjective, or rhetorical.
