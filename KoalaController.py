import sys
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
IDEAL_NOSIE_CUTOFF = 1.95
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
            x,
            y,
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

    def smart_move_rel(self, plane, pxSize, x=0, y=0):
        # TODO should prbably put in z safeguard
        a, b, c = plane
        z = a * x + b * y + c
        print(f"For dx={x}, added z={z} because dz/dx={a}")

        self.host.MoveAxes(
            False,
            x != 0,
            y != 0,
            True,  # move z axis
            False,
            x,
            y,
            int(z * -10),
            0,
            1,
            1,
            1,
            1,
            True,
        )
        return z

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
            phase = phase * hconv * 1e6 * 10
        return phase, pxSize_um  # [um (height)], [um/px (x and y)]

    def getContrast(self, avg=1):
        sumContrast = 0
        for i in range(0, avg):
            self.host.SingleReconstruction()
            sumContrast += self.host.GetHoloContrast()
        return sumContrast / avg

    def searchUntilDecrease(
        self, minH, maxH, subdivisions=25, avg=3, again=False, topDown=False
    ):
        """Search until the first decrease in contrast"""
        print(
            f"Searching for max contrast between {minH} and {maxH} using {subdivisions} subdivisions (avg = {avg})"
        )

        # minH needs to be there in case first check is decreasing, (0, minH) will be the first item in the list
        contrasts = collections.deque([(0, 0), (0, minH)], maxlen=2)

        for h in np.linspace(minH, maxH, subdivisions)[:: -1 if topDown else 1]:
            self.move_to(h=h, fast=True)
            contrast = self.getContrast(avg=avg)

            if contrast < contrasts[-1][0] and contrasts[-1][0] > IDEAL_NOSIE_CUTOFF:
                print(f"Found max contrast = {contrasts[-1][0]}")
                maxContrastInterval = list(contrasts) + [(contrast, h)]
                print(maxContrastInterval)
                return maxContrastInterval
            contrasts.append((contrast, h))

        if again:
            raise Exception(
                f"Contrast never decreased on entire range. Recheck guess of {guessHeight_mm}mm"
            )
        print("Contrast never decreased. Trying again with more subdivisions")
        return self.searchUntilDecrease(
            minH, self.ABS_MAX_H, subdivisions=150, avg=3, again=True
        )

    def find_focus(self, guessHeight_mm, topDown=False):
        # ? Convention: z's are from the top, h's are from the bottom with focus distance included.
        # ? h's are the height of the actual object

        guessHeight = guessHeight_mm * 1e3

        # ! start and bottom, go up in 100um intervals to find max holo contrast. Stop at guessHeight above the minH

        minH = guessHeight - self.focusDist / 2
        l = self.searchUntilDecrease(
            minH, self.ABS_MAX_H, subdivisions=50, avg=5, topDown=topDown
        )
        l = self.searchUntilDecrease(l[0][1], l[-1][1], subdivisions=20, avg=20)
        l = self.searchUntilDecrease(l[0][1], l[-1][1], subdivisions=10, avg=30)
        print(f"max contrast: {l[1]}")

    def find_maximising_dir(self):
        """Go up and down a bit and see which direction has increasing contrast"""
        # ? Could make it faster by only checking 2 and not the center
        dist = 25
        startZ = self.getPos()[2]
        contrasts = {}
        for dz in [-dist, dist, 0]:
            self.move_to(z=startZ + dz, fast=True)
            contrast = self.getContrast(avg=12)
            contrasts[dz] = contrast

        maxDz = max(contrasts, key=contrasts.get)
        if contrasts[maxDz] < LOWEST_NOISE_CUTOFF:
            print("Tried to find_maximising_dir but not currently focused")
            return 0
        return np.sign(maxDz)

    def traverse(self, x=0):
        step = 200  # [um]

        sumZ = 0
        for i in range(x // step):
            phase, pxSize = self.phase_um()
            plane = utils.slope(phase, pxSize)
            sumZ += self.smart_move_rel(plane, pxSize, x=step)
            # only check if contrast is bad. maybe
            if self.getContrast() < 4:
                maximisingDir = self.find_maximising_dir()
                curH = self.zToH(self.getPos()[2])
                goalH = curH + 150 * maximisingDir
                self.searchUntilDecrease(
                    min(curH, goalH),
                    max(curH, goalH),
                    subdivisions=10,
                    topDown=maximisingDir > 0,
                )

    def logout(self):
        """Logout from the Koala remote client."""
        self.host.Logout()
