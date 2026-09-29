import dataclasses
import os

from garmin_font_scaler.core import MIN_STROKE, FontProcessor, FontTask, ScreenConfig


def test_calculate_size():
    fp = FontProcessor()

    # Reference: 100x200 (Ref dimension = max(100, 200) = 200)
    fp.reference_config = ScreenConfig(width=100, height=200, shape="test")

    # Case 1: Target same as reference
    target_same = ScreenConfig(width=100, height=200, shape="test")
    # 20 * (200/200) = 20
    assert fp._calculate_size(20, target_same) == 20

    # Case 2: Target 50x30 (Target dimension = min(50, 30) = 30)
    # 20 * (30/200) = 20 * 0.15 = 3
    target_small = ScreenConfig(width=50, height=30, shape="test")
    assert fp._calculate_size(20, target_small) == 3

    # Case 3: Target 280x280 round
    # Ref 200. Target 280. Scale = 1.4. Size 20 -> 28
    fp.reference_config = ScreenConfig(width=200, height=200, shape="round")
    target_round = ScreenConfig(width=280, height=280, shape="round")
    assert fp._calculate_size(20, target_round) == 28


def test_resource_path_construction():
    fp = (
        FontProcessor()
        .with_resources_dir("my_res")
        .with_fonts_subdir("my_fonts")
        .with_xml_file_name("config.xml")
    )

    # Paths are relative to CWD by default
    expected = os.path.join(".", "my_res", "my_fonts", "config.xml")
    assert fp.xml_file_path == expected


def test_humanize_names():
    fp = FontProcessor()

    task = FontTask(None, "TimeFont", "Ubuntu-Regular", "", "", 0, 0, "")
    el, font = fp._humanize_names(task)
    assert el == "Time"
    assert font == "Ubuntu regular"

    task = FontTask(None, "SingleLineHourFont", "SUSEMono-Bold", "", "", 0, 0, "")
    el, font = fp._humanize_names(task)
    assert el == "Single line hour"
    assert font == "SUSEMono bold"


def _stroke_task(stroke):
    return FontTask(
        None,
        "TimeHollow",
        "Face-Regular",
        "",
        "",
        54,
        None,
        "",
        reference_stroke=stroke,
    )


def test_calculate_stroke_scales_with_the_screen():
    fp = FontProcessor()
    fp.reference_config = ScreenConfig(width=416, height=416, shape="round")

    # Same factor as the size, but not rounded to whole pixels.
    assert fp._calculate_stroke(_stroke_task(1.2), fp.reference_config) == 1.2
    target = ScreenConfig(width=360, height=360, shape="round")
    assert fp._calculate_stroke(_stroke_task(1.2), target) == 1.04
    target = ScreenConfig(width=448, height=486, shape="rectangle")
    assert fp._calculate_stroke(_stroke_task(1.2), target) == 1.29

    # A filled font has no stroke at any size.
    assert fp._calculate_stroke(_stroke_task(None), target) is None


def test_calculate_stroke_never_goes_below_ttf2bmp_minimum():
    fp = FontProcessor()
    fp.reference_config = ScreenConfig(width=416, height=416, shape="round")
    tiny = ScreenConfig(width=40, height=40, shape="round")
    assert fp._calculate_stroke(_stroke_task(1.0), tiny) == MIN_STROKE


def test_format_stroke_spells_like_go():
    # ttf2bmp names its output with Go's shortest round-trip formatting
    # (strconv.FormatFloat(w, 'f', -1, 64)), so the scaler must spell the width the
    # same way to find the files it asked for. These are the strings Go writes.
    fp = FontProcessor()
    assert fp._format_stroke(1.0) == "1"
    assert fp._format_stroke(1.2) == "1.2"
    assert fp._format_stroke(0.125) == "0.125"
    assert fp._format_stroke(2.25) == "2.25"
    assert fp._format_stroke(1.234) == "1.234"
    assert fp._format_stroke(1000.0) == "1000"


def test_target_fnt_filename():
    fp = FontProcessor()
    filled = FontTask(None, "Time", "Face-Regular", "", "", 54, 47, "")
    assert fp._target_fnt_filename(filled) == "Face-Regular-47.fnt"
    hollow = dataclasses.replace(filled, reference_stroke=1.2, target_stroke=1.04)
    assert fp._target_fnt_filename(hollow) == "Face-Regular-47-stroke1p04.fnt"
    hollow = dataclasses.replace(filled, reference_stroke=1.0, target_stroke=1.0)
    assert fp._target_fnt_filename(hollow) == "Face-Regular-47-stroke1.fnt"


def test_humanize_names_marks_hollow_fonts():
    fp = FontProcessor()
    _, font = fp._humanize_names(_stroke_task(1.2))
    assert font == "Face regular, hollow"


def test_calculate_stroke_keeps_the_configured_value_at_the_reference():
    fp = FontProcessor()
    fp.reference_config = ScreenConfig(width=416, height=416, shape="round")
    # Rounding is for scaled values only: what the author wrote is passed as written.
    assert fp._calculate_stroke(_stroke_task(1.234), fp.reference_config) == 1.234
    assert fp._calculate_stroke(_stroke_task(0.125), fp.reference_config) == 0.125


def test_calculate_stroke_warns_only_below_the_minimum(capsys):
    fp = FontProcessor()
    fp.reference_config = ScreenConfig(width=416, height=416, shape="round")
    # Exactly the minimum, at the reference: no warning.
    fp._calculate_stroke(_stroke_task(0.125), fp.reference_config)
    assert "minimum" not in capsys.readouterr().err
    # 0.144 scales to 0.1246 at 360x360: below the minimum, so clamped, with a warning.
    target = ScreenConfig(width=360, height=360, shape="round")
    assert fp._calculate_stroke(_stroke_task(0.144), target) == MIN_STROKE
    assert "minimum" in capsys.readouterr().err
    # 0.145 scales to 0.1255: above the minimum, rounded to 0.13, no warning.
    assert fp._calculate_stroke(_stroke_task(0.145), target) == 0.13
    assert "minimum" not in capsys.readouterr().err
    # The report asks without warning.
    fp._calculate_stroke(_stroke_task(0.01), target, warn=False)
    assert capsys.readouterr().err == ""
