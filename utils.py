import numpy as np
import pathlib
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from scipy.ndimage import gaussian_filter
import struct


def fit_plane(phase, pxSize):
    """Receives a numpy grid of heights and returns the slope in x and y"""
    # Down sample by 10. (Take every 10th point)
    step = 10
    ny, nx = phase.shape
    phase_ds = phase[::step, ::step]  # down sampled

    # [px] * [um/px]
    Y_sub, X_sub = np.mgrid[0:ny:step, 0:nx:step] * pxSize
    A = np.column_stack((X_sub.ravel(), Y_sub.ravel(), np.ones(phase_ds.size)))

    # A [um] * x [.] = phase [um]
    x, *_ = np.linalg.lstsq(A, phase_ds.ravel(), rcond=None)
    a, b, c = x

    # a = dz/dx [um/um]    b = dz/dy [um/um]    c = height at (x=0, y=0) [um]
    return a, b, c


def getZDiff(dx, dy, f1Area, f2Area):
    """Takes 2 overlaped reigons and the 2nd area's relative offset, and returns the difference in their means of their overlapped regions"""
    # make sure we're averaging over the same part
    ySlice1 = ySlice2 = xSlice1 = xSlice2 = slice(None)
    if dx > 0:
        xSlice1, xSlice2 = slice(dx, None), slice(None, -dx)
    elif dx < 0:
        xSlice1, xSlice2 = slice(None, dx), slice(-dx, None)
    if dy > 0:
        ySlice1, ySlice2 = slice(dy, None), slice(None, -dy)
    elif dy < 0:
        ySlice1, ySlice2 = slice(None, dy), slice(-dy, None)

    zDiff = np.mean(f1Area[ySlice1, xSlice1] - f2Area[ySlice2, xSlice2])

    print(f"Stitch has dx={dx}, dy={dy}, zDiff={zDiff:.2f}")
    return zDiff
