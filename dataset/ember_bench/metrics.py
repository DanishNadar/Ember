"""Surrogate accuracy metrics. Arrival maps use +inf for 'never burned'."""
import numpy as np


def burned(at, t=None):
    """Burned mask at time t (default: anything that burned within the horizon)."""
    return np.isfinite(at) if t is None else (at <= t)


def iou(a, b):
    a, b = a.astype(bool), b.astype(bool)
    u = np.logical_or(a, b).sum()
    return 1.0 if u == 0 else float(np.logical_and(a, b).sum() / u)


def compare(pred, ref, dx, horizon_s, times=None):
    """All metrics for one predicted arrival map vs the ForeFire reference.

    - iou_final         burned-area IoU at the horizon
    - iou_t{min}        IoU of the burned area at intermediate times (front position over time)
    - area_rel_err      |A_pred - A_ref| / A_ref at the horizon
    - at_mae_min        mean |arrival error| in minutes over cells both maps burned
    - at_p90_min        90th percentile of that error
    - at_mae_rel        at_mae / horizon
    """
    times = times or [horizon_s / 4, horizon_s / 2]
    pb, rb = burned(pred), burned(ref)
    both = pb & rb
    err = np.abs(pred[both] - ref[both]) / 60.0 if both.any() else np.array([np.nan])
    a_ref = rb.sum() * dx * dx
    out = {
        "iou_final": iou(pb, rb),
        "area_rel_err": float(abs(pb.sum() - rb.sum()) * dx * dx / a_ref) if a_ref > 0 else np.nan,
        "at_mae_min": float(np.nanmean(err)),
        "at_p90_min": float(np.nanpercentile(err, 90)),
        "at_mae_rel": float(np.nanmean(err) * 60.0 / horizon_s),
    }
    for t in times:
        out[f"iou_t{int(t / 60)}min"] = iou(burned(pred, t), burned(ref, t))
    return out


def burn_probability(arrivals):
    """Fraction of ensemble members that burned each cell. arrivals: (N, n, n)."""
    return np.isfinite(arrivals).mean(axis=0)


def prob_map_error(p_pred, p_ref):
    """Errors between two burn-probability maps (e.g. 1k-member vs surrogate ensemble)."""
    d = np.abs(p_pred - p_ref)
    return {"prob_mae": float(d.mean()), "prob_max_err": float(d.max()),
            "p50_iou": iou(p_pred >= 0.5, p_ref >= 0.5), "p10_iou": iou(p_pred >= 0.1, p_ref >= 0.1)}
