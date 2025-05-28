class MaxContSearch:
    def __init__(
        self, z_a, z_b, direction, minContrast, subdivisions=None, step=None, avg=5
    ):
        interval = self.zsToInterval(z_a, z_b, direction)
        (self.z_1, self.z_2) = interval
        self.direction = direction
        self.minContrast = minContrast
        self.avg = avg
        self.subdivisions = subdivisions
        if step != None:
            self.subdivisions = int(abs(z_a - z_b) / step)
        if self.subdivisions == None:
            raise Exception("Must provide subdivisions or step")

        # array of (cont, z)
        # always needs to return with 3 items with the max contrast in the middle
        # start with 2 because we index second last item
        self.contPts = [(-1, -1), (-1, self.z_1)]
        self.reallyGoodCont = 10  # ... change?

    def logXYPos(self, x, y):
        self.x = x
        self.y = y

    def newContPt(self, cont, z):
        self.contPts.append((cont, z))

    def isAtLocalMaxCont(self):
        maxGreaterThanLast = self.contPts[-3][0] - self.contPts[-1][0] > 0.1
        maxGreaterThan2ndLast = self.contPts[-3][0] - self.contPts[-2][0] > 0.1
        maxIsNotNoise = self.contPts[-3][0] > self.minContrast
        return maxGreaterThanLast and maxGreaterThan2ndLast and maxIsNotNoise

    def isStillIncreasing(self):
        conts = [pt[0] for pt in self.contPts]
        lastIsMax = max(conts) in [
            self.contPts[-1][0],
            self.contPts[-2][0],
            self.contPts[-3][0],
        ]
        # maxIsNotNoise = self.contPts[-1][0] > self.minContrast
        return lastIsMax

    def allNonNoise(self):
        conts = [pt[0] for pt in self.contPts if -1 not in pt]
        allAboveMin = min(conts) > self.minContrast
        return allAboveMin or min(conts) > self.reallyGoodCont

    def getTotalMaxContInterval(self):
        # Find the point with the maximum contrast
        max_idx = max(range(len(self.contPts)), key=lambda i: self.contPts[i][0])
        return self.contPts[max_idx - 1 : max_idx + 1]

    def getRecentMaxContInterval(self):
        self.maxCont = self.contPts[-3][0]
        self.maxContInterval = list(self.contPts)[-4:-1]
        print(f"Found max contrast = {self.maxCont:.2f}")
        return self.maxContInterval

    def zsToInterval(self, z_a, z_b, direction):
        """Returns in the interval going from z_1 to z_2 where the order is based on direction"""
        return (
            (min(z_a, z_b), max(z_a, z_b))
            if direction == 1
            else (max(z_a, z_b), min(z_a, z_b))
        )

    def extend(self, dist):
        stepSize = abs(self.z_2 - self.z_1) / self.subdivisions
        self.subdivisions = dist // stepSize
        self.z_1 = self.z_2
        self.z_2 = self.z_2 + dist * self.direction
