import traceback
from KoalaController import KoalaController
from Scan import Scan
import KoalaGui
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


def focus():
    host.find_focus(guessHeight=7_000, direction=1)


def traverse():
    host.setMinH(7_000)
    host.move_to(x=62650, y=52513, z=13576.2)  # some slant (close to center)
    host.traverse(x=10_000, step=1000)


def traverseToTop():
    host.setMinH(7_000)
    host.move_to(x=62650, y=52513, z=13576.2)  # some slant (close to center)
    host.traverseToTop()


try:
    KoalaGui.turnLive(False)
    host = KoalaController()
    host.setup()
    host.loadScan(Scan(live=True))

    start = time.time()
    host.find_focus(guessHeight=7_500, direction=-1)
    host.traverseToTop()
    # focus()
    # traverse()
    # traverseToTop()
    end = time.time()
    print(f"Time: {end - start:.3f} seconds")

except Exception as err:
    traceback.print_exc()
finally:
    host.logout()
    if host.scan:
        host.scan.viewXZPlane(hold=True)
    KoalaGui.turnLive(True)
