"""Statistics used in the analysis.

Binned fits follow ROOT's default TH1::Fit convention, which the original
PyROOT analysis used: chi-square with sigma = sqrt(observed count), empty bins
skipped, model evaluated at bin centres.
"""
import numpy as np
from scipy.optimize import curve_fit
from scipy.stats import poisson


def _neyman_fit(model, x, counts, p0, used=None):
    """Fit model(x, *p) to counts with sigma = sqrt(counts); empty bins are skipped."""
    used = (counts > 0) if used is None else used & (counts > 0)
    popt, pcov = curve_fit(model, x[used], counts[used], p0=p0,
                           sigma=np.sqrt(counts[used]), absolute_sigma=True)
    resid = (counts[used] - model(x[used], *popt)) / np.sqrt(counts[used])
    return popt, np.sqrt(np.diag(pcov)), float(resid @ resid), int(used.sum() - len(popt))


def counts_per_second(time_ms):
    """Number of events in each 1 s window from t = 0 to the last event."""
    n_sec = int(np.ceil(time_ms.max() / 1000))
    return np.histogram(time_ms, bins=np.arange(n_sec + 1) * 1000.0)[0]


def fit_poisson(counts):
    """Fit N * Poisson(k; lambda) to the histogram of per-second counts."""
    k = np.arange(counts.max() + 1)
    freq = np.bincount(counts, minlength=k.size).astype(float)
    model = lambda x, n, lam: n * poisson.pmf(np.rint(x), lam)
    (n, lam), (_, lam_err), chi2, ndf = _neyman_fit(model, k, freq, p0=[counts.size, counts.mean()])
    return {
        "k": k, "freq": freq, "model": model(k, n, lam),
        "lambda": lam, "lambda_err": lam_err, "chi2": chi2, "ndf": ndf,
        "mean": counts.mean(),
        # Var/mean = 1 for a Poisson process; dead time pushes it below 1.
        "fano": counts.var() / counts.mean(),
    }


def dead_time_fraction(events):
    """Fraction of the run during which the detector could not record (cumulative dead-time column)."""
    return events["deadtime_ms"][-1] / events["time_ms"][-1]


def fit_intervals(time_ms, x_max, n_bins=200, skip_bins=0):
    """Fit A * exp(-dt / tau) to the histogram of gaps between consecutive events.

    skip_bins drops the first bins from the fit; the shortest gaps are depleted
    because the detector is dead for a few ms after each event.
    """
    gaps = np.diff(time_ms)
    counts, edges = np.histogram(gaps, bins=n_bins, range=(0, x_max))
    centres = (edges[:-1] + edges[1:]) / 2
    model = lambda x, a, tau: a * np.exp(-x / tau)
    used = np.arange(n_bins) >= skip_bins
    (a, tau), (_, tau_err), chi2, ndf = _neyman_fit(model, centres, counts.astype(float),
                                                     p0=[counts[skip_bins], gaps.mean()], used=used)
    rate = 1000.0 / gaps.mean()
    return {
        "centres": centres, "width": edges[1] - edges[0], "counts": counts,
        "model": model(centres, a, tau), "skip_bins": skip_bins,
        "n_events": time_ms.size, "mean_gap_ms": gaps.mean(),
        "tau_ms": tau, "tau_err_ms": tau_err, "chi2": chi2, "ndf": ndf,
        "rate_hz": rate, "rate_err_hz": rate / np.sqrt(time_ms.size),
        "rate_fit_hz": 1000.0 / tau,
    }


def slave_fraction_above(master_mv, slave_mv, thresholds):
    """Ratio (# slave events with V >= v) / (# master events with V >= v), with a binomial error."""
    n_master = np.array([(master_mv >= v).sum() for v in thresholds])
    ratio = np.array([(slave_mv >= v).sum() for v in thresholds]) / n_master
    return ratio, np.sqrt(ratio * (1 - ratio) / n_master)
