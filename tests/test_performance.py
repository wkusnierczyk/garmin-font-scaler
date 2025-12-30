import pytest
import time
import os
from unittest.mock import patch
from garmin_font_scaler.core import FontProcessor, FontTask


def create_dummy_task(font_name, size):
    return FontTask(
        xml_node=None,
        font_id=f"{font_name}_{size}",
        font_name=font_name,
        fnt_filename=f"{font_name}-{size}.fnt",
        ttf_filename=f"{font_name}.ttf",
        reference_size=size,
        target_size=None,
        charset="012345"
    )


def setup_dummy_environment(tmp_path, font_names):
    fonts_dir = tmp_path / "resources" / "fonts"
    fonts_dir.mkdir(parents=True, exist_ok=True)
    for name in font_names:
        (fonts_dir / f"{name}.ttf").touch()


def test_batch_processing_benchmark(tmp_path):
    """
    Benchmarks the batching logic.
    Simulates processing 100 font sizes and measures execution time.
    """
    # 1. Setup
    font_name = "Ubuntu-Regular"
    setup_dummy_environment(tmp_path, [font_name])

    processor = FontProcessor().with_project_dir(str(tmp_path))

    # Generate 100 tasks (sizes 10 to 110)
    num_tasks = 100
    processor.font_tasks = [create_dummy_task(font_name, s) for s in range(10, 10 + num_tasks)]
    processor.target_diameters = [280, 454]  # 2 targets = 200 total outputs
    processor.reference_diameter = 280

    # 2. Execution & Timing
    start_time = time.perf_counter()

    with patch("subprocess.run") as mock_run, \
            patch("xml.etree.ElementTree.parse"), \
            patch("xml.etree.ElementTree.ElementTree.write"):

        processor.execute()

        # Verify optimization logic
        assert mock_run.call_count == 2

    end_time = time.perf_counter()
    duration = end_time - start_time

    # 3. Report
    total_ops = num_tasks * len(processor.target_diameters)

    # Define raw data
    report_data = [
        ("Tasks Processed:", f"{num_tasks} fonts x {len(processor.target_diameters)} targets"),
        ("Total Operations:", f"{total_ops}"),
        ("Optimized Batch Calls:", f"{mock_run.call_count} (vs {total_ops} unoptimized)"),
        ("Execution Time:", f"{duration:.4f} seconds"),
        ("Speed:", f"{num_tasks / duration:.0f} tasks/sec (simulated)")
    ]

    # Calculate widths for alignment
    col1_width = max(len(row[0]) for row in report_data)
    padding = 6  # Space between columns

    # Build formatted strings
    formatted_lines = []
    for label, value in report_data:
        # Left-align label within col1_width, then add padding and value
        line = f"{label:<{col1_width}}{' ' * padding}{value}"
        formatted_lines.append(line)

    # Calculate total width for the separator line
    max_line_length = max(len(l) for l in formatted_lines)
    title = "PERFORMANCE BENCHMARK REPORT"
    # Ensure separator is at least as long as title or lines
    separator_len = max(max_line_length, len(title))
    separator = "=" * separator_len

    # Print Report
    print(f"\n\n{separator}")
    print(f"{title}")
    print(f"{separator}")
    for line in formatted_lines:
        print(line)
    print(f"{separator}\n")