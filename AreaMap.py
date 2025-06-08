from datetime import datetime
import json
from pathlib import Path
from skimage.registration import phase_cross_correlation

from matplotlib import pyplot as plt
import numpy as np
from Row import Row
from Traversal import BadFit


class AreaMap:
    yOverlap = 25  # ? Could do the max number of nans on the pic below it
    acceptableDx = 15

    basePath = Path.cwd()
    baseFolder = "./stitches/"

    def __init__(self, isProfile, picShape, pxSize, maxRadius=None):
        # picShape and pxSize are only used if isProfile is False
        self.isProfile = isProfile
        self.maxRadius = maxRadius
        self.picShape = picShape  # (height, width)
        self.pxSize = pxSize
        self.rows = []
        self.done = False
        self.moveDir = -1  # go up first (-1) then down (1) each time from center
        self.stepY = (self.picShape[0] - AreaMap.yOverlap) * self.pxSize

        folderName = datetime.now().strftime("%Y-%m-%dT%H%M%S")
        self.absFolderPath = AreaMap.basePath / AreaMap.baseFolder / folderName
        Path(str(self.absFolderPath)).mkdir(parents=True)

    def nextRow(self):
        # TODO fancier logic than just constant maxRadius for all
        row = Row(maxRadius=self.maxRadius)
        if len(self.rows) == 0:
            self.centerRow = row

        if self.moveDir == -1:
            self.rows.insert(0, row)
        else:
            self.rows.append(row)
        return row

    def prematureEdge(self, y):
        return (
            self.maxRadius
            and self.centerRow
            and abs(y - self.centerRow.centerPos[1]) > self.maxRadius
        )

    def atEdge(self, x, y, z):
        if self.moveDir == -1:
            self.edge = np.array([x, y - self.stepY, z])
            self.moveDir = 1
            print(f"Y Edge is at {self.edge}")
        else:
            # TODO Stitch together the rows
            # self.stitch = np.nan_to_num(self.stitch, nan=0)
            self.done = True

    def getShift(self, lastPic, currentPic):
        def getZDiff(dx, dy, f1Area, f2Area):
            """Used in stitchX to see required constant offset to add to pic2"""
            # make sure we're averaging over the same part
            ySlice1 = ySlice2 = xSlice1 = xSlice2 = slice(None)
            if dx > 0:
                xSlice1, xSlice2 = slice(dx, None), slice(None, -dx)
            elif dx < 0:
                xSlice1, xSlice2 = slice(None, dx), slice(-dx, None)
            if dy > 0:
                ySlice1, ySlice2 = slice(dy, None), slice(None, -dy)
            elif dy < 0:
                ySlice1, ySlice2 = slice(None, dy), slice(-dy, None)

            zDiff = np.mean(f1Area[ySlice1, xSlice1] - f2Area[ySlice2, xSlice2])

            print(f"Stitch has dx={dx}, dy={dy}, zDiff={zDiff:.2f}")
            return zDiff

        """takes 2 pictures. One is the last row's center pic, and a the other is the pic of the current row's center, and gets the shift to stitch pic2 ON TOP of pic1."""
        # if currentPic.
        if self.moveDir == -1:
            pic1, pic2 = lastPic, currentPic
        else:
            pic2, pic1 = lastPic, currentPic
        f1Area = pic1[: AreaMap.yOverlap, :]
        f2Area = pic2[-AreaMap.yOverlap :, :]

        (dy, dx), err, phaseDiff = phase_cross_correlation(f1Area, f2Area)
        dy, dx = int(dy), int(dx)

        if abs(dy) > AreaMap.acceptableDx:
            print(f"Fit not acceptable (dx={dx}), trying again")
            raise BadFit

        zDiff = getZDiff(dx, dy, f1Area, f2Area)
        print(f"Shift between rows is dx={dx} dy={dy}. zDiff={zDiff}")
        return (dy, dx), zDiff

    def saveImages(self):
        """Saves .npy array and png image of the stitch and profile"""
        # TODO what if isProfile = False

        stitch = self.rows[0].stitch
        profile = np.nanmean(stitch, axis=0)

        np.save(str(self.absFolderPath / "stitch.npy"), stitch)
        np.save(str(self.absFolderPath / "profile.npy"), profile)
        plt.imsave(str(self.absFolderPath / "stitch.png"), stitch, cmap="jet")

        fig, ax = plt.subplots()
        ax.plot(profile)
        fig.savefig(str(self.absFolderPath / "profile.png"))

        with open(str(self.absFolderPath / "info.json"), "w") as f:
            json.dump(
                {
                    "folderPath": str(self.absFolderPath),
                    "isProfile": self.isProfile,
                    "numRows": len(self.rows),
                    "stitchFile": "stitch.npy",
                    "profileFile": "profile.npy",
                    "instructions": 'To recover full 2d stitch, use `stitch = np.load("./stitch.npy")`. To recover 1d profile, use `stitch = np.load("./profile.npy")`. To load this dictionary as kv pairs use `with open("info.json", "r") as f: data = json.load(f)`',
                },
                f,
                indent=2,
                default=str,
            )
