"""Small 2D U-Net for research whole-tumor segmentation on axial FLAIR."""
import torch
from torch import nn
from torch.nn import functional as F


def block(inputs, outputs):
    return nn.Sequential(nn.Conv2d(inputs, outputs, 3, padding=1), nn.GroupNorm(4, outputs),
                         nn.ReLU(), nn.Conv2d(outputs, outputs, 3, padding=1),
                         nn.GroupNorm(4, outputs), nn.ReLU())


class TumorUNet(nn.Module):
    def __init__(self):
        super().__init__()
        self.enc1 = block(1, 16)
        self.enc2 = block(16, 32)
        self.bridge = block(32, 64)
        self.dec2 = block(96, 32)
        self.dec1 = block(48, 16)
        self.out = nn.Conv2d(16, 1, 1)

    def forward(self, x):
        a = self.enc1(x)
        b = self.enc2(F.max_pool2d(a, 2))
        c = self.bridge(F.max_pool2d(b, 2))
        d = self.dec2(torch.cat([F.interpolate(c, size=b.shape[2:], mode="bilinear", align_corners=False), b], 1))
        return self.out(self.dec1(torch.cat([F.interpolate(d, size=a.shape[2:], mode="bilinear", align_corners=False), a], 1)))
