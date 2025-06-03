from datetime import datetime
from pathlib import Path
from matplotlib import cm, collections, patches, pyplot as plt
from matplotlib.ticker import FuncFormatter
from skimage.registration import phase_cross_correlation

import numpy as np


class BadFit(Exception):
    """Fit out of defined parameters"""

    pass


class Traversal:
    basePath = Path.cwd()
    baseName = "holo"
    baseFolder = "./stitches/"
    overlap = np.array([25, 25])

    def __init__(self, center, cont, phase, picSize):
        self.center = center  # (x, y, z)
        self.stitch = phase
        self.picSize = picSize  # (y, x) in um
        self.stepY, self.stepX = picSize - Traversal.overlap
        self.edge = None
        self.radius = None
        # start with the first pic
        self.pics = [{"pos": center, "shape_um": picSize, "cont": cont}]
        self.rects = []

        folderName = datetime.now().strftime("%Y-%m-%dT%H%M%S")
        self.absFolderPath = Traversal.basePath / Traversal.baseFolder / folderName
        Path(str(self.absFolderPath)).mkdir(parents=True)

        self.setupGraph()
        self.updateGraph()

    def setupGraph(self):
        plt.ion()
        self.fig, self.ax = plt.subplots(figsize=(10, 6))
        # self.norm = plt.Normalize(vmin=0, vmax=10)
        # Create PatchCollection
        # self.collection = collections.PatchCollection([])
        # self.ax.add_collection(self.collection)

        # self.contSc = self.ax.scatter(
        #     [],
        #     [],
        #     c=[],
        #     norm=self.norm,
        #     cmap="jet",
        #     marker="o",
        #     s=40,
        #     edgecolors="black",
        # )

        # self.cbar = self.fig.colorbar(self.contSc, ax=self.ax)
        # self.cbar.set_label("Contrast")

        to_mm = FuncFormatter(lambda x, pos: f"{x/1000:.2f}")
        self.ax.xaxis.set_major_formatter(to_mm)
        self.ax.yaxis.set_major_formatter(to_mm)

        self.ax.set_xlim(0, 100_000)
        self.ax.set_ylim(0, 100_000)
        self.ax.set_aspect("equal")
        # self.ax.set_aspect("equal", adjustable="datalim")

        self.ax.set_autoscale_on(True)
        self.ax.set_xlabel("X-axis [mm]")
        self.ax.set_ylabel("Y-axis [mm]")
        self.ax.set_title("Traversal")
        self.ax.grid(True)
        plt.tight_layout()

    def updateViewLimits(self):
        for pic in self.pics:
            x, y = pic["pos"][:2]
            h, w = pic["shape_um"]
            self.ax.update_datalim([[x, y], [x + w, y + h]])

        self.ax.set_aspect("equal")
        self.ax.relim()
        self.ax.autoscale_view()

    def updateGraph(self):
        [rect.remove() for rect in self.rects]
        self.rects.clear()

        cmap = cm.get_cmap("jet")  # Choose a colormap
        norm = plt.Normalize(vmin=0, vmax=10)

        for pic in self.pics:
            rect = patches.Rectangle(
                xy=pic["pos"][:2],
                width=pic["shape_um"][1],
                height=pic["shape_um"][0],
                edgecolor="black",
                facecolor=cmap(norm(pic["cont"])),
            )

            self.ax.add_patch(rect)
            self.rects.append(rect)

        self.updateViewLimits()

        self.fig.canvas.draw()
        self.fig.canvas.flush_events()
        plt.pause(0.05)

    def keepOpen(self):
        plt.ioff()
        print("holding graph open")
        plt.show()

    def lostFocus(self, x, y, z):
        self.edge = np.array([x - self.stepX, y, z])
        self.radius = np.linalg.norm(self.center - self.edge)
        print(
            f"Radius = {self.radius:.0f} (and at most {self.radius + self.stepX:.0f}. Edge is at {self.edge}"
        )

    def stitchArrays(self, pic1, pic2):
        def stitchXYOffset(pic1, pic2, overlap):
            """
            Pic 2 is placed to the right of pic 1
            Return (dz, dy, dx) where
            dz is height to add to pic1 to move it to pic2
            dy, dx are value to add to pic1 to move it to pic2.
            dx = 0 has pic2 starting at the expected overlap
            """
            # stitch to the right (for now)
            f1Area = pic1[:, -overlap:]
            f2Area = pic2[:, :overlap]

            (dy, dx), err, phaseDiff = phase_cross_correlation(f1Area, f2Area)
            dy, dx = int(dy), int(dx)

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

            print(f"Stitch has dx={dx}, dy={dy}, zDiff={zDiff:.2f} (err={err:.2f} ??)")
            return dx, dy, zDiff

        overlap = Traversal.overlap[1]  # x overlap
        dx, dy, dz = stitchXYOffset(pic1, pic2, overlap=overlap)

        # redo stitch
        if abs(dy) > 0:
            raise BadFit

        pic2 += dz
        if dy != 0:
            padBot = max(int(dy), 0)
            padTop = max(int(-dy), 0)
            pic1 = np.pad(pic1, ((padTop, padBot), (0, 0)), mode="edge")
            pic2 = np.pad(pic2, ((padBot, padTop), (0, 0)), mode="edge")

        # ? take mean of overlapping regions
        overlapRegion = (pic1[:, -overlap + dx :] + pic2[:, : overlap - dx]) / 2
        stitchPic = np.concatenate(
            (pic1[:, : -overlap + dx], overlapRegion, pic2[:, overlap - dx :]),
            axis=1,
        )

        return stitchPic

    def addToStitch(self, pic, pxSize, cont, pos, axis):
        if axis == 1:
            self.stitch = self.stitchArrays(self.stitch, pic)

        print(self.stitch.shape)
        # plt.close()
        plt.figure()
        plt.imshow(self.stitch, cmap="jet")
        plt.savefig(str(self.absFolderPath / "topDown.png"))
        plt.close()

        plt.figure()
        plt.plot(self.stitch[100, :])
        plt.savefig(str(self.absFolderPath / "topDown.png"))
        plt.close()

        # assumes the bottom left corner is pos of pic. No real way to know
        self.pics.append(
            {
                "pos": pos,
                "shape_um": np.array(pic.shape) * pxSize,
                "cont": cont,
            }
        )
        self.updateGraph()

    # def captureCenterToEdge(self): ...
