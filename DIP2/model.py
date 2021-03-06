import torch
import torch.nn as nn
import torch.nn.functional as F
from collections import OrderedDict

from torchvision import models



class SegNetEnc(nn.Module):

    def __init__(self, in_channels, out_channels, num_layers):
        super().__init__()
        layers = [
            nn.Conv2d(in_channels, in_channels // 2, 3, padding=1),
            nn.BatchNorm2d(in_channels // 2),
            nn.ReLU(inplace=True),
        ]
        layers += [
            nn.Conv2d(in_channels // 2, in_channels // 2, 3, padding=1),
            nn.BatchNorm2d(in_channels // 2),
            nn.ReLU(inplace=True),
        ] * num_layers
        layers += [
            nn.Conv2d(in_channels // 2, out_channels, 3, padding=1),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),
        ]
        self.encode = nn.Sequential(*layers)

    def forward(self, x):
        return self.encode(x)


class SegNet(nn.Module):

    def __init__(self):
        super().__init__()
        vgg16 = models.vgg16(pretrained=True)
        features = vgg16.features
        self.dec1 = features[0: 4]
        self.dec2 = features[5: 9]
        self.dec3 = features[10: 16]
        self.dec4 = features[17: 23]
        self.dec5 = features[24: -1]

        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                m.requires_grad = False

        self.enc5 = SegNetEnc(512, 512, 1)
        self.enc4 = SegNetEnc(512, 256, 1)
        self.enc3 = SegNetEnc(256, 128, 1)
        self.enc2 = SegNetEnc(128, 64, 0)

        self.final = nn.Sequential(*[
            nn.Conv2d(64, 1, 3, padding=1),
            nn.ReLU(inplace=True)
        ])

    def forward(self, x):
        x1 = self.dec1(x)
        d1, m1 = F.max_pool2d(x1, kernel_size=2, stride=2, return_indices=True)
        x2 = self.dec2(d1)
        d2, m2 = F.max_pool2d(x2, kernel_size=2, stride=2, return_indices=True)
        x3 = self.dec3(d2)
        d3, m3 = F.max_pool2d(x3, kernel_size=2, stride=2, return_indices=True)
        x4 = self.dec4(d3)
        d4, m4 = F.max_pool2d(x4, kernel_size=2, stride=2, return_indices=True)
        x5 = self.dec5(d4)
        d5, m5 = F.max_pool2d(x5, kernel_size=2, stride=2, return_indices=True)

        def upsample(d):
            e5 = self.enc5(F.max_unpool2d(d, m5, kernel_size=2, stride=2, output_size=x5.size()))
            e4 = self.enc4(F.max_unpool2d(e5, m4, kernel_size=2, stride=2, output_size=x4.size()))
            e3 = self.enc3(F.max_unpool2d(e4, m3, kernel_size=2, stride=2, output_size=x3.size()))
            e2 = self.enc2(F.max_unpool2d(e3, m2, kernel_size=2, stride=2, output_size=x2.size()))
            e1 = F.max_unpool2d(e2, m1, kernel_size=2, stride=2, output_size=x1.size())
            return e1

        e = upsample(d5)

        return torch.squeeze(self.final(e), dim=1)


if __name__=='__main__':
    test_inp = torch.ones(5,3,64,64)

    model = SegNet()
    out = model(test_inp)
    print(out.shape)
    print(model)