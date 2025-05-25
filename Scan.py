from matplotlib import pyplot as plt
from matplotlib.ticker import FuncFormatter
from matplotlib.markers import MarkerStyle
import numpy as np

import MaxContSearch


class Scan:
    def __init__(self, live):
        self.texts = []
        self.contPoints = []  # contains (x, y, z contrast)
        self.maxContSearches = []
        self.directionSearches = []
        if live:
            self.setupGraph()

    def setupGraph(self):
        plt.ion()
        self.fig, self.ax = plt.subplots(figsize=(10, 6))
        self.norm = plt.Normalize(vmin=0, vmax=10)
        self.contSc = self.ax.scatter(
            [],
            [],
            c=[],
            norm=self.norm,
            cmap="jet",
            marker="o",
            s=40,
            edgecolors="black",
        )
        self.dirSearchSc1 = self.ax.scatter([], [], marker="_", s=60)
        self.dirSearchSc2 = self.ax.scatter(
            [], [], c=[], norm=self.norm, cmap="jet", marker="o", s=30
        )
        # start and end points
        self.maxContSearchSc1 = self.ax.scatter([], [], marker="_", s=100)
        # contrast points
        self.maxContSearchSc2 = self.ax.scatter(
            [], [], c=[], norm=self.norm, cmap="jet", marker=".", s=50
        )

        self.cbar = self.fig.colorbar(self.contSc, ax=self.ax)
        self.cbar.set_label("Contrast")

        to_mm = FuncFormatter(lambda x, pos: f"{x/1000:.2f}")
        self.ax.xaxis.set_major_formatter(to_mm)
        self.ax.yaxis.set_major_formatter(to_mm)

        self.ax.set_autoscale_on(True)
        self.ax.set_xlabel("X-axis [mm]")
        self.ax.set_ylabel("Z-axis [mm]")
        self.ax.invert_yaxis()
        self.ax.set_title("Scan")
        self.ax.grid(True)
        plt.tight_layout()

    def updateContPts(self):
        x = [point["x"] for point in self.contPoints]
        z = [point["z"] for point in self.contPoints]
        cont = [point["cont"] for point in self.contPoints]

        self.contSc.set_offsets(np.column_stack((x, z)))
        self.contSc.set_array(cont)

        # add contrast value next to each point)
        for xi, zi, ci in zip(x, z, cont):
            txt = self.ax.annotate(
                f"{ci:.2f}",
                (xi, zi),
                textcoords="offset points",
                xytext=(3, 3),
                fontsize=8,
            )
            self.texts.append(txt)

    def updateDirSearchPts(self):
        startPts = []  # contains (x, z)
        contPts = []  # contains (x, z)
        contOfPts = []  # matches with contPts. contains contrasts
        for search in self.directionSearches:
            startPts.append((search["x"], search["z_start"]))
            for point in search["points"]:
                contPts.append((search["x"], point["z"]))
                contOfPts.append(point["cont"])

        self.dirSearchSc1.set_offsets(np.array(startPts))
        self.dirSearchSc2.set_offsets(np.array(contPts))
        self.dirSearchSc2.set_array(contOfPts)

        # add contrast value next to each point
        for pt, ci in zip(contPts, contOfPts):
            txt = self.ax.annotate(
                f"{ci:.2f}",
                pt,
                textcoords="offset points",
                xytext=(3, 3),
                fontsize=6,
            )
            self.texts.append(txt)

    def updateMaxContSearchPts(self):
        endPts = []  # contains (x, z)
        contPts = []  # contains (x, z)
        contOfPts = []  # matches with contPts. contains contrasts
        for search in self.maxContSearches:
            endPts.append((search.x, search.z_1))
            endPts.append((search.x, search.z_2))
            for point in search.contPts:
                if point == (0, 0):
                    continue
                contPts.append((search.x, point[1]))
                contOfPts.append(point[0])

        self.maxContSearchSc1.set_offsets(np.array(endPts))
        self.maxContSearchSc2.set_offsets(np.array(contPts))
        self.maxContSearchSc2.set_array(contOfPts)

        # add contrast value next to each point
        for pt, ci in zip(contPts, contOfPts):
            txt = self.ax.annotate(
                f"{ci:.2f}",
                pt,
                textcoords="offset points",
                xytext=(3, 0),
                fontsize=6,
            )
            self.texts.append(txt)

    def updateViewLimits(self):
        for plot in [self.contSc, self.dirSearchSc2, self.maxContSearchSc2]:
            self.ax.update_datalim(plot.get_datalim(self.ax.transData))
        self.ax.autoscale_view()

    def updateGraph(self):
        # remove old annotations
        [txt.remove() for txt in self.texts]
        self.texts.clear()

        if len(self.contPoints):
            self.updateContPts()
        if len(self.directionSearches):
            self.updateDirSearchPts()
        if len(self.maxContSearches):
            self.updateMaxContSearchPts()

        self.updateViewLimits()

        self.fig.canvas.draw()
        self.fig.canvas.flush_events()
        plt.pause(0.05)

    def logContrast(self, x, y, z, contrast):
        self.contPoints.append({"x": x, "y": y, "z": z, "cont": contrast})
        self.updateGraph()

    def startLogMaxContSearch(self, search: MaxContSearch):
        self.maxContSearches.append(search)

    def logDirectionSearch(self, x, y, z_start, maxContDirection, contrasts):
        # contrasts is a dict where key is z relative to z_start, and value is contrast
        points = [{"z": z_start + dz, "cont": cont} for dz, cont in contrasts.items()]
        self.directionSearches.append(
            {
                "x": x,
                "y": y,
                "z_start": z_start,
                "maxContDirection": maxContDirection,
                "points": points,  # each points should have {z, contrast}
            }
        )
        self.updateGraph()

    def viewXZPlane(self, hold=True):
        plt.savefig("./datas/latestScan.png")
        plt.ioff()
        if hold:
            print("holding graph open")
            plt.show()
        plt.close()
