# Trust Model

## Overview

OpenWorld uses an **explainable** trust model. Trust scores are not arbitrary AI-generated numbers.

## Dimensions

| Dimension | Weight | Description |
|-----------|--------|-------------|
| Identity | 20% | Agent identity validity |
| Policy | 25% | Policy compliance rate |
| Reliability | 20% | Historical execution success |
| Verification | 20% | Verification success rate |
| Violations | 15% | Violation-free score |

## Score Calculation

```
Trust Score = Σ(dimension × weight)
```

Range: 0–100. Higher is more trusted.

## Example

```
Trust Score: 98.4

Identity:        100
Policy:           99
Reliability:      98
Verification:     99
Violations:      100
```

Every dimension is inspectable and explainable.

## Limitations

- Initial model is rule-based, not ML-based
- Scores reflect demo/synthetic data in MVP
- Production deployment will require calibration
