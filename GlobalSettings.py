import copy
import json
from pathlib import Path


# Singleton pattern
class GlobalSettings:
    _instance = None
    defaultSettings = {
        "IDEAL_NOISE_CUTOFF": {
            "name": "Noise Contrast Cutoff",
            "type": "float",
            "value": 2.2,
            "stagedVal": None,
            "defaultValue": 2.2,
            "description": "Contrast values under this value will be considered as noise.",
        },
        "ABS_MAX_Z": {
            "name": "Maximum Safe Z",
            "type": "int",
            "value": 27175,
            "stagedVal": None,
            "defaultValue": 27175,
            "description": "The maximum value of Z (read by the joystick in um), so that the 20x lens doesn't hit the stage. MUST RECALIBRATE IF THE CRANK IS TURNED",
        },
        "FIND_DIR_DIST": {
            "name": "Find Direction Step Size",
            "type": "int",
            "value": 25,
            "stagedVal": None,
            "defaultValue": 25,
            "description": "The small distance in um to go up and down to see if the contrast increases.",
        },
        "FAST_MOVE_REL_TIME": {
            "name": "Fast Relative Move Wait Time",
            "type": "float",
            "value": 0.4,
            "stagedVal": None,
            "defaultValue": 0.4,
            "description": "Time to wait for a fast (small) relative move in seconds. No reason to go over 0.6.",
        },
    }

    filePath = Path("./settings.json")

    def __new__(cls, *args, **kwargs):
        if cls._instance == None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if GlobalSettings.filePath.exists():
            self.settings = self.read()
        else:
            self.writeDefault()
            self.settings = copy.deepcopy(GlobalSettings.defaultSettings)

    #! 'Load' means read from file, 'Save' means write to file
    def writeDefault(self):
        with open(GlobalSettings.filePath.as_posix(), "w") as json_file:
            json.dump(GlobalSettings.defaultSettings, json_file, indent=2)

    def write(self):
        with open(GlobalSettings.filePath.as_posix(), "w") as json_file:
            json.dump(self.settings, json_file, indent=2)

    def read(self):
        with open(GlobalSettings.filePath.as_posix(), "r") as json_file:
            return json.load(json_file)

    def keys(self):
        return self.settings.keys()

    def stageValue(self, key, value):
        self.settings[key]["stagedVal"] = value

    def reset(self):
        self.writeDefault()
        self.settings = copy.deepcopy(GlobalSettings.defaultSettings)

    def writeStaged(self):
        for key in self.keys():
            stagedVal = self.settings[key]["stagedVal"]
            if not stagedVal == None:
                self.settings[key]["value"] = stagedVal
            self.settings[key]["stagedVal"] = None
        self.write()

    def get(self, key):
        return self.settings[key]["value"]

    def __getitem__(self, key):
        # Enable dict-style access. settings['ABS_MAX_Z']
        return self.settings[key]
