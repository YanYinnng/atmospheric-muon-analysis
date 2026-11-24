"""Figures for one run. Each function writes a PNG and returns nothing."""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

COLORS = {"master": "#2f6db5", "slave": "#c8553d", "diff": "#7a7a7a"}


def _save(fig, path):
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def plot_counts(fits, path):
    """Per-second count histogram with the fitted Poisson model, one panel per detector."""
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    for ax, (role, f) in zip(axes, fits.items()):
        ax.bar(f["k"], f["freq"], color=COLORS[role], alpha=0.6, label="data")
        ax.plot(f["k"], f["model"], "ko-", ms=3, lw=1, label="Poisson fit")
        ax.set(title=f"{role}: events per second", xlabel="events in 1 s", ylabel="number of seconds")
        ax.text(0.97, 0.75, f"$\\lambda$ = {f['lambda']:.3f} /s\n"
                f"$\\chi^2$/NDF = {f['chi2']:.1f}/{f['ndf']} = {f['chi2'] / f['ndf']:.2f}\n"
                f"var/mean = {f['fano']:.3f}",
                transform=ax.transAxes, ha="right", va="top", fontsize=9)
        ax.legend(loc="upper right", fontsize=8, bbox_to_anchor=(1, 1))
    _save(fig, path)


def plot_intervals(fits, path):
    """Gap histograms on a log scale (an exponential is a straight line); fitted range drawn solid."""
    fig, axes = plt.subplots(2, 2, figsize=(11, 7.5))
    for ax, ((role, label), f) in zip(axes.flat, fits.items()):
        x, c = f["centres"], f["counts"]
        ax.step(x, np.where(c > 0, c, np.nan), where="mid", color=COLORS[role], label="data")
        fitted = np.arange(x.size) >= f["skip_bins"]
        ax.plot(x[fitted], f["model"][fitted], "k-", lw=1.2, label="exponential fit")
        ax.plot(x[~fitted], c[~fitted], "kx", ms=7, label="first bin, not fitted (dead time)")
        ax.set_yscale("log")
        ax.set_ylim(0.5, c.max() * 2)
        ax.set(title=f"{role}, {label}", xlabel="time between consecutive events [ms]",
               ylabel=f"events / {f['width']:.0f} ms")
        ax.text(0.03, 0.04, f"N = {f['n_events']}\n"
                f"1/mean gap = {f['rate_hz']:.3f} $\\pm$ {f['rate_err_hz']:.3f} Hz\n"
                f"1/$\\tau_{{fit}}$ = {f['rate_fit_hz']:.3f} Hz\n"
                f"$\\chi^2$/NDF = {f['chi2'] / f['ndf']:.2f}",
                transform=ax.transAxes, ha="left", va="bottom", fontsize=9,
                bbox=dict(fc="white", ec="none", alpha=0.85))
        ax.legend(loc="upper right", fontsize=8)
    _save(fig, path)


def plot_spectrum(master_mv, slave_mv, thresholds, ratio, ratio_err, cut_mv, path):
    """Left: SiPM peak-voltage spectra and their difference. Right: threshold scan."""
    edges = np.arange(10, 51, 1.0)
    hm = np.histogram(master_mv, bins=edges)[0]
    hs = np.histogram(slave_mv, bins=edges)[0]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4))
    ax1.stairs(hm - hs, edges, fill=True, color=COLORS["diff"], alpha=0.35, label="master $-$ slave")
    ax1.stairs(hm, edges, color=COLORS["master"], lw=1.5, label=f"master (N={master_mv.size})")
    ax1.stairs(hs, edges, color=COLORS["slave"], lw=1.5, label=f"slave (N={slave_mv.size})")
    ax1.set(title="SiPM peak voltage (1 mV bins)", xlabel="SiPM peak voltage [mV]", ylabel="events")
    ax1.legend(fontsize=8)
    ax2.errorbar(thresholds, ratio, yerr=ratio_err, fmt="o-", color="k", ms=4, capsize=2)
    best = thresholds[np.argmax(ratio)]
    ax2.axvline(cut_mv, color=COLORS["slave"], ls="--", lw=1, label=f"cut used: {cut_mv:g} mV")
    ax2.set(title=f"slave / master above threshold (max at {best:g} mV)",
            xlabel="threshold v [mV]", ylabel="N(slave, V $\\geq$ v) / N(master, V $\\geq$ v)")
    ax2.legend(fontsize=8)
    _save(fig, path)
