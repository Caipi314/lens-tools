import numpy as np
import pathlib
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from scipy.ndimage import gaussian_filter
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


def load_phase_file(path=None):
    # dump the displayed phase as a .bin file
    basePath = pathlib.Path.cwd()
    if path == None:
        path = str(basePath / "./tmp/phase.bin")

    with open(path, "rb") as f:
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

    # [rad] * [m/rad] * [um/m]
    if unit == 1:  # 1 = rad, 2 = m
        phase = phase * hconv * 1e6
    return phase, pxSize_um  # [um (height)], [um/px (x and y)]


def compare():
    phaseK, pxSize = load_phase_file("./datas/10mmDiamKoala.bin")
    profileK = np.nanmean(phaseK, axis=0)
    profileCai = np.load("./stitches/2025-06-05T135030/profile.npy")

    smothedCai = gaussian_filter(profileCai, sigma=5)
    smothedK = gaussian_filter(profileK, sigma=5)

    profileCai -= np.max(smothedCai)
    profileK -= np.max(smothedK)

    maxOfCai = np.argmax(smothedCai)
    maxOfK = np.argmax(smothedK)

    if maxOfCai > maxOfK:
        maxOfCai = profileCai[maxOfCai - maxOfK :]
    elif maxOfCai < maxOfK:
        maxOfK = profileK[maxOfK - maxOfCai :]

    fig, ax = plt.subplots(nrows=2, ncols=1)
    ax[0].plot(profileK)
    ax[0].plot(profileCai)
    ax[0].legend(["Koala", "Cai"])
    ax[1].plot(profileK - profileCai[: len(profileK)])
    plt.savefig("./datas/10mmDiamKoalaVsCai.png")
    # plt.show()


if __name__ == "__main__":
    compare()


def fit_plane(phase, pxSize, returnCoefs=False):
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

    if returnCoefs:
        return a, b, c

    # a = dz/dx [um/um]    b = dz/dy [um/um]    c = height at (x=0, y=0) [um]
    def surface(x, y):
        return a * x + b * y + c

    return surface


def fit_quadratic(phase, pxSize):
    """
    Receives a numpy grid `phase` of heights and pixel size `pxSize` (um/px),
    downsamples by `step`, and returns the quadratic coefficients
      z = A x^2 + B y^2 + C x y + D x + E y + F
    as a tuple (A, B, C, D, E, F).
    """
    ny, nx = phase.shape
    step = 10

    # down-sample
    phase_ds = phase[::step, ::step]
    Y_sub, X_sub = np.mgrid[0:ny:step, 0:nx:step] * pxSize

    # flatten
    x = X_sub.ravel()
    y = Y_sub.ravel()
    z = phase_ds.ravel()

    # design matrix: [x^2, y^2, x*y, x, y, 1]
    A = np.column_stack((x**2, y**2, x * y, x, y, np.ones_like(x)))

    # solve least squares
    coeffs, *_ = np.linalg.lstsq(A, z, rcond=None)
    a, b, c, d, e, f = coeffs

    # z = A x^2 + B y^2 + C x y + D x + E y + F
    def surface(x, y):
        return a * x**2 + b * y**2 + c * x * y + d * x + e * y + f

    return surface
