import asyncio
import traceback
from KoalaController import KoalaController
from Scan import Scan
import KoalaGui
import utils
import time
import matplotlib.pyplot as plt
import numpy as np

try:
    KoalaGui.turnLive(False)
    host = KoalaController()
    host.setup()

    start = time.time()
    host.setLimit(h=8_000)
    # host.move_to(58982, 56368, 13448)  # center
    # host.move_to(53921, 51042, 13658.6)  # just before the crease thing
    # host.move_to(58100.28, 51905, 13470.6)  # just before the crease thing
    # host.traverseToTop()
    # host.mapProfile(maxRadius=5_000)
    host.mapArea(curvature=-1, maxRadius=1_000)
    # host.mapArea(maxRadius=300)
    # host.mapArea(maxRadius=3_000)

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
