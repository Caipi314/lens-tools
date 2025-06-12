from io import BytesIO
import time
import traceback
import dearpygui.dearpygui as dpg
from PIL import Image

from GlobalSettings import GlobalSettings

from KoalaController import KoalaController
import KoalaGui


def startFunc(height, func):
    try:
        KoalaGui.turnLive(False)
        host = KoalaController()
        host.setup()

        start = time.time()
        host.setLimit(h=height)
        func(host)
        end = time.time()
        print(f"Time: {end - start:.3f} seconds")
    except Exception as err:
        traceback.print_exc()
    finally:
        KoalaGui.turnLive(True)
        host.logout()


dpg.create_context()

# add a font registry
with dpg.font_registry():
    # first argument ids the path to the .ttf or .otf file
    defaultFont = dpg.add_font("./fonts/Work_Sans/static/WorkSans-Medium.ttf", 35)
    smallFont = dpg.add_font("./fonts/Work_Sans/static/WorkSans-light.ttf", 20)
    btnTextFont = dpg.add_font("./fonts/Work_Sans/static/WorkSans-Medium.ttf", 80)
    titleFont = dpg.add_font("./fonts/Work_Sans/static/WorkSans-SemiBold.ttf", 70)

# dpg.set_style_window_padding(0, 0)
# dpg.set_style_frame_padding(0, 0)
# Load gear icon (replace with your own image path)

#! Init textures
with dpg.texture_registry():
    icons = [
        "gear",
        "findFocus",
        "findCenter",
        "2dProfile",
        "3dMap",
        "stop",
    ]  # so path must be './icons/gear.png', and tag will be 'gear'
    for icon in icons:
        image = Image.open(f"./icons/{icon}.png").convert("RGBA")
        width, height = image.size
        image_data = image.tobytes()
        dpg.add_static_texture(width, height, image_data, tag=icon)


# def on_findFocusBtn_click():
#     dpg.configure_item("GoModal", show=True)
#     print("Find focus btn clicked")


# def on_findCenterBtn_click():
#     dpg.configure_item("GoModal", show=True)
#     print("Find center btn clicked")


# def on_2dProfileBtn_click():
#     dpg.configure_item("GoModal", show=True)
#     print("Map Diameter btn clicked")


# def on_3dMapBtn_click():
#     dpg.configure_item("GoModal", show=True)
#     print("Map Surface btn clicked")


def on_stopBtn_click():
    #! Do something
    print("STOP button clicked")


#! Styling
with dpg.theme() as global_theme:
    with dpg.theme_component(dpg.mvAll):
        dpg.add_theme_style(
            dpg.mvStyleVar_WindowPadding, 8, 0, category=dpg.mvThemeCat_Core
        )
        dpg.add_theme_style(
            dpg.mvStyleVar_WindowBorderSize, 0, category=dpg.mvThemeCat_Core
        )
dpg.bind_theme(global_theme)

with dpg.theme() as ModalTheme:
    with dpg.theme_component(dpg.mvAll):
        dpg.add_theme_color(dpg.mvThemeCol_WindowBg, (52, 152, 219, 255))  # RGBA format

with dpg.theme() as btnTheme:
    with dpg.theme_component(dpg.mvAll):
        dpg.add_theme_color(
            dpg.mvThemeCol_ChildBg,
            (83, 98, 105, 255),
        )  # background
        dpg.add_theme_color(
            dpg.mvThemeCol_Border,
            (167, 176, 181, 255),
        )  # optional border
        dpg.add_theme_style(dpg.mvStyleVar_ChildRounding, 6)
        dpg.add_theme_style(dpg.mvStyleVar_WindowPadding, 10, 10)

with dpg.theme() as btnStopTheme:
    with dpg.theme_component(dpg.mvAll):
        dpg.add_theme_color(
            dpg.mvThemeCol_ChildBg,
            (204, 43, 43, 255),
        )  # background
        dpg.add_theme_color(
            dpg.mvThemeCol_Border,
            (167, 176, 181, 255),
        )  # optional border
        dpg.add_theme_style(dpg.mvStyleVar_ChildRounding, 6)
        dpg.add_theme_style(dpg.mvStyleVar_WindowPadding, 10, 10)

with dpg.theme() as overlayBtn:
    with dpg.theme_component(dpg.mvButton):
        dpg.add_theme_color(dpg.mvThemeCol_Button, (0, 0, 0, 0))
        dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (138, 155, 163, 30))

with dpg.theme() as overlayStopBtn:
    with dpg.theme_component(dpg.mvButton):
        dpg.add_theme_color(dpg.mvThemeCol_Button, (0, 0, 0, 0))
        dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (235, 138, 138, 30))

with dpg.theme() as goBtn:
    with dpg.theme_component(dpg.mvButton):
        dpg.add_theme_color(dpg.mvThemeCol_Button, (77, 214, 91, 255))
        dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (116, 252, 130, 30))

with dpg.theme() as red_theme:
    with dpg.theme_component(dpg.mvInputInt):
        dpg.add_theme_color(dpg.mvThemeCol_FrameBg, (255, 0, 0, 255))  # Red background


def bigBtn(func, text, icon, width, height, imgMargin=0):
    with dpg.child_window(
        height=height,
        width=width,
        border=True,
        no_scrollbar=True,
        tag=f"btn-{icon}",
    ):
        with dpg.group(horizontal=True):
            text = dpg.add_text(text)
            dpg.bind_item_font(text, btnTextFont)
            if imgMargin:
                dpg.add_spacer(width=imgMargin)
            dpg.add_image(texture_tag=icon, width=height * 0.86, height=height * 0.86)
            dpg.add_button(
                label="",
                width=width,
                height=height,
                pos=(0, 0),
                callback=func,
                tag=f"overlayBtn-{icon}",
            )
    dpg.bind_item_theme(f"btn-{icon}", btnTheme)
    dpg.bind_item_theme(f"overlayBtn-{icon}", overlayBtn)


def stopBtn():
    height = 100
    width = 280
    with dpg.child_window(
        height=height,
        width=width,
        border=True,
        no_scrollbar=True,
        tag=f"btn-stop",
    ):
        with dpg.group(horizontal=True):
            with dpg.group():
                dpg.add_spacer(height=8)
                dpg.add_image(
                    texture_tag="stop", width=height * 0.6, height=height * 0.6
                )
            dpg.add_spacer(width=1)
            text = dpg.add_text("STOP")
            dpg.bind_item_font(text, btnTextFont)
            dpg.add_button(
                label="",
                width=width,
                height=height,
                pos=(0, 0),
                callback=on_stopBtn_click,
                tag=f"overlayBtn-stop",
            )
    dpg.bind_item_theme(f"btn-stop", btnStopTheme)
    dpg.bind_item_theme(f"overlayBtn-stop", overlayStopBtn)


settings = GlobalSettings()


def showSettingsModal():
    for settingKey in settings.keys():
        dpg.set_value(settingKey, settings[settingKey]["value"])
    dpg.configure_item("SettingsModal", show=True)


def showGoModal(funcID):
    settings.setFuncID(funcID)
    dpg.configure_item("GoModal", show=True)
    dpg.configure_item("shape", show=funcID in [4])
    dpg.configure_item("radius", show=funcID in [3, 4])
    dpg.configure_item("curvature", show=funcID in [2, 3, 4])


with dpg.window(tag="MainWindow", no_resize=True, no_move=True):
    # ? Title Area
    with dpg.group(horizontal=True):
        leftMargin = 200
        with dpg.child_window(
            width=leftMargin * 1.8,
            height=50,
            border=False,
            pos=(0, 0),
            no_scrollbar=True,
        ):
            version = dpg.add_text("V1 05/2025\nhttps://github.com/Caipi314/lens-tools")
            # https://github.com/Caipi314/lens-tools
            dpg.bind_item_font(version, smallFont)

        dpg.add_spacer(width=leftMargin * 0.2, tag="left_spacer")

        # Drawing layer for custom borders
        width = 335
        height = 70
        with dpg.drawlist(width=width, height=height, tag="border_drawlist"):
            dpg.draw_line(
                (0, 0),
                (0, height),
                color=(255, 255, 255, 255),
                thickness=3,
            )
            dpg.draw_line(
                (0 + width, 0),
                (0 + width, height),
                color=(255, 255, 255, 255),
                thickness=4,
            )
            dpg.draw_line(
                (0, height),
                (0 + width, height),
                color=(255, 255, 255, 255),
                thickness=4,
            )

        with dpg.child_window(
            width=width * 0.95,
            height=height,
            border=False,
            pos=(leftMargin * 2 + 25, -6),
            no_scrollbar=True,
        ):
            title = dpg.add_text("Lens Tools")
            dpg.bind_item_font(title, titleFont)
        dpg.add_spacer(width=leftMargin * 1.7, tag="right_spacer")
        with dpg.group():
            dpg.add_spacer(height=10)  # ← top margin here
            dpg.add_image_button(
                texture_tag="gear",
                width=40,
                height=40,
                callback=showSettingsModal,
            )

    dpg.add_spacer(height=10)
    dpg.add_separator()
    dpg.add_spacer(height=10)

    # ? Buttons
    with dpg.group(horizontal=True):
        bigBtn(
            lambda: showGoModal(1),
            "Find Focus",
            "findFocus",
            width=600,
            height=120,
            imgMargin=100,
        )
        bigBtn(
            lambda: showGoModal(2),
            "Find Top",
            "findCenter",
            width=550,
            height=120,
            imgMargin=118,
        )
    dpg.add_spacer(height=10)
    with dpg.group(horizontal=True):
        bigBtn(
            lambda: showGoModal(3), "Map Diameter", "2dProfile", width=600, height=120
        )
        bigBtn(lambda: showGoModal(4), "Map Surface", "3dMap", width=550, height=120)

    dpg.add_spacer(height=10)
    dpg.add_separator()
    dpg.add_spacer(height=10)

    # ? Footer Area
    with dpg.group(horizontal=True):
        stopBtn()
    dpg.bind_font(defaultFont)


with dpg.window(
    tag="GoModal",
    modal=True,
    show=False,
    no_title_bar=True,
    no_move=True,
    no_resize=True,
    width=500,
    height=500,
    pos=(350, 120),
):

    def onGo():
        curvatureMap = {
            "Traverse to Top": 1,
            "Traverse to Bottom": -1,
            "Start at current Position": 0,
        }
        heightInput = int(dpg.get_value("height_input"))
        radiusInput = float(dpg.get_value("radius_input"))
        curvatureInput = dpg.get_value("curvature_input")
        shapeInput = dpg.get_value("shape_input")
        checkbox = dpg.get_value("checkbox")

        curvature = curvatureMap[curvatureInput]
        height = heightInput * 1000  # mm to um
        radius = radiusInput * 1000  # mm to um
        circle = shapeInput == "Stitch Circle"

        if not checkbox:
            return print("x20 lens must be positioned")
        if height > 100:
            return print("Please enter in mm")
        if settings.funcID == 2 and curvature == 0:
            return print("Please select traverse to bottom or top")

        funcMap = {
            1: lambda k: k.maximizeFocus(),
            2: lambda k: k.traverseToExtreme(curvature),
            3: lambda k: k.mapProfile(curvature, radius),
            4: lambda k: k.mapArea(curvature, circle, radius),
        }
        # close the modal
        dpg.configure_item("GoModal", show=False)
        startFunc(height, funcMap[settings.funcID])

    dpg.add_text("Enter Specimen Height in mm:")
    text = dpg.add_text("(So the microscope doesn't hit it)")
    dpg.bind_item_font(text, smallFont)
    dpg.add_spacer(height=10)

    with dpg.group(horizontal=True):
        dpg.add_spacer(width=130)
        dpg.add_input_int(label="", tag="height_input", width=200, default_value=1)
        dpg.bind_item_theme("height_input", red_theme)
    dpg.add_spacer(height=18)

    with dpg.group(tag="radius", horizontal=True):
        dpg.add_text("Radius [mm]")
        dpg.add_spacer(width=20)
        dpg.add_input_float(label="", tag="radius_input", width=200, default_value=1)
    dpg.add_spacer(height=10)

    with dpg.group(tag="shape", horizontal=True):
        shapeField = dpg.add_combo(
            ["Stitch Circle", "Stitch Square"],
            tag="shape_input",
            width=400,
        )
        dpg.set_value(shapeField, "Stitch Circle")
    dpg.add_spacer(height=10)

    with dpg.group(tag="curvature", horizontal=True):
        curvatureField = dpg.add_combo(
            ["Traverse to Top", "Traverse to Bottom", "Start at current Position"],
            tag="curvature_input",
            width=400,
        )
        dpg.set_value(curvatureField, "Traverse to Top")
    dpg.add_spacer(height=10)

    with dpg.group(horizontal=True):
        dpg.add_checkbox(tag="checkbox", label="   x20 Lens is in position")
    dpg.add_spacer(height=18)

    with dpg.group(horizontal=True):
        dpg.add_button(
            label="Cancel",
            callback=lambda: dpg.configure_item("GoModal", show=False),
        )
        dpg.add_spacer(width=280)
        dpg.add_button(label="Start", callback=onGo, tag="goBtn")
    dpg.bind_item_theme("goBtn", goBtn)


with dpg.window(
    tag="SettingsModal",
    modal=True,
    no_resize=True,
    show=False,
    no_title_bar=True,
    no_move=True,
    width=700,
    height=600,
    pos=(300, 30),
):

    def settingRow(settingKey):
        name = settings[settingKey]["name"]
        type = settings[settingKey]["type"]
        initialValue = settings[settingKey]["value"]
        description = settings[settingKey]["description"]

        def onChange(_sender, value):
            settings.stageValue(settingKey, value)

        # name, description, initialValue
        with dpg.group(horizontal=True):
            dpg.add_text(name)
            dpg.add_spacer(width=30)
            if type == "int":
                dpg.add_input_int(
                    tag=settingKey,
                    width=180,
                    default_value=initialValue,
                    callback=onChange,
                )
            elif type == "float":
                dpg.add_input_float(
                    tag=settingKey,
                    width=180,
                    default_value=initialValue,
                    callback=onChange,
                )
            else:
                dpg.add_input_text(
                    tag=settingKey,
                    width=180,
                    default_value=initialValue,
                    callback=onChange,
                )
        desc = dpg.add_text(description, wrap=500)
        dpg.bind_item_font(desc, smallFont)
        dpg.add_spacer(height=20)

    def onCancel():
        dpg.configure_item("SettingsModal", show=False)

    def onReset():
        settings.reset()
        showSettingsModal()

    def onSave():
        settings.writeStaged()
        dpg.configure_item("SettingsModal", show=False)

    title = dpg.add_text("Settings")
    dpg.bind_item_font(title, titleFont)
    dpg.add_spacer(height=40)

    for settingKey in settings.keys():
        settingRow(settingKey)
    with dpg.group(horizontal=True):
        dpg.add_button(label="Cancel", callback=onCancel)
        dpg.add_spacer(width=88)
        dpg.add_button(label="Reset", callback=onReset)
        dpg.add_spacer(width=88)
        dpg.add_button(label="Save", callback=onSave, tag="saveBtn")

dpg.create_viewport(title="Lens Tools", width=1200, height=800)

dpg.setup_dearpygui()
dpg.show_viewport()

dpg.set_primary_window("MainWindow", True)
dpg.set_viewport_resizable(False)

dpg.start_dearpygui()
dpg.destroy_context()
