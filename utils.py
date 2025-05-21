import numpy as np
import pathlib
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import struct


def plot3D(phase, pxSize, plane):
    a, b, c = plane

    ny, nx = phase.shape
    X, Y = np.meshgrid(np.linspace(0, nx * pxSize, nx), np.linspace(0, ny * pxSize, ny))

    plane_Z = a * X + b * Y + c

    # Create 3D plot
    fig = plt.figure()
    ax = fig.add_subplot(111, projection="3d")

    # Plot height data
    ax.plot_surface(X, Y, phase, cmap="viridis", alpha=0.7)

    # Plot plane
    ax.plot_surface(X, Y, plane_Z, color="red", alpha=0.3)

    # Labels
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.set_zlabel("Height")

    plt.show()


def load_phase_file():
    # dump the displayed phase as a .bin file
    basePath = pathlib.Path.cwd()
    fpath = str(basePath / "./tmp/phase.bin")

    with open(fpath, "rb") as f:
        hdr_ver, endian = struct.unpack("bb", f.read(2))
        int32 = "<i" if endian == 0 else ">i"
        float32 = "<f" if endian == 0 else ">f"
        header_size = struct.unpack(int32, f.read(4))[0]
        width = struct.unpack(int32, f.read(4))[0]
        height = struct.unpack(int32, f.read(4))[0]
        pxSize_um = struct.unpack(float32, f.read(4))[0] * 1e6
        hconv = struct.unpack(float32, f.read(4))[0]  # * metres / radian
        unit = struct.unpack("b", f.read(1))[0]
        phase = np.fromfile(f, np.float32).reshape(height, width)

        # [rad] * [m/rad] * [um/m] * z factor thing trust be bro
    if unit == 1:  # 1 = rad, 2 = m
        phase = phase * hconv * 1e5
    return phase, pxSize_um  # [um (height)], [um/px (x and y)]


def slope(phase, pxSize):
    """Receives a numpy grid of heights and returns the slope in x and y"""
    # Down sample by 10. (Take every 10th point)
    ny, nx = phase.shape
    step = 10
    phase_ds = phase[::step, ::step]  # down sampled

    # [px] * [um/px]
    Y_sub, X_sub = np.mgrid[0:ny:step, 0:nx:step] * pxSize
    A = np.column_stack((X_sub.ravel(), Y_sub.ravel(), np.ones(phase_ds.size)))

    # A [um] * x [.] = phase [um]
    x, *_ = np.linalg.lstsq(A, phase_ds.ravel(), rcond=None)
    a, b, c = x
    # z = ax + by + c
    # a = dz/dx [um/um]    b = dz/dy [um/um]    c = height at (x=0, y=0) [um]

    return (a, b, c)
