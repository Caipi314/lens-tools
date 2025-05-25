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


try:
    KoalaGui.turnLive(False)
    host = KoalaController()
    host.setup()
    host.setMinH(18_000)
    # host.move_to(x=58028, y=51034, z=1267.6)  # center
    xStart = 58577
    host.move_to(x=xStart, y=51034, z=1277)  # some slant (close to center)
    # host.find_focus(guessHeight_mm=18, direction=-1)
    cont = host.getContrast(avg=5)
    print(f"START Contrast is {cont:.2f}")
    time.sleep(3)

    # host.move_to(x=xStart + 7200, z=2112.6)
    start = time.time()
    scan = Scan()
    host.loadScan(scan)
    host.traverse(x=10_000, step=1_000)

    cont = host.getContrast(avg=5)
    print(f"FINAL Contrast is {cont:.2f}")
    end = time.time()
    print(f"Time to traverse 10mm: {end - start:.3f} seconds")

    # print(plane)

    # utils.plot3D(phase, pxSize, plane)
    # display2dArray(phase, pxSize)

except Exception as err:
    print(err)
finally:
    host.logout()
    if host.scan:
        host.scan.viewXZPlane(view=True)
    KoalaGui.turnLive(True)
