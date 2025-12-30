import os
from garmin_font_scaler.core import FontProcessor, FontTask


def test_calculate_size():
    fp = FontProcessor().with_reference_diameter(280)
    assert fp._calculate_size(280, 280) == 280
    assert fp._calculate_size(50, 454) == 81
    assert fp._calculate_size(10, 218) == 8


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
