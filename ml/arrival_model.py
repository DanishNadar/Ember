"""Two-headed *direct* simulator surrogate; no autoregressive state rollout.

Channel 0: unbounded logit of 'reached by horizon'.
Channel 1: unbounded logit converted by sigmoid to arrival fraction in [0, 1].
Uses the existing U-Net body without changing the legacy binary-mask baseline.
"""
import torch
from torch import nn
from model import UNet


class ArrivalUNet(nn.Module):
    def __init__(self, channels, base_filters=16, depth=3, dropout=0):
        super().__init__()
        self.body = UNet(channels, base_filters, depth, dropout)
        self.body.output = nn.Conv2d(base_filters, 2, kernel_size=1)

    def forward(self, x):
        out = self.body(x)
        return out[:, :1], torch.sigmoid(out[:, 1:2])


def masked_arrival_loss(burn_logits, time_fraction, reached, target_fraction, cfg):
    """Regress arrival times *only* where ForeFire reached the cell.

    An unreached cell is right-censored at the simulation horizon; it is not
    a known 'never burns' or an arrival time equal to horizon.
    """
    pos_weight = torch.tensor(cfg["positive_weight"], device=burn_logits.device)
    classification = nn.functional.binary_cross_entropy_with_logits(
        burn_logits, reached, pos_weight=pos_weight
    )
    count = reached.sum()
    if count.item() > 0:
        regression = nn.functional.smooth_l1_loss(
            time_fraction * reached, target_fraction * reached, reduction="sum"
        ) / count
    else:
        regression = burn_logits.sum() * 0.0
    return cfg["burn_loss_weight"] * classification + cfg["arrival_loss_weight"] * regression
