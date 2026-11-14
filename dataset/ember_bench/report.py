"""Collect results/*.json|csv into one markdown table: python -m ember_bench.report results"""
import csv
import glob
import json
import os
import sys


def main(out="results"):
    L = []
    host = {}
    hp = os.path.join(out, "scaling_host.json")
    if os.path.exists(hp):
        host = json.load(open(hp))
    L += [f"# Ember benchmark results", "",
          f"Measured on `{host.get('machine', '?')}`, {host.get('cores', '?')} cores, {host.get('time', '')}.", ""]

    p = os.path.join(out, "scaling.csv")
    if os.path.exists(p):
        rows = list(csv.DictReader(open(p)))
        L += ["## 1. Single-run cost (one core): same fires, finer grid", "",
              "30.7 km domain, centred ignition, 20-ft wind 0-6 m/s, 8 random scenarios per row.", "",
              "| grid | cell | horizon | ForeFire solve median | p90 | max | setup | read-out | whole process | front nodes | burned km² |",
              "|---|---|---|---|---|---|---|---|---|---|---|"]
        for r in rows:
            f = lambda k: float(r[k]) if r.get(k) not in (None, "") else float("nan")
            L.append(f"| {r['n']}² | {f('dx_m'):.0f} m | {f('horizon_h'):g} h | {f('t_sim_median_s')*1e3:.1f} ms | "
                     f"{f('t_sim_p90_s')*1e3:.0f} ms | {f('t_sim_max_s'):.2f} s | {f('t_setup_median_s')*1e3:.0f} ms | "
                     f"{f('t_extract_median_s')*1e3:.0f} ms | {f('t_process_median_s'):.3f} s | "
                     f"{f('front_nodes_median'):.0f} | {f('burned_km2_median'):.1f} |")
        L.append("")

    ens = [json.load(open(p)) for p in sorted(glob.glob(os.path.join(out, "ensemble_*.json")))]
    if ens:
        L += ["## 2. Ensemble cost (all cores, one fresh process per run)", "",
              "Random scenarios from the full parameter space (scenarios.PARAMS).", "",
              "| grid | cell | horizon | runs | wall | runs/s | core-s/run | solve median | solve p99 | parallel eff. | fire hit edge |",
              "|---|---|---|---|---|---|---|---|---|---|---|"]
        for e in sorted(ens, key=lambda e: (e["n"], e["runs"])):
            L.append(f"| {e['n']}² | {e['dx_m']:.0f} m | {e['horizon_s']/3600:g} h | {e['runs']:,} | {e['wall_s']:.1f} s | "
                     f"{e['runs_per_s']:.0f} | {e['core_s_per_run']*1e3:.1f} ms | {e['t_sim_median_s']*1e3:.1f} ms | "
                     f"{e['t_sim_p99_s']*1e3:.0f} ms | {e['parallel_efficiency']:.2f} | {e['edge_hit_frac']*100:.1f}% |")
        L.append("")

    for p in sorted(glob.glob(os.path.join(out, "floor_*.csv"))):
        rows = list(csv.DictReader(open(p)))
        L += ["## 3. Accuracy bar: how much does ForeFire disagree with itself?", "",
              f"`{os.path.basename(p)}`: medians over random scenarios (p10 in brackets for IoU).", "",
              "| perturbation | IoU final | IoU @15 min | area error | arrival MAE | arrival p90 error |",
              "|---|---|---|---|---|---|"]
        for r in rows:
            f = lambda k: float(r[k])
            L.append(f"| {r['variant']} | {f('iou_final_median'):.3f} ({f('iou_final_p10'):.2f}) | "
                     f"{f('iou_t15min_median'):.3f} | {f('area_rel_err_median')*100:.1f}% | "
                     f"{f('at_mae_min_median'):.1f} min | {f('at_p90_min_median'):.1f} min |")
        L.append("")

    for p in sorted(glob.glob(os.path.join(out, "riskmap_*.json"))):
        r = json.load(open(p))
        L += ["## 4. Burn-probability map: how many ForeFire members are enough?", "",
              f"{r['members']:,} weather-perturbed members, {r['n']}² grid, {r['horizon_s']/3600:g} h. "
              f"Wall {r['wall_s']:.1f} s on {r['workers']} cores ({r['core_s_per_member']*1e3:.1f} core-ms/member). "
              "Error of an N-member map against the full ensemble:", "",
              "| members | mean abs prob. error | max abs error | IoU of p≥0.5 area | IoU of p≥0.1 area |",
              "|---|---|---|---|---|"]
        for m, c in r["convergence_vs_full"].items():
            L.append(f"| {int(m):,} | {c['prob_mae']:.4f} | {c['prob_max_err']:.3f} | {c['p50_iou']:.3f} | {c['p10_iou']:.3f} |")
        L.append("")

    bp = os.path.join(out, "breakeven.md")
    if os.path.exists(bp):
        L += ["## 5. Break-even", ""] + open(bp).read().splitlines()[2:] + [""]
    text = "\n".join(L)
    open(os.path.join(out, "RESULTS.md"), "w").write(text)
    print(text)


if __name__ == "__main__":
    main(*(sys.argv[1:] or ["results"]))
