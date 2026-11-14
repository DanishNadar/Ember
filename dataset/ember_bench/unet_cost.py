"""Analytic cost of a standard U-Net surrogate (no torch on the build VM).
in_ch -> base*2^l channels at level l (4 levels), two 3x3 convs per block, BF16.
Time = max(FLOPs / eff_flops, bytes / eff_bw). Assumed GB10 effective rates, NOT measured."""
EFF_FLOPS = 20e12   # achieved BF16 FLOP/s (assumption: ~1/3 of dense BF16 peak)
EFF_BW = 200e9      # achieved bytes/s (GB10 LPDDR5x peak is 273 GB/s)

def unet(n, in_ch=10, base=32, levels=4, out_ch=1):
    fl = by = 0.0
    def conv(c_in, c_out, px):
        nonlocal fl, by
        fl += 2 * 9 * c_in * c_out * px
        by += 2 * (c_in + c_out) * px          # read input + write output, 2 bytes each
    c_prev = in_ch
    for l in range(levels + 1):                 # encoder + bottleneck
        px = (n >> l) ** 2; c = base * 2 ** l
        conv(c_prev, c, px); conv(c, c, px); c_prev = c
    for l in range(levels - 1, -1, -1):         # decoder (upsample, concat skip)
        px = (n >> l) ** 2; c = base * 2 ** l
        conv(c_prev // 2 + c, c, px); conv(c, c, px); c_prev = c
    fl += 2 * c_prev * out_ch * n * n
    return fl, by

def infer_s(n, batch=1):
    fl, by = unet(n)
    return batch * max(fl / EFF_FLOPS, by / EFF_BW), fl, by

if __name__ == "__main__":
    for n in [160, 320, 640, 1280, 2560]:
        t, fl, by = infer_s(n)
        print(n, f"{fl/1e9:.1f} GFLOP  {by/1e9:.2f} GB  -> {t*1e3:.2f} ms/scenario")
