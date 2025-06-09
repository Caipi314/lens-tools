import asyncio
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
    host.setLimit(h=7_000)
    host.find_focus(direction=1)


def traverse():
    host.setLimit(h=7_000)
    host.move_to(x=62650, y=52513, z=13576.2)  # some slant (close to center)
    host.traverse(x=10_000, step=1000)


def traverseToTop():
    host.setLimit(h=7_000)
    host.move_to(x=62650, y=52513, z=13576.2)  # some slant (close to center)
    host.traverseToTop()


def ensureFocus():
    host.ensureFocus()


def testFocusing():
    focuses = []
    for i in range(100):
        host.move_to(z=1_000)
        focuses.append(host.maximizeFocus())
    print(focuses)
    1


try:
    KoalaGui.turnLive(False)
    host = KoalaController()
    host.setup()

    start = time.time()
    host.setLimit(h=20_000)
    # host.move_to(58982, 56368, 13448)  # center
    # host.move_to(53921, 51042, 13658.6)  # just before the crease thing
    # host.move_to(58100.28, 51905, 13470.6)  # just before the crease thing
    # host.traverseToTop()
    # host.mapProfile(maxRadius=5_000)
    # host.mapProfile(maxRadius=500)
    # host.mapArea(maxRadius=300)
    host.mapArea(maxRadius=500)

    # host.map2dProfile(radius=5_000)

    # center = host.traverseToTop()
    # end = host.traverseToEnd(step=1_000)

    # focus()
    # traverse()
    # traverseToTop()
    end = time.time()
    print(f"Time: {end - start:.3f} seconds")

except Exception as err:
    traceback.print_exc()
finally:
    KoalaGui.turnLive(True)
    host.logout()
    # if host.scan:
    #     host.scan.viewXZPlane(hold=False)
