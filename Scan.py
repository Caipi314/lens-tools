from matplotlib import pyplot as plt


class Scan:
    def __init__(self):
        self.points = []  # contains (x, y, z contrast)
        self.contrastSearches = []
        self.directionSearches = []

    def logContrast(self, x, y, z, contrast):
        self.points.append({"x": x, "y": y, "z": z, "cont": contrast})

    def logContrastSearch(self, x, y, z_start, z_end, z_maxCont, contrasts):
        points = [{"z": z, "cont": cont} for (cont, z) in contrasts]
        self.contrastSearches.append(
            {
                "x": x,
                "y": y,
                "z_start": z_start,
                "z_end": z_end,
                "z_maxCont": z_maxCont,
                "points": points,  # each points should have {z, contrast}
            }
        )

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

    def viewXZPlane(self, view=True):
        plt.figure()

        # plot the simple contrast only points
        x = [point["x"] for point in self.points]
        z = [point["z"] for point in self.points]
        cont = [point["cont"] for point in self.points]
        plt.scatter(x, z, s=40, c=cont, cmap="jet", edgecolors="black")
        plt.colorbar(label="Color Axis (Contrast)")

        # plot the direction search points
        for search in self.directionSearches:
            x = [search["x"]] * len(search["points"])
            z = [point["z"] for point in search["points"]]
            cont = [point["cont"] for point in search["points"]]
            plt.scatter(
                x[0],
                search["z_start"],
                marker="_",
                s=60,
            )
            plt.scatter(
                x,
                z,
                marker="v" if search["maxContDirection"] == 1 else "^",
                s=45,
                color="black",
            )
            for point in search["points"]:
                plt.text(
                    x[0],
                    point["z"],
                    f"contrast: {point['cont']:.2f} ",
                    fontsize=12,
                    ha="right",
                    va="center",
                )

        plt.xlabel("X-axis")
        plt.ylabel("Z-axis")
        plt.gca().invert_yaxis()
        plt.title("Scan")
        plt.grid(True)

        plt.savefig("./datas/latestScan.png")
        if view:
            plt.show()
        plt.close()
