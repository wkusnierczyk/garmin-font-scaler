import os
from garmin_font_scaler.core import FontProcessor, FontTask, ScreenConfig


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
