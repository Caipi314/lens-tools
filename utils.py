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


def getZDiff(shift, f1Area, f2Area):
    dy, dx = shift
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


def ptToPtStitch(pic1, pt1, pic2, pt2=np.array((0, 0))):
    """Returns a new array that has pic2's pt2 at pt1 on pic1 with overlap averaged"""
    y, x = pt1 - pt2

    h1, w1 = pic1.shape
    h2, w2 = pic2.shape

    # output dimensions
    top = min(0, y)
    left = min(0, x)
    bottom = max(h1, y + h2)
    right = max(w1, x + w2)

    out_h = bottom - top
    out_w = right - left

    # create accumulators
    acc = np.zeros((out_h, out_w), dtype=np.float64)
    weight = np.zeros_like(acc)
    print(f"new size {acc.shape}")

    # paste pic1
    r1 = -top
    c1 = -left
    p1Rows = slice(r1, r1 + h1)
    p1Cols = slice(c1, c1 + w1)
    acc[p1Rows, p1Cols] += pic1
    weight[p1Rows, p1Cols] += 1

    # paste pic2
    r2 = y - top
    c2 = x - left
    p2Rows = slice(r2, r2 + h2)
    p2Cols = slice(c2, c2 + w2)
    acc[p2Rows, p2Cols] = np.nan_to_num(acc[p2Rows, p2Cols], nan=0)
    acc[p2Rows, p2Cols] += pic2
    weight[p2Rows, p2Cols] += 1

    # average where any image contributed
    acc[weight > 1] /= weight[weight > 1]
    acc[weight == 0] = np.nan

    return acc, np.array((r1, c1)), np.array((r2, c2))
