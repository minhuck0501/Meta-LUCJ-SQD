# Meta-LUCJ-SQD

## Research Mission

Develop and validate geometry-conditioned LUCJ initialization methods for efficient SQD calculations of molecular potential energy curves.

## Scientific Priorities

1. Correctness before speed.
2. SQD energy accuracy before parameter-fitting accuracy.
3. Reproducibility before large computational sweeps.
4. Fair comparison with independent and sequential warm-start baselines.
5. Explicit accounting of meta-training overhead.
6. Honest reporting of failed experiments and limitations.

## Implementation Rules

- Do not write code comments.
- Use modular Python code.
- Prefer established quantum chemistry libraries.
- Keep configuration separate from implementation.
- Fix and record random seeds.
- Avoid expensive calculations before validating numerical correctness.
- Save experiment configurations, results, and timing information.
- Do not change scientific definitions or benchmark settings silently.

## Collaboration Protocol

- Read the relevant reference files before implementing scientific methods.
- Clearly distinguish established methods from proposed research ideas.
- Explain the mathematical reasoning behind major algorithmic decisions.
- Use small, deterministic tests before launching expensive experiments.
- Update docs/DECISIONS.md when methodological choices change.
- Do not claim a result without experimental evidence.