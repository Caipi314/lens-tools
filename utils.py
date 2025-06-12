import numpy as np
import pathlib
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
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

    a1 = f1Area[ySlice1, xSlice1]
    a2 = f2Area[ySlice2, xSlice2]

    trim_percent = 40
    diff = a1 - a2
    lower = np.percentile(diff, trim_percent)
    upper = np.percentile(diff, 100 - trim_percent)
    trimmed = diff[(diff >= lower) & (diff <= upper)]
    zDiff = np.mean(trimmed)

    print(f"Stitch has dx={dx}, dy={dy}, zDiff={zDiff:.2f}")
    return zDiff


def save1(pic, cmap="jet"):
    pic = np.nan_to_num(pic, nan=1)
    plt.imsave("./datas/pic1.png", pic, cmap=cmap)


def save2(pic, cmap="jet"):
    pic = np.nan_to_num(pic, nan=1)
    plt.imsave("./datas/pic2.png", pic, cmap=cmap)


def ptToPtStitch(pic1, pt1, pic2, pt2=np.array((0, 0))):
    """Stitch pic2 onto pic1 so that pic2[pt2] lands at pic1[pt1], averaging any overlap, persisting Nans."""
    y, x = pt1 - pt2

    h1, w1 = pic1.shape
    h2, w2 = pic2.shape

    # output dimensions
    top = min(0, y)
    left = min(0, x)
    bottom = max(h1, h2 + y)
    right = max(w1, w2 + x)

    out_h = bottom - top
    out_w = right - left

    # create accumulators
    pic1Canvas = np.zeros((out_h, out_w))
    pic2Canvas = np.zeros((out_h, out_w))
    pic1Weight = np.zeros((out_h, out_w))
    pic2Weight = np.zeros((out_h, out_w))

    # paste pic1
    r1 = -top
    c1 = -left
    p1Rows = slice(r1, r1 + h1)
    p1Cols = slice(c1, c1 + w1)
    p1NonNan = ~np.isnan(pic1)
    pic1Canvas[p1Rows, p1Cols][p1NonNan] = pic1[p1NonNan]
    pic1Weight[p1Rows, p1Cols][p1NonNan] = 1

    # paste pic2
    r2 = y - top
    c2 = x - left
    p2Rows = slice(r2, r2 + h2)
    p2Cols = slice(c2, c2 + w2)
    p2NonNan = ~np.isnan(pic2)
    pic2Canvas[p2Rows, p2Cols][p2NonNan] = pic2[p2NonNan]
    pic2Weight[p2Rows, p2Cols][p2NonNan] = 1

    # * Alpha-blend the overlap
    try:
        # Get the bounds of the overlap
        rows, cols = np.argwhere(pic1Weight + pic2Weight == 2).T
        yMin, xMin = rows.min(), cols.min()  # Top-left corner
        yMax, xMax = rows.max() + 1, cols.max() + 1  # Bottom-right corner
        overlapH = yMax - yMin
        overlapW = xMax - xMin

        validOverlap = np.logical_and(
            pic1Weight[yMin:yMax, xMin:xMax] != 0, pic2Weight[yMin:yMax, xMin:xMax] != 0
        )
        if overlapW > overlapH:  # x stitch
            start, end = (1, 0) if c2 > c1 else (0, 1)
            x = np.linspace(start, end, overlapW)
            # smoother smoothing than just linear
            xCurve = np.square(np.cos(np.pi * x / 2))
            X = np.tile(xCurve, (overlapH, 1))
            pic1Weight[yMin:yMax, xMin:xMax][validOverlap] = (1 - X)[validOverlap]
            pic2Weight[yMin:yMax, xMin:xMax][validOverlap] = X[validOverlap]
        else:  # y stitch
            start, end = (1, 0) if r2 > r1 else (0, 1)
            y = np.linspace(start, end, overlapH)
            yCurve = np.square(np.cos(np.pi * y / 2))
            Y = np.tile(yCurve[:, np.newaxis], (1, overlapW))
            pic1Weight[yMin:yMax, xMin:xMax][validOverlap] = (1 - Y)[validOverlap]
            pic2Weight[yMin:yMax, xMin:xMax][validOverlap] = Y[validOverlap]
    except ValueError as err:
        print(err)
        print("could not complete alpha-blending because no overlap")

    acc = pic1Canvas * pic1Weight + pic2Canvas * pic2Weight
    #! Very important that Nans persist. Lest they become part of the "valid square"
    acc[(pic1Weight == 0) & (pic2Weight == 0)] = np.nan
    return acc, np.array((r1, c1)), np.array((r2, c2))
