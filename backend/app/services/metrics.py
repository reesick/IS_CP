import math
import numpy as np
from PIL import Image
from skimage.metrics import structural_similarity

def measure(clean, protected, epsilon):
    a = np.asarray(Image.open(clean).convert('RGB'),dtype=np.float64)/255
    b = np.asarray(Image.open(protected).convert('RGB'),dtype=np.float64)/255
    if a.shape != b.shape:
        raise ValueError('Output dimensions changed')
    delta = np.abs(a-b)
    mse = float(np.mean((a-b)**2))
    psnr = 10*math.log10(1/mse) if mse else None
    ssim = float(structural_similarity(a,b,data_range=1,channel_axis=2))
    maxdiff = float(delta.max())
    passed = bool(mse > 0 and (psnr is not None and psnr >= 35) and ssim >= .98 and maxdiff <= epsilon+1/255+1e-8)
    return dict(psnr_db=psnr,ssim=ssim,max_absolute_difference=maxdiff,mean_absolute_difference=float(delta.mean()),epsilon=epsilon,rounding_tolerance=1/255,gate='passed' if passed else 'failed',human_review='pending')
