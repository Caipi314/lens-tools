import threading
import numpy as np
from skimage.registration import phase_cross_correlation

from matplotlib import pyplot as plt
from Traversal import BadFit
import utils


class Row:
    xOverlap = 25 * 5
    overlapVec = np.array((0, xOverlap))
    acceptableDy = 20

    def __init__(self, maxRadius=None):
        self.maxRadius = maxRadius
        self.done = False
        self.moveDir = 1
        # always go right (1) then left (-1) each time from center

    def initCenter(self, centerPic, pxSize, centerPos, shift, zDiff):
        self.centerPic = centerPic
        self.pxSize = pxSize
        self.centerPos = centerPos  # (x,y,z)
        # (dy, dx) relative to the offset and last center pic. is None if first pic
        self.shift = shift
        self.zDiff = zDiff

        self.stitch = centerPic
        self.picShape = np.array(self.centerPic.shape)  # (y, x) in px
        self.stepX = (self.picShape[1] - Row.xOverlap) * self.pxSize  # positive X

        self.leftPt = np.array((0, 0))  # top left pont of stitch
        self.rightPt = np.array((0, self.picShape[1]))  # top right point of stitch
        self.centerPt = np.array((0, 0))  # top left of the center pic

    def prematureEdge(self, x):
        return self.maxRadius and abs(x - self.centerPos[0]) > self.maxRadius

    def atEdge(self, x, y, z):
        if self.moveDir == 1:
            self.edge = np.array([x - self.stepX, y, z])
            self.moveDir = -1
            print(f"X Edge is at {self.edge}")
        else:
            self.done = True

    def stitchRight(self, pic, shift):
        stitchPt = self.rightPt - Row.overlapVec + shift

        # put the point pic(0, 0) onto point self.stitch(stitchPt)
        self.stitch, stitchShift, picShift = utils.ptToPtStitch(
            self.stitch, stitchPt, pic
        )
        self.leftPt += stitchShift
        self.centerPt += stitchShift
        self.rightPt = np.array((0, self.picShape[1])) + picShift

        print(f"Left: {self.leftPt}, center: {self.centerPt}, right: {self.rightPt}")

    def stitchLeft(self, pic, shift):
        stitchPt = self.leftPt + Row.overlapVec + shift
        picPt = np.array((0, pic.shape[1]))
        # put the point pic(0, 0) onto point self.stitch(stitchPt)

        self.stitch, stitchShift, picShift = utils.ptToPtStitch(
            self.stitch, stitchPt, pic, picPt
        )
        self.leftPt = picShift
        self.centerPt += stitchShift
        self.rightPt += stitchShift

        print(f"Left: {self.leftPt}, center: {self.centerPt}, right: {self.rightPt}")

    def addToStitch(self, pic):
        """Stitches based on self.moveDir. Throws BadFit if bad stitch"""
        stitchRight = self.moveDir == 1
        if stitchRight:
            stitchArea = self.stitch[
                self.rightPt[0] : self.rightPt[0] + self.picShape[0], -Row.xOverlap :
            ]
            picArea = pic[:, : Row.xOverlap]
        else:
            stitchArea = self.stitch[
                self.leftPt[0] : self.leftPt[0] + self.picShape[0], : Row.xOverlap
            ]
            picArea = pic[:, -Row.xOverlap :]

        shift = phase_cross_correlation(stitchArea, picArea)[0].astype(int)
        if abs(shift[0]) > Row.acceptableDy:
            print(f"Fit not acceptable (dy={shift[0]}), trying again")
            raise BadFit
        pic += utils.getZDiff(shift, stitchArea, picArea)
        thread = threading.Thread(
            target=self.stitchRight if stitchRight else self.stitchLeft,
            args=(pic, shift),
        )
        thread.start()
