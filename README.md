# A Guide to lens-tools by Cai Siegel

## Quickstart "I want to map a lens"
1. Open Koala (username: "user", password: "user")
1. Start "Remote Mode" by clicking green button in menubar
1. Ensure x20 magnification is selected
1. Using the joystick, roughly place the microscope lens over your specimen (z height doesn't matter)
1. Start lens-tools with `python gui.py`
1. Select your function and settings and hit go
1. A folder will open with the results and analysis of your map

Check out **Troubleshooting** section if not working properly.

# Safety Warning!
### **If the big crank on the top of the microscope has been turned, or you suspect it has. ___You must recalibrate the `Maximum Safe Z` value in settings___.**

Procedure:
1. Ensure the 20x objective selected
1. Using the joystick move the stage so its *just* misses the stage (the closer, the better).
1. Record the Z value **read from the joystick** (Koala will show a wrong value)
1. Write that number to Settings > `Maximum Safe Z`


## Troubleshooting
#### If it seems nothing is happening
Close and reopen Remote Mode Window in Koala, and restart `gui.py`

#### If it says "reconstruction is live" and quits
Stop reconstruction mode by clicking the blue play button in the Koala menubar.


## Background

Mapping an entire lens would be very helpful, but the stock LynceeTec software can't handle it because lenses have sag.
The microscope has to refocus every time the lens surface slopes out of the depth of focus, and Koala can't handle that.

At first I tested the limits of mapping with just Koala, and it turns out you can map a 1D line along the diameter in under a few hours.
Instructions are included under `./pdfs/Measuring with Sag on the LynceeTec.pdf`

Then I dug into the api (detailed in `./pdfs/Koala API Reference.pdf`) and built the same functionality but better than Koala in 3 ways:

1. If you are currently focused, you can guess where the focus of your next step is by doing a linear fit.
(This way you have a good guess of where the next place of focus is going to be).
2. If you are "half" focused, you can go up and down a bit and see which way increases the focus slightly, and search in that direction
(This way you don't have to search for focus on your entire range every time).
3. Make a map of the specimen going from the center out in all directions.
(This way you don't need to do math to start in the top left corder of your final stitch, and the whole map is not garbage if focus is lost once).

**These improvements result in a x60 speedup for mapping lenses with significant sag.**

For a 45mm Diameter Lens:
| | 1D Line Along Center | 2D Map of entire area (projected) |
|-|----------|-----|
| Koala: | 2-3 hrs    | 28 days  |
| Lens-tools:	| 2.5 mins      | 13 hrs  |




I took on this project as a volunteer in May-June 2025 but it was cut short by the escalations of June 13, 2025 when I could not longer come into the lab.

Here are a list of things that would have been done in my remaining time:
1. Run 10+ hour tests to see how the app handles really large files (basic resizing is implemented and down-samples until file size is under 100mb)
1. Package the app into a desktop app so it doesn't need to be run from the console.
1. Show console logs on the GUI. (now just appended to `log.txt`)


## Reading and Editing the Code
### File Structure and Ownership

### Important Functions

### Non-Obvious Things Worth Knowing

## Future Improvements
* Implementing a 2-seam-stitch over of a 1-seam-stitch currently implemented.
Here, a cross correlation between 2 overlap sections is computed and is alpha blended across all overlap

<!--
GUIDE TODO
[x] Put in `Measuring with Sag on the LynceeTec.pdf`
[x] Put in `Koala API Reference.pdf`
[x] Fix time table
[x] --Underline safety warning--
[ ] Write Section: Reading and Editing the Code
 -->