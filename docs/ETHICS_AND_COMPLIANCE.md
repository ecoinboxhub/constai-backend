# Ethical, Bias, and Regulatory Considerations

## Bias and Fairness
- Data imbalance risk: prioritize balanced sampling across regions, contractor sizes, and project classes.
- Human-in-the-loop review is required for safety and legal recommendations.
- Confidence scores are exposed in API responses to avoid false certainty.

## Transparency and Auditability
- All model runs are tracked in MLflow (params/metrics/artifacts).
- DVC enforces reproducibility for data and model stages.
- Endpoint outputs include model-family labels and threshold assumptions.

## Nigerian/International Compliance
- Align handling of personal/company data with Nigeria Data Protection Regulation (NDPR) and applicable GDPR principles.
- Safety checks should map to COREN Act obligations and ILO-aligned site standards.
- Contract/tender analysis remains decision-support, not legal advice.

## Data Governance Controls
- Secrets isolated in `.env`; `.gitignore` excludes sensitive files.
- Use least-privilege DB accounts and rotate keys in production.
- Maintain retention and deletion policies for site logs/documents.

## Social Impact
- Positive: reduced accidents, fewer delays, better cost predictability.
- Risks: over-automation, opaque risk labeling, procurement exclusion bias.
- Mitigation: periodic bias audits, model cards, and appeal workflows for flagged outputs.
