import argparse
import sys
from .core import FontProcessor, FontScalerError, DEFAULT_PROJECT_DIR


def main():
    parser = argparse.ArgumentParser(
        description="Garmin Font Scaler",
        usage="%(prog)s [options]",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "--project-dir",
        default=DEFAULT_PROJECT_DIR,
        help="Base directory of the Garmin project (containing 'resources' folder)",
    )

    parser.add_argument(
        "--resources-dir",
        default="resources",
        help="Relative path to resources directory",
    )

    parser.add_argument(
        "--fonts-subdir", default="fonts", help="Relative path to fonts subdirectory"
    )

    parser.add_argument(
        "--xml-file", default="fonts.xml", help="Filename of the fonts XML"
    )

    parser.add_argument(
        "--reference-diameter", type=int, default=280, help="Reference screen diameter"
    )

    parser.add_argument(
        "--target-diameters",
        help="Comma-separated list of target diameters (overrides XML config)",
    )

    parser.add_argument(
        "--tool-path", default="ttf2bmp", help="Path to ttf2bmp executable"
    )

    parser.add_argument(
        "--table",
        nargs="?",
        const="-",  # Special value indicating STDOUT
        default=None,
        help="Generate markdown table of sizes (writes to stdout if no file is specified)",
    )

    args = parser.parse_args()

    try:
        (
            FontProcessor()
            .with_project_dir(args.project_dir)
            .with_resources_dir(args.resources_dir)
            .with_fonts_subdir(args.fonts_subdir)
            .with_xml_file_name(args.xml_file)
            .with_reference_diameter(args.reference_diameter)
            .with_target_diameters(args.target_diameters)
            .with_font_tool_path(args.tool_path)
            .with_table_filename(args.table)
            .parse_source_xml()
            .execute()
        )
    except FontScalerError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
