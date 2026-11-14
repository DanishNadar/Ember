"""Measure what a reference surrogate costs on THIS machine (run it on the GB10 GPU node).

    python -m ember_bench.surrogate_cost --sizes 128 256 512 --out results

A plain 4-level U-Net (10 input channels -> 1 arrival-time channel), the
obvious first architecture for map-to-map emulation. Writes
results/surrogate_cost.json, which `python -m ember_bench breakeven` picks up
instead of its assumed inference time.

It measures throughput only. It says nothing about accuracy: that needs the
ML teammate's trained model scored with ember_bench.metrics.
"""
import argparse
import json
import os
import time

import torch
import torch.nn as nn


def block(i, o):
    return nn.Sequential(nn.Conv2d(i, o, 3, padding=1), nn.GELU(), nn.Conv2d(o, o, 3, padding=1), nn.GELU())


class UNet(nn.Module):
    def __init__(self, cin=10, w=32):
        super().__init__()
        ch = [w, 2 * w, 4 * w, 8 * w]
        self.down = nn.ModuleList([block(cin, ch[0]), block(ch[0], ch[1]), block(ch[1], ch[2]), block(ch[2], ch[3])])
        self.up = nn.ModuleList([nn.ConvTranspose2d(ch[i + 1], ch[i], 2, 2) for i in range(3)])
        self.dec = nn.ModuleList([block(2 * ch[i], ch[i]) for i in range(3)])
        self.head = nn.Conv2d(ch[0], 1, 1)

    def forward(self, x):
        skips = []
        for i, d in enumerate(self.down):
            x = d(x)
            if i < 3:
                skips.append(x)
                x = nn.functional.max_pool2d(x, 2)
        for i in reversed(range(3)):
            x = self.dec[i](torch.cat([self.up[i](x), skips[i]], 1))
        return self.head(x)


def bench(n, batch, dev, dtype, iters=20):
    m = UNet().to(dev)
    x = torch.randn(batch, 10, n, n, device=dev)
    sync = torch.cuda.synchronize if dev == "cuda" else (lambda: None)
    with torch.no_grad(), torch.autocast(dev, dtype=dtype, enabled=dev == "cuda"):
        for _ in range(3):
            m(x)
        sync(); t = time.perf_counter()
        for _ in range(iters):
            m(x)
        sync(); infer = (time.perf_counter() - t) / iters / batch
    opt = torch.optim.AdamW(m.parameters(), 1e-3)
    y = torch.randn(batch, 1, n, n, device=dev)
    for k in range(iters // 2 + 3):
        if k == 3:
            sync(); t = time.perf_counter()
        with torch.autocast(dev, dtype=dtype, enabled=dev == "cuda"):
            loss = nn.functional.mse_loss(m(x), y)
        opt.zero_grad(); loss.backward(); opt.step()
    sync(); step = (time.perf_counter() - t) / (iters // 2)
    return {"infer_s_per_query": infer, "train_step_s": step, "batch": batch,
            "params_M": sum(p.numel() for p in m.parameters()) / 1e6, "device": dev}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sizes", type=int, nargs="+", default=[128, 256, 512])
    ap.add_argument("--batch", type=int, default=32)
    ap.add_argument("--out", default="results")
    a = ap.parse_args()
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    res = {}
    for n in a.sizes:
        b = max(1, a.batch * (128 * 128) // (n * n))
        res[n] = bench(n, b, dev, torch.bfloat16)
        # e.g. 10k samples x 50 epochs: epochs_time = samples/batch * step
        res[n]["train_s_per_epoch_10k"] = 10000 / b * res[n]["train_step_s"]
        print(n, res[n], flush=True)
    os.makedirs(a.out, exist_ok=True)
    json.dump(res, open(os.path.join(a.out, "surrogate_cost.json"), "w"), indent=2)


if __name__ == "__main__":
    main()
