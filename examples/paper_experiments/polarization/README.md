# Polarization Experiment (Paper Section 7.2)

Gun control opinion dynamics under three conditions.

## Paper Findings
- **Control**: 39% polarized, 33% moderated
- **Homophilic** (echo chamber): 52% polarized
- **Heterogeneous** (cross-cutting): 89% moderated

## Run

```bash
pip install agentsociety2 python-dotenv
# Set AGENTSOCIETY_LLM_API_KEY and AGENTSOCIETY_LLM_API_BASE in .env
python run_polarization.py
```

Results saved to `results/polarization/results.json`.
