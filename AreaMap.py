from datetime import datetime
import scipy.optimize as opt
import json
import math
from pathlib import Path
import threading
from skimage.transform import downscale_local_mean
from skimage.registration import phase_cross_correlation

from matplotlib import colors, gridspec, pyplot as plt
import numpy as np
from GlobalSettings import GlobalSettings
from Row import Row
from Traversal import BadFit
import utils


class AreaMap:
    settings = GlobalSettings()
    yOverlap = settings.get("PIC_OVERLAP")
    overlapVec = np.array((yOverlap, 0))
    acceptableDx = 15

    basePath = Path.cwd()
    baseFolder = "./stitches/"

    def __init__(self, isProfile, picShape, pxSize, maxRadius, curvature, circle):
        self.isProfile = isProfile
        self.curvature = curvature
        self.circle = circle
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
        self.stitchDS = None
        self.downFacPxSize = None

    def nextRow(self):
        totalCenter = getattr(self.centerRow, "centerPos", None)  # could be none
        row = Row(self.circle, maxRadius=self.maxRadius, totalCenter=totalCenter)
        if self.centerRow is None:
            self.centerRow = row

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
            self.done = True

    def getShift(self, lastPic, currPic):
        """takes 2 pictures. One is the last row's center pic, and a the other is the pic of the current row's center, and gets the shift to stitch pic2 ON TOP of pic1."""
        if self.moveDir == -1:  # stitch up
            lastArea = lastPic[: AreaMap.yOverlap, :]
            currArea = currPic[-AreaMap.yOverlap :, :]
        else:  # stitch down
            lastArea = lastPic[-AreaMap.yOverlap :, :]
            currArea = currPic[: AreaMap.yOverlap, :]

        shift = phase_cross_correlation(lastArea, currArea)[0].astype(int)

        if abs(shift[1]) > AreaMap.acceptableDx:
            print(f"Fit not acceptable (dx={shift[1]}), trying again")
            raise BadFit

        zDiff = utils.getZDiff(shift, lastArea, currArea)
        return shift, zDiff

    def stitchUp(self, row: Row):
        row.stitch += row.zDiff

        stitchPt = self.topPt + AreaMap.overlapVec + row.shift
        rowPt = row.centerPt + (row.picShape[0], 0)
        self.stitch, stitchShift, picShift = utils.ptToPtStitch(
            self.stitch, stitchPt, row.stitch, rowPt
        )
        self.topPt = picShift + row.centerPt
        self.botPt += stitchShift
        self.saveImages()  # on a thread so non blocking

    def stitchDown(self, row: Row):
        row.stitch += row.zDiff

        stitchPt = self.botPt + (self.picShape[0], 0) - AreaMap.overlapVec + row.shift
        rowPt = row.centerPt
        self.stitch, stitchShift, picShift = utils.ptToPtStitch(
            self.stitch, stitchPt, row.stitch, rowPt
        )
        self.botPt = picShift + row.centerPt
        self.topPt += stitchShift
        self.saveImages()  # on a thread so non blocking

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

    def saveFit(self, phase=None, pxSize=None, curvature=None):
        if phase is None:
            phase = self.stitchDS
        if pxSize is None:
            pxSize = self.downFacPxSize
        if curvature is None:
            curvature = self.curvature
        if curvature == 0:
            return print("not saving fit. curvature == 0")
        if phase is None or pxSize is None:
            return print("Can't save fit because no DS stitch")
        print("Saving curvature_fit.png")

        x = np.linspace(0, phase.shape[1] * pxSize, phase.shape[1])
        y = np.linspace(0, phase.shape[0] * pxSize, phase.shape[0])
        X, Y = np.meshgrid(x, y)

        # mask out the NaNs
        mask = ~np.isnan(phase)
        x_flat = X[mask]
        y_flat = Y[mask]
        xy_flat = np.vstack((x_flat, y_flat))
        z_flat = phase[mask]

        def fitFunc(XY, a, b, c, R):
            x, y = XY
            circ = np.square(x - a) + np.square(y - b)
            bot = R + np.sqrt(R**2 - circ)
            return c - curvature * circ / bot

        guess = (
            phase.shape[1] * pxSize / 2,
            phase.shape[0] * pxSize / 2,
            0,
            0.1e6,
        )

        popt, pcov = opt.curve_fit(fitFunc, xy_flat, z_flat, p0=guess)
        uncert = np.sqrt(np.diag(pcov))

        fig = plt.figure(figsize=(10, 10))
        fig.suptitle("Fit to Conic Section", fontsize=16)

        fig.text(
            0,
            0.93,
            s=f"center (from top left) (a,b,c)=({popt[0]:.0f}, {popt[1]:.0f}, {popt[2]:.2e}) [um]",
        )
        fig.text(
            0,
            0.91,
            s=f"R_curvature=({popt[3]/1e6:.3e} ± {uncert[3]/1e6:.3e}) [m]",
        )
        fig.text(
            0.5,
            0.93,
            s=f"Z = ((x-a)^2 + (y-b)^2)/(R + √(R^2 - (x-a)^2 - (y-b)^2))",
        )
        gs = gridspec.GridSpec(2, 2)
        ax1 = fig.add_subplot(gs[0, 0])
        ax2 = fig.add_subplot(gs[0, 1])
        ax3 = fig.add_subplot(gs[1, :])

        ax1.set_title("Original phase [um]")
        im1 = ax1.imshow(phase, cmap="jet")
        fig.colorbar(im1, ax=ax1, fraction=0.046, pad=0.04)

        ax2.set_title("Fitted phase [um]")
        fitted = fitFunc((X, Y), *popt)
        im2 = ax2.imshow(fitted, cmap="jet")
        fig.colorbar(im2, ax=ax2, fraction=0.046, pad=0.04)

        ax3.set_title("Residuals [um]")
        resids = phase - fitted
        norm = colors.TwoSlopeNorm(vmin=resids.min(), vcenter=0, vmax=resids.max())
        im3 = ax3.imshow(resids, norm=norm, cmap="seismic")

        fig.colorbar(im3, ax=ax3, fraction=0.046, pad=0.04)

        path = str(self.absFolderPath / "curvature_fit.png")
        fig.savefig(path)

        with open(str(self.absFolderPath / "curvature_fit.json"), "w") as f:
            json.dump(
                {
                    "pxSize": pxSize,
                    "phase shape": phase.shape,
                    "curvature": self.curvature,
                    "fitFunc": "Z = ((x-a)^2 + (y-b)^2)/(R + √(R^2 - (x-a)^2 - (y-b)^2))",
                    "fit variable names": ("a", "b", "c", "R"),
                    "fit variables [um]": popt,
                    "fit variable uncertainty [um]": uncert,
                    "phaseFile": "stitch_DS.npy",
                },
                f,
                indent=2,
                default=str,
            )

    def saveImages(self):
        """Saves .npy array and png image of the stitch and profile"""

        stitch = self.stitch if self.stitch is not None else self.centerRow.stitch
        profile = self.centerRow.stitch
        np.save(str(self.absFolderPath / "profile.npy"), profile)

        # limit stitch size under 100mb
        stitchSize = np.prod(stitch.shape) * np.dtype(stitch.dtype).itemsize / (1024**2)
        downFac = max(1, math.floor(stitchSize / 100))
        self.downFacPxSize = self.pxSize * downFac
        self.stitchDS = downscale_local_mean(stitch, (downFac, downFac))
        np.save(str(self.absFolderPath / "stitch_DS.npy"), self.stitchDS)

        stitchNoNan = np.nan_to_num(self.stitchDS, nan=np.nanmin(stitch))
        plt.imsave(str(self.absFolderPath / "stitch_DS.png"), stitchNoNan, cmap="jet")

        with open(str(self.absFolderPath / "info.json"), "w") as f:
            json.dump(
                {
                    "folderPath": str(self.absFolderPath),
                    "isProfile": self.isProfile,
                    "numRows": len(self.rows),
                    "profilePxSize": self.pxSize,
                    "stitchDSPxSize": self.downFacPxSize,
                    "stitchFile": "stitch_DS.npy",
                    "profileFile": "profile.npy",
                    "instructions": 'To recover .npy file into a np array use `stitch = np.load("./stitch.npy")`. To load this dictionary as kv pairs use `with open("info.json", "r") as f: data = json.load(f)`',
                },
                f,
                indent=2,
                default=str,
            )
