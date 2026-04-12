# Hurricane External Shock Experiment (Paper Section 7.5)

Simulates Hurricane Dorian impact on mobility in Columbia, SC over 9 days.

## Paper Findings
- Activity level drops from 70-90% to ~30% during hurricane landfall
- Gradual recovery to normal levels after hurricane passes
- Simulated daily trips align with real SafeGraph mobility data

## Run

```bash
pip install agentsociety2 python-dotenv
python run_hurricane.py
```

Results saved to `results/hurricane/results.json`.
