import sys
import matplotlib.pyplot as plt
from datetime import datetime
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

    def loadScan(self, scan):
        self.scan = scan

    def setMinH(self, h):
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
        return ABS_MAX_Z - self.focusDist - z

    def zsToInterval(self, z_a, z_b, direction):
        """Returns in the interval going from z_1 to z_2 where the order is based on direction"""
        return (
            (min(z_a, z_b), max(z_a, z_b))
            if direction == 1
            else (max(z_a, z_b), min(z_a, z_b))
        )

    def move_to(self, x=0, y=0, z=0, h=0, fatal=True, fast=False):
        """MUST SET self.maxZ in order to move the Z axis"""
        # ? Fast mode does not wait for the moving to finish (according to Koala), but adds 0.4s delay. ~50% speedup for small movements
        # * give Z in joystick/real heights
        # * h is height of surface from stage.
        if h != 0:
            z = ABS_MAX_Z - h - self.focusDist

        if z != 0:
            if self.maxZ == None:
                print("Tried to move without setting self.maxZ")
                exit()
            if z < 0 or z > ABS_MAX_Z or z > self.maxZ:
                if fatal:
                    print(f"Tried to move to not allowed z={z}")
                    exit()
                else:
                    return False
        ok = self.host.MoveAxes(
            True,
            x != 0,
            y != 0,
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
            dx != 0,
            dy != 0,
            True,  # move z axis
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

    def searchUntilDecrease(
        self,
        searchInterval,
        minContrast=IDEAL_NOISE_CUTOFF,
        subdivisions=25,
        avg=3,
        again=0,  # the nth try
    ):
        """Search from z_1 to z_2 until the first decrease in contrast"""
        z_1, z_2 = searchInterval
        print(
            f"Searching for max contrast from z_1 = {int(z_1)} and z_2 = {int(z_2)} using {subdivisions} subdivisions (avg = {avg})"
        )

        # z_1 needs to be there in case first check is decreasing, (0, z_1) will be the first item in the list
        contrasts = [(0, z_1)]  # always needs to return with 3 items

        for z in np.linspace(z_1, z_2, subdivisions):
            self.move_to(z=z, fast=True)
            contrasts.append((self.getContrast(avg=avg), z))

            if contrasts[-1][0] < contrasts[-2][0] and contrasts[-2][0] > minContrast:
                print(f"Found max contrast = {contrasts[-2][0]:.2f}")
                maxContrastInterval = list(contrasts)[-3:]
                self.scan.logContrastSearch(
                    *self.getPos()[:2],
                    *searchInterval,
                    contrasts[-2][0],
                    contrasts,
                )
                return maxContrastInterval

        if contrasts[-1][0] > minContrast:
            print("Prematurely stopped searching, extending range 200um")
            direction = np.sign(z_2 - z_1)
            return self.searchUntilDecrease(
                self.zsToInterval(z_2, z_2 + 200 * direction, direction),
                subdivisions=subdivisions,
                mincontrast=IDEAL_NOISE_CUTOFF,
                avg=avg,
                again=again,
            )

        if again == 0:
            print("Contrast never decreased. Trying again with lower threshold")
            return self.searchUntilDecrease(
                searchInterval,
                subdivisions=subdivisions * 2,
                mincontrast=IDEAL_NOISE_CUTOFF,
                avg=5,
                again=1,
            )
        if again == 1:
            raise Exception(f"Contrast never decreased on entire range.")

    def find_focus(self, guessHeight_mm, direction=-1):
        # ? Convention: z's are from the top, h's are from the bottom with focus distance included.
        # ? h's are the height of the actual object
        # * Direction: -1 for stage going down, 1 for stage going up
        guessHeight = guessHeight_mm * 1e3
        self.setMinH(guessHeight)

        minH = guessHeight - self.focusDist / 2
        maxZ = self.hToZ(minH)

        l = self.searchUntilDecrease(
            self.zsToInterval(0, maxZ, direction),
            minContrast=IDEAL_NOISE_CUTOFF,
            subdivisions=65,
            avg=5,
        )
        l = self.searchUntilDecrease(
            # start on the side with higher contrast
            self.zsToInterval(l[0][1], l[-1][1], -1 if l[0][0] > l[-1][0] else 1),
            minContrast=l[1][0],
            subdivisions=20,
            avg=10,
        )
        l = self.searchUntilDecrease(
            self.zsToInterval(l[0][1], l[-1][1], -1 if l[0][0] > l[-1][0] else 1),
            minContrast=l[1][0],
            subdivisions=20,
            avg=30,
        )
        zFocus = l[1][1]
        print(f"Found focus @ z = {int(zFocus)}")
        return zFocus

    def find_maximising_dir(self, dist=25):
        """Go up and down a bit and see which direction has increasing contrast"""
        # ? Could make it faster by only checking 2 and not the center
        startZ = self.getPos()[2]
        contrasts = {}
        for dz in [-dist, dist]:
            self.move_to(z=startZ + dz, fast=True)
            contrast = self.getContrast(avg=50)
            contrasts[dz] = contrast

        maxDz = max(contrasts, key=contrasts.get)
        if contrasts[maxDz] < LOWEST_NOISE_CUTOFF:
            print("Tried to find_maximising_dir but not currently focused")
            return 0
        maximisingDir = np.sign(maxDz)

        self.scan.logDirectionSearch(
            *self.getPos()[:2], startZ, maximisingDir, contrasts
        )
        return maximisingDir

    def smart_move_rel(self, dx=0, dy=0):
        phase, pxSize = self.phase_um()

        y_1, x_1 = np.array(phase.shape) * pxSize / 2  # center point of image
        y_2, x_2 = y_1 + dy, x_1 + dx

        # so far, quadratic doesn't outperform planer fits
        fit_func = utils.fit_plane(phase, pxSize)
        dz = fit_func(x_2, y_2) - fit_func(x_1, y_1)

        print(f"For dx={int(dx)}, added dz={int(dz)}")

        # -dz because the phase picture is calculating heights, and higher things mean lower z
        self.move_rel(dx, dy, -dz)
        return dz

    def traverse(self, x=0, step=100):
        startCont = self.getContrast(avg=5)

        sumZ = 0
        for i in range(x // step):
            sumZ += self.smart_move_rel(dx=step)
            cont = self.getContrast(avg=5)
            self.scan.logContrast(*self.getPos(), cont)

            print(f"Contrast is {cont:.2f} @ ∑dx = {i*step}")
            # cutoff could be a functino of how big your step was, and your slope
            if cont < IDEAL_NOISE_CUTOFF * 2:
                maximisingDir = self.find_maximising_dir()
                if maximisingDir == 0:
                    maximisingDir = self.find_maximising_dir()

                print(f"MaximisingDir = {maximisingDir}")
                curZ = self.getPos()[2]
                raise Exception("we done")
                try:
                    self.searchUntilDecrease(
                        self.zsToInterval(
                            curZ, curZ + 200 * maximisingDir, maximisingDir
                        ),
                        minContrast=startCont * 0.5,
                        subdivisions=30,
                    )
                except:  # we got maximising direction wrong?
                    print("No focus found. Trying the other direction")
                    self.searchUntilDecrease(
                        self.zsToInterval(
                            curZ, curZ - 200 * maximisingDir, maximisingDir
                        ),
                        minContrast=startCont * 0.5,
                        subdivisions=20,
                    )

        print(f"Sum delta_Z={sumZ:.1f} to traverse {x/1000}mm")

    def logout(self):
        """Logout from the Koala remote client."""
        self.host.Logout()
