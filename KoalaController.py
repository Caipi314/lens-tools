import sys
from tracemalloc import start
import matplotlib.pyplot as plt
from datetime import datetime
from MaxContSearch import MaxContSearch
from Scan import Scan
import utils
import struct
import pathlib
import numpy as np
import clr
import time
import collections

clr.AddReference("System")
import System
from System import Array

# Add reference and import KoalaRemoteClient
sys.path.append(r"C:\\Program Files\\LynceeTec\\Koala\\Remote\\Remote Libraries\\x64")
clr.AddReference("LynceeTec.KoalaRemote.Client")
from LynceeTec.KoalaRemote.Client import KoalaRemoteClient

# MAX_Z = 2_962
IDEAL_NOISE_CUTOFF = 2.2  # 1.95
LOWEST_NOISE_CUTOFF = 1.7
ABS_MAX_Z = 27175.0  # um. Max z with no lens or holder on the stage
MID_Y = 52_500


class FocusNotFound(Exception):
    """Contrast never decreased"""

    pass


class KoalaController:
    def __init__(self, host="localhost", user="user", passw="user"):
        self.basePath = pathlib.Path.cwd()
        self.host = KoalaRemoteClient()
        ret, username = self.host.Connect(
            host, user, True
        )  # True is deprecated but required
        self.host.Login(passw)
        self.maxZ = None
        self.scan = None

    def setup(self):
        """Initialize configuration and source state."""
        self.host.OpenConfig(142)  # for 20x objective
        self.host.SetSourceState(0, True, True)
        self.pxSize = self.host.GetPxSizeUm()
        self.focusDist = (
            27175 - 13207 - (7.66 - 0.16) * 1e3
        )  # d_focus = Z_max - Z_focus - h_real #! calibrated dont touch now
        self.ABS_MAX_H = ABS_MAX_Z - self.focusDist
        self.host.SetUnwrap2DMethod(0)
        self.host.OpenPhaseWin()
        time.sleep(0.1)

    def loadScan(self, scan: Scan):
        self.scan = scan

    def setLimit(self, h):
        if h < 500:
            raise Exception("Please give h in um to host.setMinH(h)")
        self.maxZ = ABS_MAX_Z - h

    def getPos(self):
        buffer = System.Array.CreateInstance(System.Double, 4)
        self.host.GetAxesPosMu(buffer)
        return (buffer[0], buffer[1], buffer[2] / 10)

    def hToZ(self, h):
        return ABS_MAX_Z - self.focusDist - h

    def zToH(self, z):
        if z == None:
            raise Exception(f"Cannot convert z to h when z = {z}")
        return ABS_MAX_Z - self.focusDist - z

    def move_to(self, x=0, y=0, z=0, h=0, fatal=True, fast=False):
        """MUST SET self.maxZ in order to move the Z axis"""
        # ? Fast mode does not wait for the moving to finish (according to Koala), but adds 0.4s delay. ~50% speedup for small movements
        # * give Z in joystick/real heights
        # * h is height of surface from stage.
        if h != 0:
            z = ABS_MAX_Z - h

        if z != 0:
            if self.maxZ == None:
                raise Exception("Tried to move without setting self.maxZ")
            if z < 0 or z > ABS_MAX_Z or z > self.maxZ:
                if fatal:
                    print(f"Tried to move to not allowed z={z}")
                    exit()
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

    def move_rel(self, dx=0, dy=0, dz=0):
        # TODO should prbably put in z safeguard
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
            True,
        )

    def phase(self):
        """Load the phase image to a numpy array."""
        #! Take an image (unwrap it)
        self.host.SingleReconstruction()
        self.host.SetUnwrap2DState(True)

        #! Moved to the save reconstruction from memory to a numpy array
        w = self.host.GetPhaseWidth()
        h = self.host.GetPhaseHeight()

        # Koala gives phase as 32-bit floats (= System.Single)
        stride = ((w + 3) // 4) * 4  # Koala pads rows to 4-pixel multiples
        size = stride * h  # total number of samples in the buffer
        buf = Array.CreateInstance(System.Single, size)  # .NET float[]
        self.host.GetPhase32fImage(buf)
        phase_flat = np.array(buf, dtype=np.float32)
        phase = phase_flat[: h * w].reshape((h, w))  # drop padding & reshape

        return phase  # * Returns in radians

    def phase_um(self):
        """Load phase image to file, then read file and return numpy array with height in um"""
        # implies SetUnwrap2DMethod == 0 (fast method). (For time saving)
        self.host.SingleReconstruction()
        self.host.SetUnwrap2DState(True)

        # dump the displayed phase as a .bin file
        fpath = str(self.basePath / "./tmp/phase.bin")
        try:
            self.host.SaveImageFloatToFile(4, fpath, True)
        except:
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

        # [rad] * [m/rad] * [um/m] * 10 (z factor thing trust be bro)
        if unit == 1:  # 1 = rad, 2 = m
            phase = phase * hconv * 1e6
        return phase, pxSize_um  # [um (height)], [um/px (x and y)]

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
        for z in np.linspace(search.z_1, search.z_2, int(search.subdivisions)):
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
        raise FocusNotFound()

    def find_focus(self, direction=-1):
        """Finds the focus from scratch. Can throw FocusNotFound error if nothing is found"""
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
                minContrast=IDEAL_NOISE_CUTOFF,
                subdivisions=65,
                avg=5,
            )
        )  # will throw NoFocusFound if nothing found
        I = self.searchUntilDecrease(
            MaxContSearch(
                I[0][1],
                I[-1][1],
                # start on the side with higher contrast
                np.sign(I[-1][0] - I[0][0]),
                minContrast=I[1][0],
                subdivisions=20,
                avg=10,
            )
        )
        I = self.searchUntilDecrease(
            MaxContSearch(
                I[0][1],
                I[-1][1],
                # start on the side with higher contrast
                np.sign(I[-1][0] - I[0][0]),
                minContrast=I[1][0],
                subdivisions=5,
                avg=20,
            )
        )
        zFocus = I[1][1]
        self.move_to(z=zFocus)
        print(f"Found focus @ z = {int(zFocus)}")
        return zFocus

    def find_maximising_dir(self, minContrast, dist=25):
        """Go up and down a bit and see which direction has increasing contrast. Then goes to the less focused point
        MUST CATCH FocusNotFound Error"""

        x, y, startZ = self.getPos()
        contrasts = {}  # kv pairs of dz: contrast
        for dz in [-dist, dist, 0]:
            self.move_to(z=startZ + dz, fast=True)
            contrast = self.getContrast(avg=dist + 1)  # fast huristic for avg
            contrasts[dz] = contrast

        maxDz = max(contrasts, key=contrasts.get)
        if contrasts[maxDz] < minContrast:
            raise FocusNotFound()
        maximisingDir = np.sign(maxDz)

        self.move_to(z=startZ - maxDz, fast=True)  # assumes only 2 opposite points

        self.scan.logDirectionSearch(x, y, startZ, maximisingDir, contrasts)

        return maximisingDir

    def maximizeFocus(self, minContrast=IDEAL_NOISE_CUTOFF):
        """Does a direction search, then a maxContrast search. if directino search fails, does a total search. Will propogate FocusNotFound only if the total search fails or a maxZ is not set"""
        maximisingDir = None
        try:
            maximisingDir = self.find_maximising_dir(minContrast)
            if maximisingDir == 0:
                return  # already focused
        except FocusNotFound:
            print(
                "find_maximising_dir could not determine focus direction. Doing a total search"
            )
            # could throw if no focus is found
            self.find_focus()
            return

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
        except FocusNotFound:  # maybe we got maximising direction wrong?
            print("No focus found. Trying the other direction")
            try:
                self.searchUntilDecrease(
                    MaxContSearch(
                        curZ,
                        endPoints[-maximisingDir],
                        -maximisingDir,
                        minContrast,
                        step=30,
                    ),
                )
            except FocusNotFound:
                # will throw if found nothing
                self.find_focus()
                return

    def ensureFocus(self, minContrast):
        """Sees if focused, if not, maximizesFocus"""
        cont = self.getContrast(avg=5)
        self.scan.logContrast(*self.getPos(), cont)
        print(f"Contrast is {cont:.2f}")

        # Could make this more advanced, where min contrast could be a functino of how big your step was, and your slope
        if cont > minContrast:
            return  # already focused
        self.maximizeFocus()

    def smart_move_rel(self, dx=0, dy=0):
        phase, pxSize = self.phase_um()

        y_1, x_1 = np.array(phase.shape) * pxSize / 2  # center point of image
        y_2, x_2 = y_1 + dy, x_1 + dx

        # so far, quadratic doesn't outperform planer fits
        fit_func = utils.fit_plane(phase, pxSize, returnCoefs=False)
        dh = fit_func(x_2, y_2) - fit_func(x_1, y_1)

        print(f"For dx={int(dx)}, added dz={int(dh)}")

        # -dh because the phase picture is calculating heights, and higher things mean lower z
        self.move_rel(dx, dy, -dh)
        return dh

    def traverse(self, x=0, step=100):
        startCont = self.getContrast(avg=5)

        sumZ = 0
        for i in range(x // step):
            sumZ += self.smart_move_rel(dx=step)
            self.ensureFocus(minContrast=startCont * 0.5)
        print(f"Sum delta_Z={sumZ:.1f} to traverse {x/1000}mm")

    def traverseUp(self, speed=100_000, maxStep=300):
        # ?* Assumes already focused
        phase, pxSize = self.phase_um()

        # so far, quadratic doesn't outperform planer fits
        a, b, c = utils.fit_plane(phase, pxSize, returnCoefs=True)
        grad = np.array([a, b])
        mag = np.linalg.norm(grad)
        dx, dy = grad * speed if mag * speed <= maxStep else maxStep * grad / mag
        dh = a * dx + b * dy

        self.move_rel(dx, dy, -dh)
        print(f"For dx={int(dx)} dy={int(dy)}, added dz={dh:.2f}")
        return dh

    def traverseToTop(self):
        self.maximizeFocus()
        startCont = self.getContrast()

        while True:
            dz = self.traverseUp(speed=100_000, maxStep=1_000)
            self.ensureFocus(minContrast=startCont * 0.5)
            # self.maximizeFocus()
            if dz < 0.01:
                center = self.getPos()
                print(f"Top is at {center}")
                return center

    def traverseToEnd(self, step=100):
        """Traverses to the end of a lens until you can't find the contrast. Returns the position of the end"""
        self.maximizeFocus()
        startCont = self.getContrast()

        sag = 0
        while True:
            try:
                dz = self.smart_move_rel(dx=step)
                sag += dz
                print(f"Sag is at least {sag/1000:.2f}mm")
                self.ensureFocus(minContrast=startCont * 0.5)
            except FocusNotFound:
                x, y, z = self.getPos()
                edge = (x - step, y, z)
                print(f"Edge is at {edge}")
                return edge

    # def map2dProfile(self):

    def logout(self):
        """Logout from the Koala remote client."""
        self.host.Logout()
