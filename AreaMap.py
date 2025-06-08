from datetime import datetime
import json
from pathlib import Path
import threading
from skimage.registration import phase_cross_correlation

from matplotlib import pyplot as plt
import numpy as np
from Row import Row
from Traversal import BadFit
import utils


class AreaMap:
    yOverlap = 25  # ? Could do the max number of nans on the pic below it
    overlapVec = np.array((yOverlap, 0))
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
        self.centerRow = None
        self.done = False
        self.moveDir = -1  # go up first (-1) then down (1) each time from center
        self.stepY = (self.picShape[0] - AreaMap.yOverlap) * self.pxSize
        self.stitch = None
        self.topPt = None  # top left corner of the top center pic
        self.botPt = None  # bot left corder of the bot center pic

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
            and self.centerRow is not None
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
        """takes 2 pictures. One is the last row's center pic, and a the other is the pic of the current row's center, and gets the shift to stitch pic2 ON TOP of pic1."""
        # if currentPic.
        stitchUp = self.moveDir == -1
        if stitchUp == -1:
            pic1, pic2 = lastPic, currentPic
        else:
            pic1, pic2 = currentPic, lastPic
        f1Area = pic1[: AreaMap.yOverlap, :]
        f2Area = pic2[-AreaMap.yOverlap :, :]

        shift = phase_cross_correlation(f1Area, f2Area)[0].astype(int)

        if abs(shift[1]) > AreaMap.acceptableDx:
            print(f"Fit not acceptable (dx={shift[1]}), trying again")
            raise BadFit

        zDiff = utils.getZDiff(shift, f1Area, f2Area)
        return shift, zDiff

    def stitchUp(self, row: Row):
        row.stitch += row.zDiff

        stitchPt = self.topPt + AreaMap.overlapVec + row.shift
        rowPt = row.centerPt + (row.picShape[0], 0)
        self.stitch, stitchShift, picShift = utils.ptToPtStitch(
            self.stitch, stitchPt, row.stitch, rowPt
        )
        self.topPt += stitchShift
        self.botPt += stitchShift

    def stitchDown(self, row: Row):
        row.stitch -= row.zDiff

        stitchPt = self.botPt + (self.picShape[0], 0) - AreaMap.overlapVec + row.shift
        rowPt = row.centerPt
        self.stitch, stitchShift, picShift = utils.ptToPtStitch(
            self.stitch, stitchPt, row.stitch, rowPt
        )
        self.topPt += stitchShift
        self.botPt += stitchShift

    def addToStitch(self, row):
        stitchUp = self.moveDir == -1
        if self.stitch is None:
            self.stitch = row.stitch.copy()
            self.topPt = row.centerPt.copy()
            self.botPt = row.centerPt.copy()
            return
        thread = threading.Thread(
            target=self.stitchUp if stitchUp else self.stitchDown,
            args=(row,),  # need trailing comma
        )
        thread.start()

    def saveImages(self):
        """Saves .npy array and png image of the stitch and profile"""
        # TODO what if isProfile = False

        stitch = self.stitch if self.stitch is not None else self.centerRow.stitch
        profile = np.nanmean(self.centerRow.stitch, axis=0)

        np.save(str(self.absFolderPath / "stitch.npy"), stitch)
        np.save(str(self.absFolderPath / "profile.npy"), profile)

        stitch = np.nan_to_num(stitch, nan=0)
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
