class MaxContSearch:
    def __init__(self, z_a, z_b, direction, minContrast, subdivisions=25, avg=5):
        interval = self.zsToInterval(z_a, z_b, direction)
        (self.z_1, self.z_2) = interval
        self.direction = direction
        self.minContrast = minContrast
        self.subdivisions = subdivisions
        self.avg = avg

        # array of (cont, z)
        # always needs to return with 3 items with the max contrast in the middle
        # start with 2 because we index second last item
        self.contPts = [(0, 0), (0, self.z_1)]

    def setXYPos(self, x, y):
        self.x = x
        self.y = y

    def newContPt(self, cont, z):
        self.contPts.append((cont, z))

    def isAtLocalMaxCont(self):
        maxGreaterThanLast = self.contPts[-3][0] - self.contPts[-1][0] > 0.2
        maxGreaterThan2ndLast = self.contPts[-3][0] - self.contPts[-2][0] > 0.2
        maxIsNotNoise = self.contPts[-3][0] > self.minContrast
        return maxGreaterThanLast and maxGreaterThan2ndLast and maxIsNotNoise

    def getMaxContInterval(self):
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
