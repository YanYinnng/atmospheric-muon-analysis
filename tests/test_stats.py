"""Checks on simulated event streams with known rate and dead time."""
import tempfile
import unittest
from pathlib import Path

import numpy as np

from muon import stats
from muon.io import load_events, load_run


def simulate(rate_hz, duration_s, dead_ms=0.0, seed=0):
    """Event times [ms] of a Poisson process seen through a non-paralyzable dead time."""
    rng = np.random.default_rng(seed)
    t = np.cumsum(rng.exponential(1000.0 / rate_hz, size=int(rate_hz * duration_s * 1.2)))
    t = t[t < duration_s * 1000]
    if dead_ms:
        kept, last = [], -np.inf
        for x in t:
            if x - last >= dead_ms:
                kept.append(x)
                last = x
        t = np.array(kept)
    return np.round(t)


class PoissonFit(unittest.TestCase):
    def test_recovers_rate(self):
        fit = stats.fit_poisson(stats.counts_per_second(simulate(3.0, 20000)))
        self.assertAlmostEqual(fit["lambda"], 3.0, delta=4 * fit["lambda_err"])
        self.assertAlmostEqual(fit["fano"], 1.0, delta=0.05)

    def test_dead_time_gives_var_below_mean(self):
        fit = stats.fit_poisson(stats.counts_per_second(simulate(5.0, 20000, dead_ms=10)))
        self.assertLess(fit["fano"], 0.97)


class IntervalFit(unittest.TestCase):
    def test_slope_gives_true_rate(self):
        fit = stats.fit_intervals(simulate(2.0, 20000), x_max=4000, skip_bins=1)
        self.assertAlmostEqual(fit["rate_fit_hz"], 2.0, delta=0.05)

    def test_dead_time_depletes_first_bin_only(self):
        t = simulate(5.0, 20000, dead_ms=10)
        with_first = stats.fit_intervals(t, x_max=4000, skip_bins=0)
        without = stats.fit_intervals(t, x_max=4000, skip_bins=1)
        self.assertGreater(with_first["chi2"] / with_first["ndf"], 2)
        self.assertLess(without["chi2"] / without["ndf"], 1.5)
        # The slope still measures the undistorted rate; 1/mean gap is lowered by dead time.
        self.assertAlmostEqual(without["rate_fit_hz"], 5.0, delta=0.1)
        self.assertLess(without["rate_hz"], 4.85)


class ThresholdScan(unittest.TestCase):
    def test_ratio(self):
        master = np.array([10, 12, 14, 16, 18, 20])
        slave = np.array([14, 18, 20])
        ratio, err = stats.slave_fraction_above(master, slave, np.array([10, 15, 19]))
        np.testing.assert_allclose(ratio, [3 / 6, 2 / 3, 1 / 1])
        self.assertEqual(err[-1], 0)


class Loading(unittest.TestCase):
    def test_shipped_runs(self):
        for run in ("run1", "run2"):
            for role, events in load_run(run).items():
                self.assertGreater(events.size, 10000, f"{run} {role}")

    def test_rejects_unsorted_times(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "bad.csv"
            path.write_text("event,time_ms,adc,sipm_mv,deadtime_ms,temp_c\n1,50,1,1,1,20\n2,40,1,1,1,20\n")
            with self.assertRaises(ValueError):
                load_events(path)


if __name__ == "__main__":
    unittest.main()
