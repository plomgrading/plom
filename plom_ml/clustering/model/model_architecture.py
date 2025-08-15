# # SPDX-License-Identifier: AGPL-3.0-or-later
# # Copyright (C) 2025 Bryan Tanady
# """Defines the architecture of clustering models used upon training."""

# import torch
# import torch.nn as nn
# from torchvision import models  # type: ignore[import]


# class MCQClusteringNet(nn.Module):
#     """MCQ Clustering model architecture.

#     Current architecture uses resnet18 as a base with some modifications:
#         1. Modifies conv1 in_channels from 3 to 1, so model is targeted for grayscale task.
#         2. Changes last fully connected (fc) layer to outputs 11 classes, i,e A-F and a-f with
#             'C' and 'c' merged.
#         3. Replaces AdaptiveAvgPooling to custom AttentionPooling.
#     """

#     class _AttentionPooling(nn.Module):
#         """Custom attention pooling.

#         This custom pooling do weighted sum to the penultimate feature vectors.
#         The weights are obtained from Softmax function across the features.
#         """

#         def __init__(self, in_features: int):
#             super().__init__()
#             self.attention = nn.Sequential(
#                 nn.Linear(in_features, 512),
#                 nn.Tanh(),
#                 nn.Linear(512, 1),
#                 nn.Softmax(dim=1),
#             )

#         def forward(self, x: torch.Tensor):
#             # Input: [batch, channels, height, width]
#             batch, channels, h, w = x.size()
#             # Flatten spatial dimensions: [batch, channels, h*w]
#             flattened = x.view(batch, channels, h * w)
#             # Permute: [batch, h*w, channels]
#             flattened = flattened.permute(0, 2, 1)
#             # Compute attention weights: [batch, h*w, 1]
#             attn_weights = self.attention(flattened)
#             # Weighted sum: [batch, channels]
#             return torch.sum(attn_weights * flattened, dim=1)

#     def __init__(self, out_features):
#         super().__init__()
#         self.backbone = models.resnet18(models.ResNet18_Weights.DEFAULT)

#         # Changes in_channels from 3 to 1, other params remain the same
#         self.backbone.conv1 = nn.Conv2d(
#             in_channels=1,
#             out_channels=64,
#             kernel_size=7,
#             stride=2,
#             padding=3,
#             bias=False,
#         )

#         in_feats = self.backbone.fc.in_features
#         self.backbone.avgpool = self._AttentionPooling(in_feats)

#         # changes out_features from 1000 to 11
#         self.backbone.fc = nn.Linear(in_feats, out_features)

#     def forward(self, x: torch.Tensor) -> torch.Tensor:
#         """Forward pass through the MCQClusteringNet.

#         Args:
#             x: Input tensor of shape (B, 1, H, W), representing a batch of
#                 grayscale images.

#         Returns:
#             Output tensor of shape (B, 11), containing probability for each class and
#                 for each input sample.
#         """
#         return self.backbone(x)


# class HMESymbolicNet(nn.Module):
#     """HME Symbolic clustering architecture.

#     Current architecture: resnet34 + ProjectionHead.
#     """

#     class _ProjectionHead(nn.Module):
#         def __init__(
#             self, in_dim: int = 512, emb_dim: int = 128, num_classes: int = 229
#         ):
#             super().__init__()
#             self.projector = nn.Sequential(
#                 nn.Linear(in_dim, emb_dim),
#                 nn.ReLU(),
#                 nn.Linear(emb_dim, emb_dim),
#             )
#             self.classifier = nn.Linear(emb_dim, num_classes)
#             nn.init.normal_(self.classifier.weight, std=0.01)
#             nn.init.constant_(self.classifier.bias, 0)

#         def forward(self, features: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
#             emb = self.projector(features)
#             logits = self.classifier(emb)
#             return emb, logits

#     def __init__(self, out_classes: int = 229):
#         super().__init__()
#         # resnet34 backbone
#         backbone = models.resnet34(models.ResNet34_Weights.DEFAULT)
#         backbone.conv1 = nn.Conv2d(
#             1, 64, kernel_size=7, stride=2, padding=3, bias=False
#         )
#         backbone.fc = nn.Identity()
#         self.backbone = backbone

#         # projection head
#         self.head = self._ProjectionHead(
#             in_dim=512, emb_dim=128, num_classes=out_classes
#         )

#     def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
#         """Forward pass through the HMESymbolicNet.

#         Args:
#             x: Input tensor of shape (B, 1, H, W), representing a batch of
#                 grayscale images.

#         Returns:
#             Output tensor of shape (B, out_classes), containing probability for each class and
#             for each input sample.
#         """
#         features = self.backbone(x)
#         return self.head(features)
