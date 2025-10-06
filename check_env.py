import cv2, torch, numpy as np
print("OpenCV:", cv2.__version__)
print("PyTorch:", torch.__version__)
x = torch.randn(1, 3, 64, 64)
print("Tensor OK:", x.shape, x.dtype)
print("CUDA available:", torch.cuda.is_available())
