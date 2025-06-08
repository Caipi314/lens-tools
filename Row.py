import threading
import numpy as np
from skimage.registration import phase_cross_correlation

from Traversal import BadFit
import utils


class Row:
    xOverlap = 25
    acceptableDy = 20

    def __init__(self, maxRadius=None):
        self.maxRadius = maxRadius
        self.done = False
        self.moveDir = 1
        # always go right (1) then left (-1) each time from center

    def initCenter(self, centerPic, pxSize, centerPos, shiftFromLast, zDiff=0):
        self.centerPic = centerPic
        self.pxSize = pxSize
        self.centerPos = centerPos  # (x,y,z)
        # (dy, dx) relative to the offset and last center pic. is None if first pic
        self.shiftFromLast = shiftFromLast
        self.zDiff = zDiff

        self.stitch = centerPic
        self.picShape = np.array(self.centerPic.shape)  # (y, x) in px
        self.stepX = (self.picShape[1] - Row.xOverlap) * self.pxSize  # positive X

    def prematureEdge(self, x):
        return self.maxRadius and abs(x - self.centerPos[0]) > self.maxRadius

    def atEdge(self, x, y, z):
        if self.moveDir == 1:
            self.edge = np.array([x - self.stepX, y, z])
            self.moveDir = -1
            print(f"X Edge is at {self.edge}")
        else:
            #! Should be replacing Nan based on closes valid pixrel
            self.stitch = np.nan_to_num(self.stitch, nan=0)
            self.done = True

    def padAndStitch(self, pic1, pic2, dx, dy, f1Area, f2Area, p1TopPads, p2TopPads):
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

        dz = utils.getZDiff(dx, dy, f1Area, f2Area)
        pic2 += dz
        dy = dy + p1TopPads - p2TopPads
        pic1, pic2 = padPics(pic1, pic2, dy)

        # take mean of overlapping regions
        overlapRegion = (pic1[:, -Row.xOverlap :] + pic2[:, : Row.xOverlap]) / 2
        stitchPic = np.concatenate(
            (pic1[:, : -Row.xOverlap], overlapRegion, pic2[:, Row.xOverlap :]), axis=1
        )
        # stitchPic = np.nan_to_num(stitchPic, nan=0, copy=False)
        self.stitch = stitchPic

    def stitchX(self, pic1, pic2):
        """Stitches pic1 to the right of pic2 and sets it as self.stitch. Throws BadFit if bad stitch"""
        # how many NaN pads are at the top of each image (in the overlap reigon)
        p1TopPads = np.argmax(~np.isnan(pic1[:, -1]))
        p2TopPads = np.argmax(~np.isnan(pic2[:, 0]))

        # f1Area and f2Area should represent the same physical space
        f1Area = pic1[p1TopPads : self.picShape[0] + p1TopPads, -Row.xOverlap :]
        f2Area = pic2[p2TopPads : self.picShape[0] + p2TopPads, : Row.xOverlap]

        # relative to being overlapped perfectly, whats the required shift to line up perfectly
        (dy, dx), err, phaseDiff = phase_cross_correlation(f1Area, f2Area)
        dy, dx = int(dy), int(dx)

        if abs(dy) > Row.acceptableDy:
            print(f"Fit not acceptable (dy={dy}), trying again")
            raise BadFit

        # now safe to thread for the speed increase
        thread = threading.Thread(
            target=self.padAndStitch,
            args=(pic1, pic2, dx, dy, f1Area, f2Area, p1TopPads, p2TopPads),
        )
        thread.start()

    def addToStitch(self, pic):
        """Stitches based on self.moveDir. Throws BadFit if bad stitch"""
        if self.moveDir == 1:
            self.stitchX(self.stitch, pic)
        else:
            self.stitchX(pic, self.stitch)
