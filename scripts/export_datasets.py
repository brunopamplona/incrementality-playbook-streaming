"""Generate the datasets in data/ (3 years of daily data, 27 UFs, 10 channels)."""
from pathlib import Path

from growthlab import calibrated_config, run_simulation
from growthlab.export import export_datasets

ROOT = Path(__file__).resolve().parents[1]
cfg = calibrated_config(80_000, monthly_budget_brl=3_250_000)
df = run_simulation(cfg)
for name, (path, n) in export_datasets(df, cfg, ROOT / "data").items():
    print(f"{path.relative_to(ROOT)}: {n:,} rows, {path.stat().st_size/1e6:.1f} MB")
print(f"period: {df['date'].min().date()} to {df['date'].max().date()}")
