import time
from unittest.mock import patch
from garmin_font_scaler.core import FontProcessor, FontTask, ScreenConfig


def create_dummy_task(font_name, size):
    return FontTask(
        xml_node=None,
        font_id=f"{font_name}_{size}",
        font_name=font_name,
        fnt_filename=f"{font_name}-{size}.fnt",
        ttf_filename=f"{font_name}.ttf",
        reference_size=size,
        target_size=None,
        charset="012345",
    )


def setup_dummy_environment(tmp_path, font_names):
    fonts_dir = tmp_path / "resources" / "fonts"
    fonts_dir.mkdir(parents=True, exist_ok=True)
    for name in font_names:
        (fonts_dir / f"{name}.ttf").touch()


def test_batch_processing_benchmark(tmp_path):
    """
    Benchmarks the batching logic.
    """
    font_name = "Ubuntu-Regular"
    setup_dummy_environment(tmp_path, [font_name])

    processor = FontProcessor().with_project_dir(str(tmp_path))

    num_tasks = 100
    processor.font_tasks = [
        create_dummy_task(font_name, s) for s in range(10, 10 + num_tasks)
    ]

    # Updated Configuration
    processor.reference_config = ScreenConfig(280, 280, "round")
    processor.target_configs = [
        ScreenConfig(280, 280, "round"),
        ScreenConfig(454, 454, "round")
    ]

    start_time = time.perf_counter()

    with patch("subprocess.run") as mock_run, patch(
            "xml.etree.ElementTree.parse"
    ), patch("xml.etree.ElementTree.ElementTree.write"):
        processor.execute()

        # Verify optimization: 2 targets, 1 font source -> 2 calls (1 per target resolution)
        assert mock_run.call_count == 2

    end_time = time.perf_counter()
    duration = end_time - start_time

    total_ops = num_tasks * len(processor.target_configs)

    report_data = [
        (
            "Tasks Processed:",
            f"{num_tasks} fonts x {len(processor.target_configs)} targets",
        ),
        ("Total Operations:", f"{total_ops}"),
        (
            "Optimized Batch Calls:",
            f"{mock_run.call_count} (vs {total_ops} unoptimized)",
        ),
        ("Execution Time:", f"{duration:.4f} seconds"),
        ("Speed:", f"{num_tasks / duration:.0f} tasks/sec (simulated)"),
    ]

    col1_width = max(len(row[0]) for row in report_data)
    padding = 6

    formatted_lines = []
    for label, value in report_data:
        line = f"{label:<{col1_width}}{' ' * padding}{value}"
        formatted_lines.append(line)

    max_line_length = max(len(line) for line in formatted_lines)
    title = "PERFORMANCE BENCHMARK REPORT"
    separator_len = max(max_line_length, len(title))
    separator = "=" * separator_len

    print(f"\n\n{separator}")
    print(f"{title}")
    print(f"{separator}")
    for line in formatted_lines:
        print(line)
    print(f"{separator}\n")