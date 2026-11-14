"""Small supervised segmentation U-Net. Forward returns raw logits, never sigmoid."""
import torch
from torch import nn


class ConvBlock(nn.Module):
    def __init__(self, in_channels, out_channels, dropout):
        super().__init__()
        self.layers = nn.Sequential(
            nn.Conv2d(in_channels, out_channels, 3, padding=1), nn.ReLU(inplace=True),
            nn.Conv2d(out_channels, out_channels, 3, padding=1), nn.ReLU(inplace=True),
            nn.Dropout2d(dropout),
        )

    def forward(self, x):
        return self.layers(x)


class UNet(nn.Module):
    def __init__(self, in_channels, base_filters=16, depth=3, dropout=0.0):
        super().__init__()
        self.factor = 2 ** depth
        self.down = nn.ModuleList()
        self.up = nn.ModuleList()
        self.decode = nn.ModuleList()
        widths = [base_filters * 2 ** i for i in range(depth + 1)]
        for width in widths[:-1]:
            self.down.append(ConvBlock(in_channels, width, dropout))
            in_channels = width
        self.pool = nn.MaxPool2d(2)
        self.bottleneck = ConvBlock(widths[-2], widths[-1], dropout)
        for i in range(depth - 1, -1, -1):
            self.up.append(nn.ConvTranspose2d(widths[i + 1], widths[i], 2, stride=2))
            self.decode.append(ConvBlock(widths[i] * 2, widths[i], dropout))
        self.output = nn.Conv2d(widths[0], 1, 1)

    def forward(self, x):
        if x.ndim != 4 or x.shape[-2] % self.factor or x.shape[-1] % self.factor:
            raise ValueError(f"Expected [B,C,H,W] with H,W divisible by {self.factor}")
        skips = []
        for block in self.down:
            x = block(x)
            skips.append(x)
            x = self.pool(x)
        x = self.bottleneck(x)
        for up, block, skip in zip(self.up, self.decode, reversed(skips)):
            x = block(torch.cat((up(x), skip), dim=1))
        return self.output(x)


def build_model(cfg):
    return UNet(len(cfg["channel_names"]), cfg["base_filters"], cfg["depth"], cfg["dropout"])
