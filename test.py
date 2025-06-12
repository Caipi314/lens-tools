import json
import struct
from matplotlib import gridspec
from scipy.ndimage import gaussian_filter
import scipy.optimize as opt
import pathlib
import matplotlib.pyplot as plt
import numpy as np
import time


def plot3D(phase, pxSize, plane):
    a, b, c = plane

    ny, nx = phase.shape
    X, Y = np.meshgrid(np.linspace(0, nx * pxSize, nx), np.linspace(0, ny * pxSize, ny))

    plane_Z = a * X + b * Y + c

    # Create 3D plot
    fig = plt.figure()
    ax = fig.add_subplot(111, projection="3d")

    # Plot height data
    ax.plot_surface(X, Y, phase, cmap="jet", alpha=0.7)

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


def compareXStitch():
    phaseK, pxSize = load_phase_file("./datas/10mmDiamKoala.bin")

    # print(phaseK)
    # plt.imsave("./datas/pic1.png", phaseK, cmap="jet")
    profileK = np.nanmean(phaseK, axis=0)
    phaseCai = np.load("./stitches/2025-06-10T150720/profile.npy")
    profileCai = np.nanmean(phaseCai, axis=0)

    smothedCai = gaussian_filter(profileCai, sigma=5)
    smothedK = gaussian_filter(profileK, sigma=5)

    profileCai -= np.max(smothedCai)
    profileK -= np.max(smothedK)

    maxOfCai = np.argmax(smothedCai)
    maxOfK = np.argmax(smothedK)

    if maxOfCai > maxOfK:
        profileCai = profileCai[maxOfCai - maxOfK :]
    elif maxOfCai < maxOfK:
        profileK = profileK[maxOfK - maxOfCai :]

    fig, ax = plt.subplots(nrows=2, ncols=1)
    ax[0].plot(profileK)
    ax[0].plot(profileCai)
    ax[0].legend(["Koala", "Cai"])
    ax[1].plot(profileK[: len(profileCai)] - profileCai)
    plt.savefig("./datas/10mmDiamKoalaVsCai.png")


def compareYStitch():
    phaseK, pxSize = load_phase_file("./datas/2mmYDiamKoala.bin")

    # print(phaseK)
    # plt.imsave("./datas/pic1.png", phaseK, cmap="jet")
    profileK = np.nanmean(phaseK, axis=1)
    phaseCai = np.load("./stitches/2025-06-10T151810/stitch.npy")
    profileCai = np.nanmean(phaseCai, axis=1)

    smothedCai = gaussian_filter(profileCai, sigma=5)
    smothedK = gaussian_filter(profileK, sigma=5)

    profileCai -= np.max(smothedCai)
    profileK -= np.max(smothedK)

    maxOfCai = np.argmax(smothedCai)
    maxOfK = np.argmax(smothedK)

    if maxOfCai > maxOfK:
        profileCai = profileCai[maxOfCai - maxOfK :]
    elif maxOfCai < maxOfK:
        profileK = profileK[maxOfK - maxOfCai :]

    fig, ax = plt.subplots(nrows=2, ncols=1)
    ax[0].plot(profileK)
    ax[0].plot(profileCai)
    ax[0].legend(["Koala", "Cai"])
    ax[1].plot(profileK[: len(profileCai)] - profileCai)
    plt.savefig("./datas/2mmYDiamKoalaVsCai.png")


# compareXStitch()
# compareYStitch()
