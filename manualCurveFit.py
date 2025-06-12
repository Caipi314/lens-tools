import json

import numpy as np

from AreaMap import AreaMap

folder = "./stitches/2025-06-12T125334/"


def curveFitFromFiles():
    with open(folder + "curvature_fit.json") as f:
        data = json.load(f)
        pxSize = data["pxSize"]
        curvature = data["curvature"]
        phase = np.load(folder + "stitch_DS.npy")

    areaMap = AreaMap(False, np.array((800, 800)), 1, None, curvature)
    areaMap.saveFit(phase, pxSize)
    #! Will store the results in a new folder under the CURRENT time


curveFitFromFiles()
