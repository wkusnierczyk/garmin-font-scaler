import pytest
from unittest.mock import patch
from garmin_font_scaler.core import FontProcessor

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