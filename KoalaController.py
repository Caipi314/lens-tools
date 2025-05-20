import sys
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
sys.path.append(r'C:\\Program Files\\LynceeTec\\Koala\\Remote\\Remote Libraries\\x64')
clr.AddReference("LynceeTec.KoalaRemote.Client")
from LynceeTec.KoalaRemote.Client import KoalaRemoteClient

# MAX_Z = 2_962
ABS_MAX_Z = 27175.0 # um. Max z with no lens or holder on the stage
MID_Y = 52_500
# NOISE_CUTOFF = 2.1

class KoalaController:
    def __init__(self, host='localhost', user='user', passw='user'):
        self.basePath = pathlib.Path.cwd()
        self.host = KoalaRemoteClient()
        ret, username = self.host.Connect(host, user, True)  # True is deprecated but required
        self.host.Login(passw)
        self.maxZ = None

    def setup(self):
        """Initialize configuration and source state."""
        self.host.OpenConfig(142) # for 20x objective
        self.host.SetSourceState(0, True, True)
        self.pxSize = self.host.GetPxSizeUm()
        self.focusDist = 27175 - 13207 - (7.66 - 0.16)*1e3 # d_focus = Z_max - Z_focus - h_real #! calibrated dont touch now
        self.ABS_MAX_H = ABS_MAX_Z - self.focusDist
        self.host.SetUnwrap2DMethod(0)
        self.host.OpenPhaseWin()
        time.sleep(0.1)

    def move_to(self, x=None, y=None, z=None, h=None, fatal=True, fast=False):
        """MUST SET self.maxZ in order to move the Z axis"""
        #* give Z in joystick/real heights
        #* h is height of surface from stage.
        if h != None:
            z = ABS_MAX_Z - h - self.focusDist

        if z != None:
            if self.maxZ == None:
                print("Tried to move without setting self.maxZ")
                exit()
            if z < 0 or z > ABS_MAX_Z or z > self.maxZ:
                if fatal:
                    print(f"Tried to move to not allowed z={z}")
                    exit()
                else:
                    return False
        ok = self.host.MoveAxes(True, x != None, y != None, z != None, False, x or 0, y or 0, z*10 or 0, 0, 1, 1, 1, 1, not fast)
        if fast:
            time.sleep(0.4)
        return ok

    def phase(self):
        """Load the phase image to a numpy array."""
        #! Take an image (unwrap it)
        self.host.SingleReconstruction()
        self.host.SetUnwrap2DState(True)

        #! Moved to the save reconstruction from memory to a numpy array
        w = self.host.GetPhaseWidth()
        h = self.host.GetPhaseHeight()

        # Koala gives phase as 32-bit floats (= System.Single)
        stride = ((w + 3) // 4) * 4 # Koala pads rows to 4-pixel multiples
        size = stride * h # total number of samples in the buffer
        buf = Array.CreateInstance(System.Single, size) # .NET float[]
        self.host.GetPhase32fImage(buf)
        phase_flat = np.array(buf, dtype=np.float32)
        phase = phase_flat[:h * w].reshape((h, w)) # drop padding & reshape

        return phase #* Returns in radians

    def phase_um(self):
        """Load phase image to file, then read file and return numpy array with height in um"""
        # implies SetUnwrap2DMethod == 0 (fast method). (For time saving)
        self.host.SingleReconstruction()
        self.host.SetUnwrap2DState(True)

        # dump the displayed phase as a .bin file
        fpath = str(self.basePath / './tmp/phase.bin')
        self.host.SaveImageFloatToFile(4, fpath, True)

        with open(fpath, "rb") as f:
            hdr_ver, endian = struct.unpack("bb", f.read(2))
            int32 = "<i" if endian == 0 else ">i"
            float32 = "<f" if endian == 0 else ">f"
            header_size = struct.unpack(int32, f.read(4))[0]
            width = struct.unpack(int32, f.read(4))[0]
            height = struct.unpack(int32, f.read(4))[0]
            px_um = struct.unpack(float32, f.read(4))[0]
            hconv = struct.unpack(float32, f.read(4))[0] #* metres / radian
            unit = struct.unpack("b",  f.read(1))[0]
            phase = np.fromfile(f, np.float32).reshape(height, width)

        if unit == 1: # 1 = rad, 2 = m
            phase = phase * hconv * 1e5
        return phase

    def getContrast(self, avg = 1):
        sumContrast = 0
        for i in range(0, avg):
            self.host.SingleReconstruction()
            sumContrast += self.host.GetHoloContrast()
        return sumContrast  / avg

        #? Convention: z's are from the top, h's are from the bottom with focus distance included.
    def find_focus2(self, guessHeight_mm):
        #? h's are the height of the actual object

        guessHeight = guessHeight_mm * 1e3
        self.maxZ = ABS_MAX_Z - guessHeight * 1.2 # 20% factor is safety

        # ! start and bottom, go up in 100um intervals to find max holo contrast. Stop at guessHeight above the minH
        minH = guessHeight / 1.8
        maxContrast = (0, 0) # the contrast, and the associated h
        noiseCutoff = 2.1 # if below this, definitely noise

        contrasts = []
        maxContrast = (0, 0) # contrast, and height of max contrast
        for h in range(int(minH), int(minH + guessHeight), 100):
            self.move_to(h = h, fast = True)

            contrast = self.getContrast(avg = 3)
            contrasts.append(contrast)
            if contrast > maxContrast[0]:
                maxContrast = (contrast, h)
            # if we have a good contrast, and the last 4 are below the cutoff, end it
            if maxContrast[0] > noiseCutoff and np.all(np.array(contrasts[-5:]) < noiseCutoff):
                break

            print(int((h-minH) * 100 / guessHeight), contrast)

        print(f'max contrast: {maxContrast}')

    def find_focus(self, guessHeight_mm, topDown = False):
        def searchUntilDecrease(minH, maxH, subdivisions = 25, avg = 3, again = False, topDown = False):
            """Search until the first decrease in contrast"""
            print(f'Searching for max contrast between {minH} and {maxH} using {subdivisions} subdivisions (avg = {avg})')

            contrasts = collections.deque([(0, 0), (0, minH)], maxlen=2) # minH needs to be there in case first check is decreasing, (0, minH) will be the first item in the list

            for h in np.linspace(minH, maxH, subdivisions)[::-1 if topDown else 1]:
                self.move_to(h = h, fast = True)
                contrast = self.getContrast(avg = avg)

                if contrast < contrasts[-1][0] and contrasts[-1][0] > noiseCutoff:
                    print(f'Found max contrast = {contrasts[-1][0]}')
                    maxContrastInterval = list(contrasts) + [(contrast, h)]
                    print(maxContrastInterval)
                    return maxContrastInterval
                contrasts.append((contrast, h))

            if again:
                raise Exception(f"Contrast never decreased on entire range. Recheck guess of {guessHeight_mm}mm")
            print('Contrast never decreased. Trying again with more subdivisions')
            return searchUntilDecrease(minH, self.ABS_MAX_H, subdivisions = 150, avg = 3, again = True)

        #? h's are the height of the actual object

        guessHeight = guessHeight_mm * 1e3
        self.maxZ = ABS_MAX_Z - guessHeight # 20% factor is safety
        print(self.maxZ)

        # ! start and bottom, go up in 100um intervals to find max holo contrast. Stop at guessHeight above the minH
        # maxH = minH + guessHeight
        noiseCutoff = 1.9 # if below this, definitely noise

        minH = guessHeight - self.focusDist / 2
        l = searchUntilDecrease(minH, self.ABS_MAX_H, subdivisions = 50, avg = 3, topDown = topDown)
        l = searchUntilDecrease(l[0][1], l[-1][1], subdivisions = 20, avg = 5)
        l = searchUntilDecrease(l[0][1], l[-1][1], subdivisions = 50, avg = 30)
        print(f'max contrasts: {l}')


    def logout(self):
        """Logout from the Koala remote client."""
        self.host.Logout()
