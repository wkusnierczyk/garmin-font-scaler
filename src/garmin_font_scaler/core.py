import dataclasses
import json
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

from collections import defaultdict
from typing import Optional, Tuple, List

# --- Configuration Constants ---

DEFAULT_PROJECT_DIR = "."
DEFAULT_RESOURCES_DIR = "resources"
DEFAULT_FONTS_SUBDIR = "fonts"
DEFAULT_XML_FILENAME = "fonts.xml"
DEFAULT_TOOL_PATH = "ttf2bmp"

# Default fallback if XML is missing config
DEFAULT_REFERENCE_CONFIG = {"resolution": [280, 280], "shape": "round"}

DEFAULT_CHARSET = "0123456789:"
DEFAULT_HINTING = "none"

# New Directory Template: resources-{shape}-{width}x{height}
TARGET_RESOURCES_DIR_TEMPLATE = "resources-{shape}-{width}x{height}"

XML_DEFAULT_CHARSET_NODE = "DefaultCharset"
XML_FONT_CHARSETS_NODE = "FontCharsets"
XML_SCREEN_RESOLUTIONS_NODE = "ScreenResolutions"

JSON_REFERENCE_KEY = "reference"
JSON_TARGETS_KEY = "targets"
JSON_RESOLUTION_KEY = "resolution"
JSON_SHAPE_KEY = "shape"
JSON_FONT_ID_KEY = "fontId"
JSON_CHARSET_KEY = "fontCharset"

XML_FONT_NODE_PATTERN = ".//font"
XML_FONT_NODE_ID_ATTRIBUTE = "id"
XML_FONT_NODE_FILENAME_ATTRIBUTE = "filename"

XML_JSON_NODE_PATTERN = ".//jsonData"
XML_JSON_NODE_ID_ATTRIBUTE = "id"

XML_ENCODING = "UTF-8"

FONT_TOOL_SOURCE_TTF_OPTION = "-f"
FONT_TOOL_CHARSET_OPTION = "-c"
FONT_TOOL_HINTING_OPTION = "-hinting"
FONT_TOOL_SIZE_OPTION = "-s"
FONT_TOOL_OUTPUT_OPTION = "-o"
FONT_TOOL_PADDING_OPTION = "-p"

FNT_FILENAME_PARSE_REGEX = r"^(.*)-(\d+)\.fnt$"

DEFAULT_TABLE_FILENAME = "fonts.md"


# --- Exceptions ---


class FontScalerError(Exception):
    """Base exception for Font Scaler errors."""

    pass


# --- Data Structures ---


@dataclasses.dataclass
class FontTask:
    xml_node: ET.Element
    font_id: str
    font_name: str
    fnt_filename: str
    ttf_filename: str
    reference_size: int
    target_size: Optional[int]
    charset: str


@dataclasses.dataclass
class ScreenConfig:
    width: int
    height: int
    shape: str

    @property
    def key(self):
        return f"{self.shape}-{self.width}x{self.height}"


# --- Core Logic ---


class FontProcessor:
    def __init__(self):
        self.project_dir = DEFAULT_PROJECT_DIR
        self.resources_dir = DEFAULT_RESOURCES_DIR
        self.fonts_subdir = DEFAULT_FONTS_SUBDIR
        self.xml_file_name = DEFAULT_XML_FILENAME
        self.font_tool_path = DEFAULT_TOOL_PATH
        self.font_tool_padding = None

        self.resources_fonts_path = ""
        self.xml_file_path = ""
        self._set_resources_paths()

        # Defaults
        self.reference_config = ScreenConfig(
            width=DEFAULT_REFERENCE_CONFIG["resolution"][0],
            height=DEFAULT_REFERENCE_CONFIG["resolution"][1],
            shape=DEFAULT_REFERENCE_CONFIG["shape"],
        )
        self.target_configs: List[ScreenConfig] = []
        self.font_tasks = []

        self.table_filename = None

    def with_project_dir(self, project_dir=None):
        if project_dir:
            self.project_dir = project_dir
            self._set_resources_paths()
        return self

    def with_resources_dir(self, resources_dir=None):
        if resources_dir:
            self.resources_dir = resources_dir
            self._set_resources_paths()
        return self

    def with_fonts_subdir(self, fonts_subdir=None):
        if fonts_subdir:
            self.fonts_subdir = fonts_subdir
            self._set_resources_paths()
        return self

    def with_xml_file_name(self, xml_file_name=None):
        if xml_file_name:
            self.xml_file_name = xml_file_name
            self._set_resources_paths()
        return self

    def _set_resources_paths(self):
        self.resources_fonts_path = os.path.join(
            self.project_dir, self.resources_dir, self.fonts_subdir
        )
        self.xml_file_path = os.path.join(self.resources_fonts_path, self.xml_file_name)
        return self

    def with_font_tool_path(self, font_tool_path=None):
        if font_tool_path:
            self.font_tool_path = font_tool_path
        return self

    def with_font_tool_padding(self, font_tool_padding=None):
        if font_tool_padding is not None:
            self.font_tool_padding = font_tool_padding
        return self

    def with_table_filename(self, table_filename=None):
        self.table_filename = table_filename
        return self

    def _load_json_data(self, node: ET.Element):
        """
        Helper to load JSON data from a jsonData node.
        Prioritizes the 'filename' attribute (external file) over inline text content.
        """
        if node is None:
            return None

        # Strategy 1: External File via 'filename' attribute
        filename = node.get("filename")
        if filename:
            # Resolve path relative to the XML file location
            base_dir = os.path.dirname(os.path.abspath(self.xml_file_path))
            json_path = os.path.join(base_dir, filename)

            if not os.path.exists(json_path):
                raise FontScalerError(f"External JSON file not found: {json_path}")

            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except json.JSONDecodeError as e:
                raise FontScalerError(
                    f"Error parsing external JSON file '{json_path}': {e}"
                )

        # Strategy 2: Inline Content
        if node.text and node.text.strip():
            return json.loads(node.text)

        return None

    def parse_source_xml(self):
        if not os.path.exists(self.xml_file_path):
            raise FontScalerError(f"Font xml file '{self.xml_file_path}' not found.")

        try:
            tree = ET.parse(self.xml_file_path)
            root = tree.getroot()

            # 1. Parse Screen Resolutions
            resolutions_node = self._find_json_node(root, XML_SCREEN_RESOLUTIONS_NODE)
            if resolutions_node is None:
                raise FontScalerError(
                    f"<jsonData id='{XML_SCREEN_RESOLUTIONS_NODE}'> not found in XML."
                )

            resolution_config = self._load_json_data(resolutions_node)
            if not resolution_config:
                raise FontScalerError(
                    f"Content for {XML_SCREEN_RESOLUTIONS_NODE} is empty or invalid."
                )

            # Parse Reference
            reference_data = resolution_config.get(JSON_REFERENCE_KEY)
            if not reference_data:
                raise FontScalerError(
                    f"Invalid {XML_SCREEN_RESOLUTIONS_NODE}: Missing '{JSON_REFERENCE_KEY}'"
                )
            self.reference_config = ScreenConfig(
                width=reference_data[JSON_RESOLUTION_KEY][0],
                height=reference_data[JSON_RESOLUTION_KEY][1],
                shape=reference_data[JSON_SHAPE_KEY],
            )

            # Parse Targets
            targets_data = resolution_config.get(JSON_TARGETS_KEY, [])
            self.target_configs = []
            for target in targets_data:
                self.target_configs.append(
                    ScreenConfig(
                        width=target[JSON_RESOLUTION_KEY][0],
                        height=target[JSON_RESOLUTION_KEY][1],
                        shape=target[JSON_SHAPE_KEY],
                    )
                )

            if not self.target_configs:
                raise FontScalerError(
                    f"Invalid {XML_SCREEN_RESOLUTIONS_NODE}: No targets specified."
                )

            # 2. Determine Active Default Charset
            active_default_charset = DEFAULT_CHARSET
            default_charset_node = self._find_json_node(root, XML_DEFAULT_CHARSET_NODE)
            if default_charset_node is not None:
                data = self._load_json_data(default_charset_node)
                if data is not None:
                    active_default_charset = str(data)

            # 3. Parse Specific Charset Maps
            charsets_node = self._find_json_node(root, XML_FONT_CHARSETS_NODE)
            charsets_map = {}
            if charsets_node is not None:
                charsets = self._load_json_data(charsets_node)
                if charsets:
                    charsets_map = {
                        item[JSON_FONT_ID_KEY]: item[JSON_CHARSET_KEY]
                        for item in charsets
                    }
            else:
                self._warn(f"<jsonData id='{XML_FONT_CHARSETS_NODE}'> not found.")

            # 4. Parse Font Definitions
            self.font_tasks = []
            for font_node in root.findall(XML_FONT_NODE_PATTERN):
                font_id = font_node.get(XML_FONT_NODE_ID_ATTRIBUTE)
                fnt_filename = font_node.get(XML_FONT_NODE_FILENAME_ATTRIBUTE)

                match = re.search(FNT_FILENAME_PARSE_REGEX, fnt_filename)
                if not match:
                    self._warn(
                        f"Skipping {fnt_filename} (Format '<font-name>-<fonts-size>.fnt' required)"
                    )
                    continue

                font_name = match.group(1)
                ttf_filename = f"{font_name}.ttf"
                font_size = int(match.group(2))

                charset = charsets_map.get(font_id, active_default_charset)

                task = FontTask(
                    xml_node=font_node,
                    font_id=font_id,
                    fnt_filename=fnt_filename,
                    font_name=font_name,
                    ttf_filename=ttf_filename,
                    reference_size=font_size,
                    target_size=None,
                    charset=charset,
                )
                self.font_tasks.append(task)

        except ET.ParseError as e:
            raise FontScalerError(f"Parsing XML failed with error: {e}")
        except json.JSONDecodeError as e:
            raise FontScalerError(f"Parsing JSON data in XML failed with error: {e}")

        return self

    def _find_json_node(self, root, json_id):
        for node in root.findall(XML_JSON_NODE_PATTERN):
            if node.get(XML_JSON_NODE_ID_ATTRIBUTE) == json_id:
                return node
        return None

    def execute(self):
        self._info("Font processing pipeline")
        self._info(f"* Project directory: {os.path.abspath(self.project_dir)}")
        self._info(f"* Reference: {self.reference_config}")
        self._info(f"* Targets: {len(self.target_configs)} configurations")
        self._info("Starting batch processing...")
        self._validate_sources()

        for config in self.target_configs:
            self._process_resolution(config)

        if self.table_filename:
            self._generate_markdown_report()

        self._info("Batch processing complete.")

    def _validate_sources(self):
        missing = []
        required_ttf_filenames = set(task.ttf_filename for task in self.font_tasks)
        for ttf_filename in required_ttf_filenames:
            path = os.path.join(self.resources_fonts_path, ttf_filename)
            if not os.path.exists(path):
                missing.append(ttf_filename)

        if missing:
            file_list = ", ".join(missing)
            message = f"Missing {len(missing)} Source TTF File(s): {file_list}"
            raise FontScalerError(message)

    def _process_resolution(self, target_config: ScreenConfig):
        self._info(f"Processing target: {target_config.key}")
        target_dir, target_xml = self._prepare_target(target_config)

        target_tree = ET.parse(target_xml)
        target_root = target_tree.getroot()
        target_node_map = {
            node.get(XML_FONT_NODE_ID_ATTRIBUTE): node
            for node in target_root.findall(XML_FONT_NODE_PATTERN)
        }

        work_batches = defaultdict(list)
        for task in self.font_tasks:
            target_size = self._calculate_size(task.reference_size, target_config)
            task = dataclasses.replace(task, target_size=target_size)
            work_batches[(task.ttf_filename, task.charset)].append(task)

        for (ttf_filename, charset), tasks in work_batches.items():
            source_ttf_path = os.path.join(self.resources_fonts_path, ttf_filename)
            unique_sizes = sorted(list(set(task.target_size for task in tasks)))
            size_argument = ",".join(map(str, unique_sizes))

            font_tool_command = [
                self.font_tool_path,
                FONT_TOOL_SOURCE_TTF_OPTION,
                source_ttf_path,
                FONT_TOOL_CHARSET_OPTION,
                charset,
                FONT_TOOL_HINTING_OPTION,
                DEFAULT_HINTING,
                FONT_TOOL_SIZE_OPTION,
                size_argument,
                FONT_TOOL_OUTPUT_OPTION,
                target_dir,
            ]

            if self.font_tool_padding is not None:
                font_tool_command.extend(
                    [FONT_TOOL_PADDING_OPTION, str(self.font_tool_padding)]
                )

            try:
                subprocess.run(
                    font_tool_command,
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                for task in tasks:
                    new_filename = f"{task.font_name}-{task.target_size}.fnt"
                    if task.font_id in target_node_map:
                        node = target_node_map[task.font_id]
                        node.set(XML_FONT_NODE_FILENAME_ATTRIBUTE, new_filename)

            except subprocess.CalledProcessError as e:
                raise FontScalerError(
                    f"Failed processing TTF file '{ttf_filename}': {e}"
                )
            except FileNotFoundError:
                raise FontScalerError(
                    f"font processing tool '{self.font_tool_path}' not found."
                )

        self._pretty_print_xml(target_tree)
        target_tree.write(target_xml, encoding=XML_ENCODING, xml_declaration=True)

    def _generate_markdown_report(self):
        seen_keys = {self.reference_config.key}
        all_configs = [self.reference_config]

        for config in self.target_configs:
            if config.key not in seen_keys:
                all_configs.append(config)
                seen_keys.add(config.key)

        if self.table_filename == "-":
            self._write_report_content(sys.stdout, all_configs)
        else:
            full_table_path = os.path.join(self.project_dir, self.table_filename)
            self._info(f"Generating markdown report: {full_table_path}")
            try:
                with open(full_table_path, "w", encoding="utf-8") as f:
                    self._write_report_content(f, all_configs)
            except IOError as e:
                raise FontScalerError(
                    f"Failed to write table to {full_table_path}: {e}"
                )

    def _write_report_content(self, file, configs):
        file.write("# Font sizes by element\n\n")
        self._write_matrix_table(file, configs)
        file.write("\n")
        file.write("# Font sizes by resolution\n\n")
        self._write_resolution_list_table(file, configs)

    def _write_matrix_table(self, file, configs):
        headers = ["Element", "Font"] + [
            f"{config.shape}<br/>{config.width}x{config.height}" for config in configs
        ]
        rows = []
        for task in self.font_tasks:
            element_text, font_text = self._humanize_names(task)
            row_data = [element_text, font_text]
            for config in configs:
                if config.key == self.reference_config.key:
                    row_data.append(str(task.reference_size))
                else:
                    size = self._calculate_size(task.reference_size, config)
                    row_data.append(str(size))
            rows.append(row_data)
        alignments = [True, True] + [False] * len(configs)
        self._write_formatted_table(file, headers, rows, alignments)

    def _write_resolution_list_table(self, file, configs):
        headers = ["Resolution", "Shape", "Element", "Font", "Size"]
        rows = []
        for config in configs:
            for task in self.font_tasks:
                element_text, font_text = self._humanize_names(task)
                if config.key == self.reference_config.key:
                    size = task.reference_size
                else:
                    size = self._calculate_size(task.reference_size, config)
                rows.append(
                    {
                        "sort_res": config.width * config.height,
                        "sort_elem": element_text,
                        "data": [
                            f"{config.width} x {config.height}",
                            config.shape,
                            element_text,
                            font_text,
                            str(size),
                        ],
                    }
                )
        rows.sort(key=lambda x: (x["sort_res"], x["sort_elem"]))
        clean_rows = [r["data"] for r in rows]
        alignments = [False, True, True, True, False]
        self._write_formatted_table(file, headers, clean_rows, alignments)

    def _humanize_names(self, task) -> Tuple[str, str]:
        element_text = re.sub(r"font$", "", task.font_id, flags=re.IGNORECASE)
        element_text = re.sub(r"([a-z])([A-Z])", r"\1 \2", element_text)
        element_text = element_text.strip().capitalize()

        parts = task.font_name.split("-")
        if parts:
            base = parts[0]
            suffixes = [p.lower() for p in parts[1:]]
            font_text = " ".join([base] + suffixes)
        else:
            font_text = task.font_name
        return element_text, font_text

    def _write_formatted_table(self, file, headers, rows, is_left_align):
        header_lines = [header.split("\n") for header in headers]
        max_header_lines = max(len(header) for header in header_lines)
        for header in header_lines:
            while len(header) < max_header_lines:
                header.insert(0, "")

        column_widths = [0] * len(headers)
        for i, header in enumerate(header_lines):
            width = max(len(line) for line in header)
            column_widths[i] = width

        for row in rows:
            for i, cell in enumerate(row):
                column_widths[i] = max(column_widths[i], len(cell), 3)

        for line_idx in range(max_header_lines):
            parts = []
            for column_index in range(len(headers)):
                text = header_lines[column_index][line_idx]
                width = column_widths[column_index]
                parts.append(f"{text:^{width}}")
            file.write("| " + " | ".join(parts) + " |\n")

        separator_parts = []
        for i in range(len(headers)):
            width = column_widths[i]
            separator_parts.append(
                (":" + "-" * (width - 1))
                if is_left_align[i]
                else ("-" * (width - 1) + ":")
            )
        file.write("| " + " | ".join(separator_parts) + " |\n")

        for row in rows:
            formatted_parts = []
            for i, part in enumerate(row):
                width = column_widths[i]
                if is_left_align[i]:
                    formatted_parts.append(f"{part:<{width}}")
                else:
                    formatted_parts.append(f"{part:>{width}}")
            file.write("| " + " | ".join(formatted_parts) + " |\n")

    def _prepare_target(self, target_config: ScreenConfig):
        dir_name = TARGET_RESOURCES_DIR_TEMPLATE.format(
            shape=target_config.shape,
            width=target_config.width,
            height=target_config.height,
        )
        target_resources_dir = os.path.join(self.project_dir, dir_name)
        target_fonts_dir = os.path.join(target_resources_dir, self.fonts_subdir)
        if not os.path.exists(target_fonts_dir):
            os.makedirs(target_fonts_dir)

        target_xml_path = os.path.join(target_fonts_dir, DEFAULT_XML_FILENAME)
        try:
            tree = ET.parse(self.xml_file_path)
            root = tree.getroot()
            for json_node in root.findall(XML_JSON_NODE_PATTERN):
                root.remove(json_node)
            self._pretty_print_xml(tree)
            tree.write(target_xml_path, encoding=XML_ENCODING, xml_declaration=True)
        except ET.ParseError:
            raise FontScalerError("Error preparing target XML.")
        return target_fonts_dir, target_xml_path

    def _pretty_print_xml(self, tree):
        if hasattr(ET, "indent"):
            ET.indent(tree, space="    ", level=0)

    def _calculate_size(self, original_size, target_config: ScreenConfig):
        # Improved Heuristic:
        # Calculate scaling factors for both dimensions and pick the minimum.
        # This ensures the font fits within the constraints of BOTH width and height,
        # preserving identity when the screen sizes match, even if they aren't square.

        width_ratio = target_config.width / self.reference_config.width
        height_ratio = target_config.height / self.reference_config.height

        scale_factor = min(width_ratio, height_ratio)

        return int(round(original_size * scale_factor))

    def _info(self, message):
        print(message, file=sys.stderr)

    def _warn(self, message):
        print(f"Warning: {message}", file=sys.stderr)
