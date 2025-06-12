import asyncio
import sys
from datetime import datetime
from GlobalSettings import GlobalSettings
import threading
from Graph import Graph
from AreaMap import AreaMap
from MaxContSearch import MaxContSearch
from Row import Row
from Scan import Scan
from Traversal import BadFit, Traversal
import utils
import struct
import pathlib
import numpy as np
import clr
import time

clr.AddReference("System")
import System
from System import Array

# Add reference and import KoalaRemoteClient
sys.path.append(r"C:\\Program Files\\LynceeTec\\Koala\\Remote\\Remote Libraries\\x64")
clr.AddReference("LynceeTec.KoalaRemote.Client")
from LynceeTec.KoalaRemote.Client import KoalaRemoteClient


class FocusNotFound(Exception):
    """Contrast never decreased"""

    pass


class InvalidMove(Exception):
    """Invalid move"""

    def __init__(self, z):
        msg = f"Tried to move to not allowed z={z}"
        print(msg)
        super().__init__(msg)


class KoalaController:
    def __init__(self, host="localhost", user="user", passw="user"):
        self.basePath = pathlib.Path.cwd()
        self.settings = GlobalSettings()
        self.host = KoalaRemoteClient()
        ret, username = self.host.Connect(
            host, user, True
        )  # True is deprecated but required
        self.host.Login(passw)
        self.maxZ = None
        self.scan = None
        # d_focus = Z_max - Z_focus - h_real #! calibrated dont touch now
        self.focusDist = 27175 - 13207 - (7.66 - 0.16) * 1e3
        self.ABS_MAX_H = self.settings.get("ABS_MAX_Z") - self.focusDist
        self.scan = Scan(show=False)

    def setup(self):
        """Initialize configuration and source state."""
        self.host.OpenConfig(142)  # for 20x objective
        self.host.SetSourceState(0, True, True)
        self.pxSize = self.host.GetPxSizeUm()
        self.host.SetUnwrap2DMethod(0)
        self.host.OpenPhaseWin()
        time.sleep(0.1)

    def setLimit(self, h):
        if h < 500:
            raise Exception("Please give h in um to host.setMinH(h)")
        self.maxZ = self.settings.get("ABS_MAX_Z") - h

    def getPos(self):
        buffer = System.Array.CreateInstance(System.Double, 4)
        self.host.GetAxesPosMu(buffer)
        return np.array([buffer[0], buffer[1], buffer[2] / 10])

    def hToZ(self, h):
        return self.settings.get("ABS_MAX_Z") - self.focusDist - h

    def zToH(self, z):
        if z == None:
            raise Exception(f"Cannot convert z to h when z = {z}")
        return self.settings.get("ABS_MAX_Z") - self.focusDist - z

    def move_to(self, x=0, y=0, z=0, h=0, fatal=True, fast=False):
        """MUST SET self.maxZ in order to move the Z axis"""
        # ? Fast mode does not wait for the moving to finish (according to Koala), but adds 0.4s delay. ~50% speedup for small movements
        # * give Z in joystick/real heights
        # * h is height of surface from stage.
        if h != 0:
            z = self.settings.get("ABS_MAX_Z") - h

        if z != 0:
            if self.maxZ == None:
                raise Exception("Tried to move without setting self.maxZ")
            if z < 0 or z > self.settings.get("ABS_MAX_Z") or z > self.maxZ:
                if fatal:
                    raise InvalidMove(z)
                else:
                    return False
        ok = self.host.MoveAxes(
            True,
            bool(x != 0),
            bool(y != 0),
            bool(z != 0),
            False,
            int(x),
            int(y),
            int(z * 10),
            0,
            1,
            1,
            1,
            1,
            not fast,
        )
        if fast:
            time.sleep(0.4)
        return ok

    def move_rel(self, dx=0, dy=0, dz=0, fast=False):
        # TODO should prbably put in z safeguard
        def move():
            return self.host.MoveAxes(
                False,
                bool(dx != 0),
                bool(dy != 0),
                bool(dz != 0),
                False,
                int(dx),
                int(dy),
                int(dz * 10),
                0,
                1,
                1,
                1,
                1,
                not fast,
            )

        if fast:
            thread = threading.Thread(target=move)
            thread.start()
            time.sleep(self.settings.get("FAST_MOVE_REL_TIME"))
        else:
            return move()

    def phase_um(self):
        """Load phase image to file, then read file and return numpy array with height in um"""
        # implies SetUnwrap2DMethod == 0 (fast method). (For time saving)
        self.host.SingleReconstruction()
        self.host.SetUnwrap2DState(True)

        # dump the displayed phase as a .bin file
        fpath = str(self.basePath / "./tmp/phase.bin")
        try:
            self.host.SaveImageFloatToFile(4, fpath, True)
        except Exception as err:
            print("err in SaveImageFloatToFile")
            return self.phase_um()

        with open(fpath, "rb") as f:
            hdr_ver, endian = struct.unpack("bb", f.read(2))
            int32 = "<i" if endian == 0 else ">i"
            float32 = "<f" if endian == 0 else ">f"
            header_size = struct.unpack(int32, f.read(4))[0]
            width = struct.unpack(int32, f.read(4))[0]
            height = struct.unpack(int32, f.read(4))[0]
            pxSize_um = struct.unpack(float32, f.read(4))[0] * 1e6
            hconv = struct.unpack(float32, f.read(4))[0]  # * metres / radian
            unit = struct.unpack("b", f.read(1))[0]
            phase = np.fromfile(f, np.float32).reshape(height, width)

        if unit == 1:  # 1 = rad, 2 = m
            # [um] = [rad] * [m/rad] * [um/m]
            phase = phase * hconv * 1e6
        return phase, pxSize_um  # [um (height)], [um/px (x and y)]

    def phaseAvg_um(self, avg=5):
        avg += 2
        avg = max(avg - 1, 0)
        phase0, pxSize = self.phase_um()
        phases = [self.phase_um()[0] for _ in range(avg)]
        return np.mean((phase0, *phases), axis=0), pxSize

    def getContrast(self, avg=5):
        contrasts = []
        for i in range(0, avg):
            self.host.SingleReconstruction()
            contrasts.append(self.host.GetHoloContrast())

        highest_half = np.partition(contrasts, -avg // 2)[-avg // 2 :]
        return np.mean(highest_half)

    def searchUntilDecrease(self, search: MaxContSearch):
        """Search from z_1 to z_2 until the first decrease in contrast. Throws if contrast never decreased"""
        print(
            f"Searching for max contrast from z_1 = {int(search.z_1)} and z_2 = {int(search.z_2)} using {search.subdivisions} subdivisions (avg = {search.avg})"
        )

        search.logXYPos(*self.getPos()[:2])
        self.scan.startLogMaxContSearch(search)

        # search
        for z in np.arange(search.z_1, search.z_2, search.step * search.direction):
            self.move_to(z=z, fast=True)
            search.newContPt(self.getContrast(avg=search.avg), z)
            self.scan.updateGraph()

            if search.isAtLocalMaxCont():
                return search.getRecentMaxContInterval()

        if search.isStillIncreasing():
            print("Prematurely stopped searching, extending range 200um")
            search.extend(200)
            return self.searchUntilDecrease(search)

        if search.allNonNoise():
            print(
                "No decrease in contrast found, so taking highest contrast on interval"
            )
            return search.getTotalMaxContInterval()

        if not search.dontTryAgain:
            return self.searchUntilDecrease(search.emptyCopy())
        raise FocusNotFound()

    def find_focus(self, direction=-1):
        """Finds the focus from scratch. Can throw FocusNotFound error if nothing is found. Return (contrast, z)at max contrast"""
        # ? Convention: z's are from the top, h's are from the bottom with focus distance included.
        # * Direction: -1 for stage going down, 1 for stage going up
        maxZ = self.maxZ - self.focusDist / 2

        # running max interval
        I = []
        I = self.searchUntilDecrease(
            MaxContSearch(
                0,
                maxZ,
                direction,
                minContrast=self.settings.get("IDEAL_NOISE_CUTOFF"),
                step=200,
                avg=5,
            )
        )  # will throw NoFocusFound if nothing found
        I = self.searchUntilDecrease(
            MaxContSearch(
                I[0][1],
                I[-1][1],
                # start on the side with higher contrast
                np.sign(I[-1][0] - I[0][0]),
                minContrast=I[1][0] * 0.9,
                subdivisions=12,
                avg=10,
            )
        )
        I = self.searchUntilDecrease(
            MaxContSearch(
                I[0][1],
                I[-1][1],
                # start on the side with higher contrast
                np.sign(I[-1][0] - I[0][0]),
                minContrast=I[1][0] * 0.9,
                subdivisions=10,
                avg=20,
            )
        )
        zFocus = I[1][1]
        self.move_to(z=zFocus)
        print(f"Found focus @ z = {int(zFocus)}")
        return I[1][0], self.getPos()

    def find_maximising_dir(self, minContrast):
        """Go up and down a bit and see which direction has increasing contrast. Then goes to the less focused point
        MUST CATCH FocusNotFound Error"""

        x, y, startZ = self.getPos()
        contrasts = {}  # kv pairs of dz: contrast
        dist = self.settings.get("FIND_DIR_DIST")
        for dz in [-dist, dist, 0]:
            try:
                self.move_to(z=startZ + dz, fast=True)
            except InvalidMove:
                raise FocusNotFound()
            contrast = self.getContrast(avg=dist // 5 + 1)  # fast huristic for avg
            contrasts[dz] = contrast

        maxDz = max(contrasts, key=contrasts.get)
        if contrasts[maxDz] < minContrast:
            raise FocusNotFound()
        maximisingDir = np.sign(maxDz)

        # move to the side of lowest contrast to approach the side of highest contrast
        self.move_to(z=startZ - maxDz, fast=True)  # assumes only 2 opposite points

        self.scan.logDirectionSearch(x, y, startZ, maximisingDir, contrasts)

        return maximisingDir

    def maximizeFocus(self, minContrast=None):
        """Does a direction search, then a maxContrast search. if directino search fails, does a total search. Will propogate FocusNotFound only if the total search fails or a maxZ is not set. Return the (contrast, pos) at max contrast"""
        if minContrast == None:
            minContrast = self.settings.get("IDEAL_NOISE_CUTOFF")

        maximisingDir = None
        try:
            maximisingDir = self.find_maximising_dir(minContrast)
            if maximisingDir == 0:
                return self.getContrast(), self.getPos()  # already focused
        except FocusNotFound:
            print(
                "find_maximising_dir could not determine focus direction. Doing a total search"
            )
            # could throw if no focus is found
            return self.find_focus()

        # We do have a valid maximisingDir, go in that direction
        print(f"Searhcing in maximisingDir = {maximisingDir}")
        curZ = self.getPos()[2]
        endPoints = {1: self.maxZ - self.focusDist / 2, -1: 0}
        try:
            I = self.searchUntilDecrease(
                MaxContSearch(
                    curZ,
                    endPoints[maximisingDir],
                    maximisingDir,
                    minContrast,
                    step=50,  # safe to do a small step beacuse we're already half focused, and the focus depth is not that big
                ),
            )
            I = self.searchUntilDecrease(
                MaxContSearch(
                    I[0][1],
                    I[-1][1],
                    # start on the side with higher contrast
                    np.sign(I[-1][0] - I[0][0]),
                    minContrast=I[1][0],
                    subdivisions=10,
                    avg=10,
                )
            )
            print(f"Found focus {I[1][0]} @ z = {int(I[1][1])}")
            self.move_to(z=I[1][1])
            return I[1][0], self.getPos()
        except FocusNotFound:  # maybe we got maximising direction wrong?
            print("No focus found. Trying total search")
            # will throw if found nothing
            return self.find_focus()

    def ensureFocus(self, minContrast, avg=5):
        """Sees if focused, if not, maximizesFocus. Returns (contrast, pos)"""
        cont = self.getContrast(avg=avg)
        pos = self.getPos()

        self.scan.logContrast(*pos, cont)
        print(f"Contrast is {cont:.2f} (minContrast={minContrast:.2f})")

        # Could make this more advanced, where min contrast could be a functino of how big your step was, and your slope
        if cont > minContrast:
            return cont, pos  # already focused
        return self.maximizeFocus()

    def smart_move_rel(self, dx=0, dy=0, fast=False):
        phase, pxSize = self.phase_um()

        # quadratic doesn't outperform planer fits
        a, b, c = utils.fit_plane(phase, pxSize)
        # -dh because the phase picture is calculating heights, and higher things mean lower z
        dh = a * dx + b * dy
        dz = -dh

        self.move_rel(dx, dy, dz, fast=fast)
        return dz

    def stepToExtreme(self, dir, speed=100_000, maxStep=300):
        """Dir = 1 for the top of a convex object, dir =-1 for the bottom of a concave object"""
        # ?* Assumes already focused
        phase, pxSize = self.phase_um()

        # so far, quadratic doesn't outperform planer fits
        a, b, c = utils.fit_plane(phase, pxSize)
        grad = dir * np.array([a, b])
        mag = np.linalg.norm(grad)
        dx, dy = grad * speed if mag * speed <= maxStep else maxStep * grad / mag
        # -dh because the phase picture is calculating heights, and higher things mean lower z
        dh = a * dx + b * dy
        dz = -dh

        self.move_rel(dx, dy, dz)
        print(f"For dx={int(dx)} dy={int(dy)}, added dz={dz:.2f}")
        return dz

    def traverseToExtreme(self, dir):
        """Returns the focused cords and contrast at the center (top)"""
        """Dir = 1 for the top of a convex object, dir =-1 for the bottom of a concave object"""

        startCont, pos = self.maximizeFocus()
        dzThresh = self.settings.get("DZ_THRESH")

        for i in range(1000):
            dz = self.stepToExtreme(dir=dir, speed=50_000 - i * 50, maxStep=1_000)
            cont, _pos = self.ensureFocus(minContrast=startCont * 0.5)
            if abs(dz) < dzThresh:
                center = self.getPos()
                print(f"Top is at {center}")
                return cont, center

    def mapRow(self, row: Row):
        """Asumes we are focused at the center of the row. The row has already been initialized at the center"""
        startCont = self.getContrast()
        pos = self.getPos()
        self.scan.logContrast(*pos, startCont)

        while not row.done:
            t0 = time.time()
            self.smart_move_rel(dx=row.moveDir * row.stepX, fast=True)

            try:
                MaxContSearch.dontTryAgain = True
                cont, (x, y, z) = self.ensureFocus(minContrast=startCont * 0.5, avg=3)

                if row.prematureEdge(x):
                    raise FocusNotFound
            except FocusNotFound:
                row.atEdge(*self.getPos())
                self.move_to(*row.centerPos)
                continue

            for i in range(1000):  # try 1000 times at maximum
                try:
                    phase, _ = self.phaseAvg_um(avg=i // 100)
                    row.addToStitch(phase)
                    break
                except BadFit:
                    ...
            else:
                raise Exception("Could not find a valid stitch")  # not caught
            picTime = time.time() - t0
            print(f"Total Pic time: {picTime:.3f}s")

    def mapProfile(self, curvature, maxRadius=None):
        """Curvature=1, traverse to top, =-1 to bottom, =0 dont traverse at all"""
        if curvature != 0:  # convex
            self.scan = Scan(show=True)
            startCont, center = self.traverseToExtreme(dir=curvature)
            self.scan.saveToFiles()
        else:
            self.move_to(58249.36, 52110, 12227.2)  # TODO just for debugging, remove
            center = self.getPos()

        phase, pxSize = self.phaseAvg_um(avg=1)
        areaMap = AreaMap(True, phase.shape, pxSize, maxRadius, curvature)
        self.scan = Graph(areaMap=areaMap)
        row = areaMap.nextRow()
        row.initCenter(phase, pxSize, center, None, 0)
        self.mapRow(row)

        areaMap.saveImages()
        self.scan.saveToFiles(show=False)

    def mapArea(self, curvature, circle, maxRadius=None):
        """Curvature=1, traverse to top, =-1 to bottom, =0 dont traverse at all"""
        if curvature != 0:
            self.scan = Scan(show=True)
            startCont, center = self.traverseToExtreme(dir=curvature)
            self.scan.saveToFiles()
        else:
            self.move_to(58249.36, 52110, 12227.2)  # TODO just for debugging, remove
            center = self.getPos()

        phase, pxSize = self.phaseAvg_um(avg=1)
        areaMap = AreaMap(True, phase.shape, pxSize, maxRadius, curvature, circle)
        self.scan = Graph(areaMap=areaMap)
        row = areaMap.nextRow()
        row.initCenter(phase, pxSize, center, None, 0)

        # * for each row:
        while not areaMap.done:
            self.scan.clear()
            if not row.done:
                self.mapRow(row)
                areaMap.addToStitch(row)

            self.smart_move_rel(dy=areaMap.moveDir * areaMap.stepY)
            startCont = self.getContrast()
            pos = self.getPos()

            try:
                MaxContSearch.dontTryAgain = True
                cont, (x, y, z) = self.ensureFocus(minContrast=startCont * 0.5, avg=3)

                if areaMap.prematureEdge(y):
                    raise FocusNotFound
            except FocusNotFound:
                areaMap.atEdge(*pos)
                row = areaMap.centerRow  # so that the next row stitches correctly
                self.move_to(*center)
                continue

            for i in range(1000):  # try 1000 times at maximum
                try:
                    phase, _ = self.phaseAvg_um(avg=i // 100)
                    shift, zDiff = areaMap.getShift(row.centerPic, phase)
                    curZDiff = row.zDiff
                    row = areaMap.nextRow()
                    row.initCenter(phase, pxSize, pos, shift, curZDiff + zDiff)
                    break
                except BadFit:
                    ...
            else:
                raise Exception("Could not find a valid stitch")  # not caught

        self.scan.saveToFiles(show=False)

    def logout(self):
        """Logout from the Koala remote client."""
        self.host.Logout()
