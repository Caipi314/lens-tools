from datetime import datetime
from pathlib import Path

import numpy as np


class Traversal:
    basePath = Path.cwd()
    baseName = "holo"
    baseFolder = "./stitches/"
    overlap = np.array([25, 25])

    def __init__(self, center, picSize):
        self.picSize = picSize  # (y, x)
        self.stepY, self.stepX = picSize - Traversal.overlap
        self.center = center
        self.edge = None
        self.radius = None
        self.picCount = 0  # first pic is taken as 1

        folderName = datetime.now().strftime("%Y-%m-%dT%H%M%S")
        self.absFolderPath = Traversal.basePath / Traversal.baseFolder / folderName
        Path(str(self.absFolderPath)).mkdir(parents=True)

    def getPicName(self):
        self.picCount += 1
        firstName = "dxPos" if self.edge == None else "dxNeg"
        return str(self.absFolderPath / f"00001_{self.picCount:05}_{firstName}.tif")
        # return str(self.absFolderPath / f"{firstName}_00001_{self.picCount:05}.tif")

    def lostFocus(self, x, y, z):
        self.edge = np.array([x - self.stepX, y, z])
        self.radius = np.linalg.norm(self.center - self.edge)
        print(
            f"Radius = {self.radius:.0f} (and at most {self.radius + self.stepX:.0f}. Edge is at {self.edge}"
        )

    # def captureCenterToEdge(self): ...
