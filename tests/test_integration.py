import pytest
import xml.etree.ElementTree as ET
from unittest.mock import patch
from garmin_font_scaler.core import FontProcessor, FontScalerError

# Updated Sample XML with new JSON format
SAMPLE_XML = """
<resources>
    <fonts>
        <font id="TimeFont" filename="Ubuntu-Bold-60.fnt" />
    </fonts>
    <jsonData id="ScreenResolutions">{
        "reference": { "resolution": [280, 280], "shape": "round" },
        "targets": [
            { "resolution": [454, 454], "shape": "round" },
            { "resolution": [148, 205], "shape": "rectangle" }
        ]
    }</jsonData>
    <jsonData id="DefaultCharset">"0-9"</jsonData>
</resources>
"""


@pytest.fixture
def workspace(tmp_path):
    project_dir = tmp_path / "my_project"
    res_dir = project_dir / "resources"
    fonts_dir = res_dir / "fonts"
    fonts_dir.mkdir(parents=True)

    xml_file = fonts_dir / "fonts.xml"
    xml_file.write_text(SAMPLE_XML, encoding="utf-8")

    ttf_file = fonts_dir / "Ubuntu-Bold.ttf"
    ttf_file.write_text("dummy binary content")

    return project_dir


def test_pipeline_execution(workspace):
    project_dir = workspace

    processor = (
        FontProcessor().with_project_dir(str(project_dir)).with_font_tool_path("echo")
    )

    with patch("subprocess.run") as mock_run:
        processor.parse_source_xml().execute()

        assert mock_run.called
        args = mock_run.call_args[0][0]
        assert "-c" in args
        assert "0-9" in args

    # Check Output 1: Round 454
    output_dir_round = project_dir / "resources-round-454x454" / "fonts"
    assert output_dir_round.exists()

    # Check Output 2: Rectangle 148x205
    output_dir_rect = project_dir / "resources-rectangle-148x205" / "fonts"
    assert output_dir_rect.exists()

    output_xml = output_dir_rect / "fonts.xml"
    content = output_xml.read_text()
    assert "jsonData" not in content


STROKE_XML = """
<resources>
    <fonts>
        <font id="Time" filename="Ubuntu-Bold-60.fnt" />
        <font id="TimeLarge" filename="Ubuntu-Bold-80.fnt" />
        <font id="TimeHollow" filename="Ubuntu-Bold-60.fnt" stroke="1.2" />
    </fonts>
    <jsonData id="ScreenResolutions">{
        "reference": { "resolution": [416, 416], "shape": "round" },
        "targets": [
            { "resolution": [416, 416], "shape": "round" },
            { "resolution": [360, 360], "shape": "round" }
        ]
    }</jsonData>
</resources>
"""


def _stroke_workspace(tmp_path, xml):
    project_dir = tmp_path / "stroke_project"
    fonts_dir = project_dir / "resources" / "fonts"
    fonts_dir.mkdir(parents=True)
    (fonts_dir / "fonts.xml").write_text(xml, encoding="utf-8")
    (fonts_dir / "Ubuntu-Bold.ttf").write_text("dummy binary content")
    return project_dir


def _calls(project_dir):
    processor = FontProcessor().with_project_dir(str(project_dir))
    with patch("subprocess.run") as mock_run:
        processor.parse_source_xml().execute()
    return [call[0][0] for call in mock_run.call_args_list]


def test_stroke_gets_its_own_ttf2bmp_call(tmp_path):
    project_dir = _stroke_workspace(tmp_path, STROKE_XML)
    calls = _calls(project_dir)

    # Per target: one call for the two filled sizes, one for the hollow font.
    assert len(calls) == 4
    filled = [c for c in calls if "-stroke" not in c]
    hollow = [c for c in calls if "-stroke" in c]
    assert sorted(c[c.index("-s") + 1] for c in filled) == ["52,69", "60,80"]
    assert sorted(
        (c[c.index("-s") + 1], c[c.index("-stroke") + 1]) for c in hollow
    ) == [("52", "1.04"), ("60", "1.2")]


def _target_fonts(project_dir, target):
    path = project_dir / f"resources-{target}" / "fonts" / "fonts.xml"
    return {n.get("id"): n.attrib for n in ET.parse(path).getroot().iter("font")}


def test_stroke_target_xml(tmp_path):
    project_dir = _stroke_workspace(tmp_path, STROKE_XML)
    _calls(project_dir)

    fonts = _target_fonts(project_dir, "round-360x360")
    # The hollow font points at its own file; the filled one at the same size does not.
    assert fonts["TimeHollow"]["filename"] == "Ubuntu-Bold-52-stroke1p04.fnt"
    assert fonts["Time"]["filename"] == "Ubuntu-Bold-52.fnt"
    # stroke is the scaler's configuration and must not reach a compiled resource.
    assert all("stroke" not in attrib for attrib in fonts.values())


def test_strokes_at_one_size(tmp_path):
    xml = STROKE_XML.replace(
        '<font id="TimeHollow" filename="Ubuntu-Bold-60.fnt" stroke="1.2" />',
        '<font id="Thin" filename="Ubuntu-Bold-60.fnt" stroke="1.2" />'
        '<font id="ThinToo" filename="Ubuntu-Bold-60.fnt" stroke="1.2" />'
        '<font id="Thick" filename="Ubuntu-Bold-60.fnt" stroke="2.5" />',
    )
    project_dir = _stroke_workspace(tmp_path, xml)
    calls = _calls(project_dir)

    # Per target: the filled call and one per distinct stroke; equal strokes share one.
    assert len(calls) == 6
    fonts = _target_fonts(project_dir, "round-416x416")
    assert fonts["Thin"]["filename"] == "Ubuntu-Bold-60-stroke1p2.fnt"
    assert fonts["ThinToo"]["filename"] == "Ubuntu-Bold-60-stroke1p2.fnt"
    assert fonts["Thick"]["filename"] == "Ubuntu-Bold-60-stroke2p5.fnt"
    assert fonts["Time"]["filename"] == "Ubuntu-Bold-60.fnt"


def test_without_stroke_the_command_is_unchanged(tmp_path):
    xml = STROKE_XML.replace(
        '<font id="TimeHollow" filename="Ubuntu-Bold-60.fnt" stroke="1.2" />', ""
    )
    project_dir = _stroke_workspace(tmp_path, xml)
    calls = _calls(project_dir)
    ttf = str(project_dir / "resources" / "fonts" / "Ubuntu-Bold.ttf")
    out = str(project_dir / "resources-round-416x416" / "fonts")
    # The exact call main makes: no stroke option, the default charset, no padding.
    assert calls[0] == [
        "ttf2bmp",
        "-f",
        ttf,
        "-c",
        "0123456789:",
        "-hinting",
        "none",
        "-s",
        "60,80",
        "-o",
        out,
    ]


def test_invalid_stroke_is_refused(tmp_path):
    for bad in ("0", "-1", "wide", "nan", "inf", "1_0", " 1", "1e3", "2000", ""):
        xml = STROKE_XML.replace('stroke="1.2"', f'stroke="{bad}"')
        project_dir = _stroke_workspace(tmp_path / bad, xml)
        processor = FontProcessor().with_project_dir(str(project_dir))
        with pytest.raises(FontScalerError):
            processor.parse_source_xml()


def test_table_has_a_stroke_column_only_with_strokes(tmp_path):
    with_stroke = _stroke_workspace(tmp_path / "a", STROKE_XML)
    without = _stroke_workspace(
        tmp_path / "b",
        STROKE_XML.replace(
            '<font id="TimeHollow" filename="Ubuntu-Bold-60.fnt" stroke="1.2" />', ""
        ),
    )
    tables = {}
    for name, project_dir in (("with", with_stroke), ("without", without)):
        processor = (
            FontProcessor()
            .with_project_dir(str(project_dir))
            .with_table_filename("fonts.md")
        )
        with patch("subprocess.run"):
            processor.parse_source_xml().execute()
        tables[name] = (project_dir / "fonts.md").read_text()

    assert "Stroke" in tables["with"]
    assert "Ubuntu bold, hollow" in tables["with"]
    # The by-element table lists reference sizes, and so the reference stroke.
    assert "Ubuntu bold, hollow 1.2" in tables["with"]
    assert "1.04" in tables["with"]
    assert "Stroke" not in tables["without"]
    assert "hollow" not in tables["without"]
