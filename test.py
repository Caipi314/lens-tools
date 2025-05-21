from KoalaController import KoalaController
import utils
import time
import matplotlib.pyplot as plt
import numpy as np


def display2dArray(array):
    print(np.min(array), np.max(array))
    fig, ax = plt.subplots()
    im = ax.imshow(array, cmap="jet")  # Choose any colormap

    # Add a color bar to show the mapping of values to colors
    cbar = plt.colorbar(im)
    cbar.set_label("Color Intensity")
    plt.tight_layout()
    plt.savefig("./datas/pic.png")


try:
    host = KoalaController()
    host.setup()
    host.setMinH(7 * 1e3)
    host.move_to(x=57840, y=35134)

    host.find_focus(guessHeight_mm=7, topDown=False)

    start = time.time()
    host.traverse(x=10_000)
    end = time.time()
    print(f"Time to traverse 10mm: {end - start:.3f} seconds")

    # print(plane)

    # utils.plot3D(phase, pxSize, plane)
    # display2dArray(phase, pxSize)


finally:
    host.logout()
