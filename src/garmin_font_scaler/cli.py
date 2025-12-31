import argparse
import sys
from garmin_font_scaler.core import FontProcessor, FontScalerError, DEFAULT_PROJECT_DIR


class AboutAction(argparse.Action):
    """Custom action to print about info to stderr and exit."""

    def __init__(self, option_strings, dest, **kwargs):
        super().__init__(option_strings, dest, nargs=0, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        info = (
            "garmin-font-scaler: bitmap font scaling automation for Garmin screen dimensions\n"
            "├─ developer:  mailto:waclaw.kusnierczyk@gmail.com\n"
            "├─ source:     https://github.com/wkusnierczyk/garmin-font-scaler\n"
            "└─ licence:    MIT https://opensource.org/licenses/MIT"
        )
        print(info, file=sys.stderr)
        sys.exit(0)


def main():
    parser = argparse.ArgumentParser(
        description="Garmin Font Scaler",
        usage="%(prog)s [options]",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # The custom action triggers immediately when encountered
    parser.add_argument(
        "--about", action=AboutAction, help="Show about information and exit"
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
