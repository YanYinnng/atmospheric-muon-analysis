"""Load de-identified CosmicWatch event tables from data/."""
from pathlib import Path

import numpy as np

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
COLUMNS = ("event", "time_ms", "adc", "sipm_mv", "deadtime_ms", "temp_c")


def load_events(path):
    """Return a structured array with one row per recorded event."""
    table = np.genfromtxt(path, delimiter=",", names=True)
    missing = set(COLUMNS) - set(table.dtype.names)
    if missing:
        raise ValueError(f"{path}: missing columns {sorted(missing)}")
    if np.any(np.diff(table["time_ms"]) < 0):
        raise ValueError(f"{path}: timestamps are not monotonic")
    return table


def load_run(run, data_dir=DATA_DIR):
    """Load the master and slave tables of one run, e.g. load_run("run1")."""
    return {role: load_events(Path(data_dir) / f"{run}_{role}.csv") for role in ("master", "slave")}
