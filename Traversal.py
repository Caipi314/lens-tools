from datetime import datetime
import json
import math
from pathlib import Path
import threading
import time
from matplotlib import cm, collections, patches, pyplot as plt
from matplotlib.ticker import FuncFormatter
from scipy import ndimage
from skimage.registration import phase_cross_correlation
from scipy.ndimage import zoom

import numpy as np


class BadFit(Exception):
    """Fit out of defined parameters"""

    pass


class Traversal:
    basePath = Path.cwd()
    baseName = "holo"
    baseFolder = "./stitches/"
    # overlap_px = np.array([3, 3])
    overlap_px = np.array([25, 25])

    def __init__(self, center, cont, phase, pxSize, show=True):
        self.center = center  # (x, y, z)
        self.stitch = phase
        self.picShape = np.array(phase.shape)  # (y, x) in px
        self.pxSize = pxSize  # um/px
        self.picSize_um = self.picShape * pxSize  # (y, x) in um
        self.stepY, self.stepX = self.picSize_um - Traversal.overlap_px * self.pxSize
        self.edge = None
        self.radius = None
        # start with the first pic
        self.pics = [{"pos": center, "cont": cont}]
        self.rects = []
        self.acceptableDy = Traversal.overlap_px[0]
        self.done = False
        self.profile = None  # set on done
        self.show = show

        folderName = datetime.now().strftime("%Y-%m-%dT%H%M%S")
        self.absFolderPath = Traversal.basePath / Traversal.baseFolder / folderName
        Path(str(self.absFolderPath)).mkdir(parents=True)

        self.setupGraph()
        self.updateGraph()

    def setupGraph(self):
        if not self.show:
            return
        plt.ion()
        self.fig, axes = plt.subplots(2, 1, figsize=(10, 10))
        self.ax, self.map = axes

        to_mm = FuncFormatter(lambda x, pos: f"{x/1000:.2f}")
        self.ax.xaxis.set_major_formatter(to_mm)
        self.ax.yaxis.set_major_formatter(to_mm)

        # self.ax.set_xlim(0, 100_000)
        # self.ax.set_ylim(0, 100_000)
        self.ax.set_aspect("equal")

        self.ax.set_autoscale_on(True)
        self.ax.set_xlabel("X-axis [mm]")
        self.ax.set_ylabel("Y-axis [mm]")
        self.ax.set_title("Traversal")
        self.ax.grid(True)
        plt.tight_layout()

    def updateViewLimits(self):
        for pic in self.pics:
            x, y = pic["pos"][:2]
            h, w = self.picSize_um
            self.ax.update_datalim([[x, y], [x + w, y + h]])

        self.ax.set_aspect("equal")
        self.ax.relim()
        self.ax.autoscale_view()

    def updateGraph(self):
        if not self.show:
            return
        # redraw the squares
        [rect.remove() for rect in self.rects]
        self.rects.clear()

        cmap = cm.get_cmap("jet")  # Choose a colormap
        norm = plt.Normalize(vmin=0, vmax=10)

        for pic in self.pics:
            rect = patches.Rectangle(
                xy=pic["pos"][:2],
                height=self.picSize_um[0],
                width=self.picSize_um[1],
                edgecolor="black",
                facecolor=cmap(norm(pic["cont"])),
            )

            self.ax.add_patch(rect)
            self.rects.append(rect)

        self.updateViewLimits()

        # redraw the map
        self.map.clear()
        step = math.ceil(math.prod(self.stitch.shape) / (800 * 800 * 5))
        stitch_downsampled = self.stitch[::step, ::step]
        self.map.imshow(
            stitch_downsampled,
            cmap="prism",  # 'jet'
            rasterized=True,
            resample=False,
            interpolation="none",
        )

        self.fig.canvas.draw()
        self.fig.canvas.flush_events()
        plt.pause(0.05)

    def keepOpen(self):
        if not self.show:
            return
        plt.ioff()
        print("holding graph open")
        plt.show()

    def atEdge(self, x, y, z):
        if self.stepX > 0:
            self.edge = np.array([x - self.stepX, y, z])
            self.radius = np.linalg.norm(self.center - self.edge)
            self.stepX *= -1
            print(
                f"Radius = {self.radius:.0f} (and at most {self.radius + self.stepX:.0f}. Edge is at {self.edge}"
            )
        else:
            # clean up
            self.profile = np.nanmean(self.stitch, axis=0)
            #! Should be replacing Nan based on closes valid pixrel
            self.stitch = np.nan_to_num(self.stitch, nan=0)

            self.done = True

    def stitchArrays(self, pic1, pic2):
        def getTopPads():
            pic1TopPads = np.argmax(~np.isnan(pic1[:, -1]))
            pic2TopPads = np.argmax(~np.isnan(pic2[:, 0]))
            return pic1TopPads, pic2TopPads

        def getOverlapArea(p1TopPads, p2TopPads):
            # stitch pic2 to the right of pic1
            xOverlap = Traversal.overlap_px[1]
            f1Area = pic1[p1TopPads : self.picShape[0] + p1TopPads, -xOverlap:]
            f2Area = pic2[p2TopPads : self.picShape[0] + p2TopPads, :xOverlap]
            return f1Area, f2Area

        def XYOffset(f1Area, f2Area):
            """
            Pic 2 is placed to the right of pic 1
            Return (dz, dy, dx) where
            dz is height to add to pic1 to move it to pic2
            dy, dx are value to add to pic1 to move it to pic2.
            dx = 0 has pic2 starting at the expected overlap

            Not assuming that pic1 is the big one, but assuing that at at most one picture is already padded
            """
            (dy, dx), err, phaseDiff = phase_cross_correlation(f1Area, f2Area)
            dy, dx = int(dy), int(dx)
            return dx, dy

        def getZDiff(dx, dy, f1Area, f2Area):
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

        def padPics(pic1, pic2, dy):
            h1, h2 = pic1.shape[0], pic2.shape[0]
            pad1Top = pad2Top = 0
            if h1 > h2:
                if dy > 0:
                    pad2Top = dy
                else:
                    pad1Top = -dy
            else:
                if dy > 0:
                    pad2Top = dy
                else:
                    pad1Top = -dy

            # pad the bottom until the're equal
            h1 += pad1Top
            h2 += pad2Top
            targetH = max(h1, h2)
            pad1Bot = targetH - h1
            pad2Bot = targetH - h2
            pic1 = np.pad(
                pic1,
                ((pad1Top, pad1Bot), (0, 0)),
                mode="constant",
                constant_values=np.nan,
            )
            pic2 = np.pad(
                pic2,
                ((pad2Top, pad2Bot), (0, 0)),
                mode="constant",
                constant_values=np.nan,
            )
            return pic1, pic2

        pic1TopPads, pic2TopPads = getTopPads()
        f1Area, f2Area = getOverlapArea(pic1TopPads, pic2TopPads)
        dx, dy = XYOffset(f1Area, f2Area)
        # redo stitch if dy greater than a third of the whole image
        if abs(dy) > 20:
            print(f"Fit not acceptable (dy={dy}), trying again")
            raise BadFit

        def padAndStitch(
            self, pic1, pic2, dx, dy, f1Area, f2Area, pic1TopPads, pic2TopPads
        ):
            dz = getZDiff(dx, dy, f1Area, f2Area)
            pic2 += dz
            dy = dy + pic1TopPads - pic2TopPads
            pic1, pic2 = padPics(pic1, pic2, dy)
            xOverlap = Traversal.overlap_px[1] - dx

            # ? take mean of overlapping regions
            overlapRegion = (pic1[:, -xOverlap:] + pic2[:, :xOverlap]) / 2
            stitchPic = np.concatenate(
                (pic1[:, :-xOverlap], overlapRegion, pic2[:, xOverlap:]), axis=1
            )
            # stitchPic = np.nan_to_num(stitchPic, nan=0, copy=False)
            self.stitch = stitchPic

        thread = threading.Thread(
            target=lambda: padAndStitch(
                self, pic1, pic2, dx, dy, f1Area, f2Area, pic1TopPads, pic2TopPads
            )
        )
        thread.start()

    def addToStitch(self, pic, cont, x, y, z):
        if self.stepX > 0:
            self.stitchArrays(self.stitch, pic)
        else:
            self.stitchArrays(pic, self.stitch)

        # assumes the bottom left corner is pos of pic. No real way to know
        self.pics.append({"pos": (x, y, z), "cont": cont})
        self.updateGraph()

    def genInfo(self):
        return {
            "folderPath": str(self.absFolderPath),
            "pxSize (um per px)": self.pxSize,
            "center": list(self.center),
            "overlap": list(Traversal.overlap_px),
            "picShape_px (height, width)": list(self.picShape),
            "done": self.done,
            "numPics": len(self.pics),
            "pics": self.pics,
            "stitchFile": "stitch.npy",
            "profileFile": "profile.npy",
            "instructions": 'To recover full 2d stitch, use `stitch = np.load("./stitch.npy")`. To recover 1d profile, use `stitch = np.load("./profile.npy")`. To load this dictionary as kv pairs use `with open("info.json", "r") as f: data = json.load(f)`',
        }

    def saveImages(self):
        np.save(str(self.absFolderPath / "stitch.npy"), self.stitch)
        np.save(str(self.absFolderPath / "profile.npy"), self.profile)
        plt.figure()
        plt.imsave(str(self.absFolderPath / "stitch.png"), self.stitch, cmap="jet")

        plt.figure()
        plt.plot(self.profile)
        plt.savefig(str(self.absFolderPath / "profile.png"))
        plt.close()
        with open(str(self.absFolderPath / "info.json"), "w") as f:
            json.dump(self.genInfo(), f, indent=2, default=str)
