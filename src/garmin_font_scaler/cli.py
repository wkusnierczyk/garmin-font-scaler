import argparse
import sys

from .core import (FontProcessor,
                   FontScalerError,
                   DEFAULT_PROJECT_DIR,
                   DEFAULT_RESOURCES_DIR,
                   DEFAULT_FONTS_SUBDIR,
                   DEFAULT_XML_FILENAME,
                   DEFAULT_REFERENCE_DIAMETER,
                   DEFAULT_TOOL_PATH,
                   DEFAULT_TABLE_FILENAME)


def main():
    parser = argparse.ArgumentParser(
        description="Garmin Font Scaler",
        usage="%(prog)s [options]",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("--project-dir",
                        default=DEFAULT_PROJECT_DIR,
                        help="Base directory of the Garmin project containing the 'resources' directory")
    parser.add_argument("--resources-dir",
                        default=DEFAULT_RESOURCES_DIR,
                        help="Relative path to resources directory")
    parser.add_argument("--fonts-subdir",
                        default=DEFAULT_FONTS_SUBDIR,
                        help="Relative path to fonts subdirectory")
    parser.add_argument("--xml-file",
                        default=DEFAULT_XML_FILENAME,
                        help="Filename of the fonts XML")
    parser.add_argument("--reference-diameter",
                        type=int,
                        default=DEFAULT_REFERENCE_DIAMETER,
                        help="Reference screen diameter")
    parser.add_argument("--target-diameters",
                        help="Comma-separated list of target diameters")
    parser.add_argument("--tool-path",
                        default=DEFAULT_TOOL_PATH,
                        help="Path to ttf2bmp executable")
    parser.add_argument("--table",
                        nargs='?',
                        const=DEFAULT_TABLE_FILENAME,
                        default=DEFAULT_TABLE_FILENAME,
                        help=f"Generate markdown table of sizes")

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