import dataclasses
import json
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

from collections import defaultdict
from typing import Optional, Tuple

# --- Configuration Constants ---
DEFAULT_PROJECT_DIR = "."
DEFAULT_RESOURCES_DIR = "resources"
DEFAULT_FONTS_SUBDIR = "fonts"
DEFAULT_XML_FILENAME = "fonts.xml"
DEFAULT_TOOL_PATH = "ttf2bmp"

DEFAULT_REFERENCE_DIAMETER = 280
DEFAULT_CHARSET = "0123456789:"
DEFAULT_HINTING = "none"

TARGET_RESOURCES_DIR_PREFIX = "resources-round-"
TARGET_RESOURCES_DIR_INFIX = "x"
TARGET_RESOURCES_DIR_TEMPLATE = f"{TARGET_RESOURCES_DIR_PREFIX}{{diameter}}{TARGET_RESOURCES_DIR_INFIX}{{diameter}}"

XML_DEFAULT_CHARSET_NODE = "DefaultCharset"
XML_FONT_CHARSETS_NODE = "FontCharsets"
XML_SCREEN_DIAMETERS_NODE = "ScreenDiameters"
JSON_REFERENCE_DIAMETER_KEY = "referenceDiameter"
JSON_TARGET_DIAMETERS_KEY = "targetDiameters"
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


# --- Core Logic ---

class FontProcessor:
    def __init__(self):
        self.project_dir = DEFAULT_PROJECT_DIR
        self.resources_dir = DEFAULT_RESOURCES_DIR
        self.fonts_subdir = DEFAULT_FONTS_SUBDIR
        self.xml_file_name = DEFAULT_XML_FILENAME
        self.font_tool_path = DEFAULT_TOOL_PATH

        self.resources_fonts_path = ""
        self.xml_file_path = ""
        self._set_resources_paths()

        self.reference_diameter = DEFAULT_REFERENCE_DIAMETER
        self.target_diameters = []
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
        self.resources_fonts_path = os.path.join(self.project_dir, self.resources_dir, self.fonts_subdir)
        self.xml_file_path = os.path.join(self.resources_fonts_path, self.xml_file_name)
        return self

    def with_font_tool_path(self, font_tool_path=None):
        if font_tool_path:
            self.font_tool_path = font_tool_path
        return self

    def with_reference_diameter(self, reference_diameter=None):
        if reference_diameter:
            self.reference_diameter = reference_diameter
        return self

    def with_target_diameters(self, target_diameters=None):
        if target_diameters:
            if isinstance(target_diameters, str):
                self.target_diameters = [int(x.strip()) for x in target_diameters.split(",")]
            else:
                self.target_diameters = target_diameters
        return self

    def with_table_filename(self, table_filename=None):
        self.table_filename = table_filename
        return self

    def parse_source_xml(self):
        if not os.path.exists(self.xml_file_path):
            raise FontScalerError(f"Font xml file '{self.xml_file_path}' not found.")

        try:
            tree = ET.parse(self.xml_file_path)
            root = tree.getroot()

            # 1. Parse Screen Diameters
            diameters_node = self._find_json_node(root, XML_SCREEN_DIAMETERS_NODE)
            if diameters_node is None:
                raise FontScalerError(f"<jsonData id='{XML_SCREEN_DIAMETERS_NODE}'> not found in XML.")

            diameters_config = json.loads(diameters_node.text)

            if not self.target_diameters:
                self.reference_diameter = diameters_config.get(JSON_REFERENCE_DIAMETER_KEY, self.reference_diameter)
                self.target_diameters = diameters_config.get(JSON_TARGET_DIAMETERS_KEY, [])

            if not self.reference_diameter or not self.target_diameters:
                raise FontScalerError(f"Invalid {XML_SCREEN_DIAMETERS_NODE} JSON configuration.")

            # 2. Determine Active Default Charset
            active_default_charset = DEFAULT_CHARSET
            def_charset_node = self._find_json_node(root, XML_DEFAULT_CHARSET_NODE)
            if def_charset_node is not None:
                active_default_charset = str(json.loads(def_charset_node.text))

            # 3. Parse Specific Charset Maps
            charsets_node = self._find_json_node(root, XML_FONT_CHARSETS_NODE)
            charsets_map = {}
            if charsets_node is not None:
                charsets = json.loads(charsets_node.text)
                charsets_map = {item[JSON_FONT_ID_KEY]: item[JSON_CHARSET_KEY] for item in charsets}
            else:
                self._warn(f"<jsonData id='{XML_FONT_CHARSETS_NODE}'> not found.")

            # 4. Parse Font Definitions
            self.font_tasks = []
            for font_node in root.findall(XML_FONT_NODE_PATTERN):
                font_id = font_node.get(XML_FONT_NODE_ID_ATTRIBUTE)
                fnt_filename = font_node.get(XML_FONT_NODE_FILENAME_ATTRIBUTE)

                match = re.search(FNT_FILENAME_PARSE_REGEX, fnt_filename)
                if not match:
                    self._warn(f"Skipping {fnt_filename} (Format '<font-name>-<fonts-size>.fnt' required)")
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
                    charset=charset
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
        self._info(f"* Reference diameter: {self.reference_diameter}")
        self._info(f"* Target diameters: {self.target_diameters}")
        self._info("Starting batch processing...")
        self._validate_sources()

        for diameter in self.target_diameters:
            self._process_diameter(diameter)

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
            missing_ttfs = ", ".join(missing)
            msg = f"Missing {len(missing)} source TTF files: {missing_ttfs}"
            raise FontScalerError(msg)

    def _process_diameter(self, target_diameter):
        self._info(f"Processing target diameter: {target_diameter}")
        target_dir, target_xml = self._prepare_target(target_diameter)

        target_tree = ET.parse(target_xml)
        target_root = target_tree.getroot()
        target_node_map = {node.get(XML_FONT_NODE_ID_ATTRIBUTE): node
                           for node in target_root.findall(XML_FONT_NODE_PATTERN)}

        work_batches = defaultdict(list)
        for task in self.font_tasks:
            target_size = self._calculate_size(task.reference_size, target_diameter)
            task = dataclasses.replace(task, target_size=target_size)
            work_batches[(task.ttf_filename, task.charset)].append(task)

        for (ttf_filename, charset), tasks in work_batches.items():
            source_ttf_path = os.path.join(self.resources_fonts_path, ttf_filename)
            unique_sizes = sorted(list(set(task.target_size for task in tasks)))
            size_arg = ",".join(map(str, unique_sizes))

            font_tool_cmd = [
                self.font_tool_path,
                FONT_TOOL_SOURCE_TTF_OPTION, source_ttf_path,
                FONT_TOOL_CHARSET_OPTION, charset,
                FONT_TOOL_HINTING_OPTION, DEFAULT_HINTING,
                FONT_TOOL_SIZE_OPTION, size_arg,
                FONT_TOOL_OUTPUT_OPTION, target_dir
            ]

            try:
                subprocess.run(font_tool_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                for task in tasks:
                    new_filename = f"{task.font_name}-{task.target_size}.fnt"
                    if task.font_id in target_node_map:
                        node = target_node_map[task.font_id]
                        node.set(XML_FONT_NODE_FILENAME_ATTRIBUTE, new_filename)

            except subprocess.CalledProcessError as e:
                # We log this but do not crash the whole batch, or we could raise.
                # Since one failure ruins the build, raising is safer.
                raise FontScalerError(f"Failed processing TTF file '{ttf_filename}': {e}")
            except FileNotFoundError:
                raise FontScalerError(f"font processing tool '{self.font_tool_path}' not found.")

        self._pretty_print_xml(target_tree)
        target_tree.write(target_xml, encoding=XML_ENCODING, xml_declaration=True)

    def _generate_markdown_report(self):
        full_table_path = os.path.join(self.project_dir, self.table_filename)
        self._info(f"Generating markdown report: {full_table_path}")

        all_diameters = sorted(list(set([self.reference_diameter] + self.target_diameters)))

        try:
            with open(full_table_path, "w", encoding="utf-8") as f:
                f.write("# Font sizes by element\n\n")
                self._write_matrix_table(f, all_diameters)
                f.write("\n")
                f.write("# Font sizes by resolution\n\n")
                self._write_resolution_list_table(f, all_diameters)

        except IOError as e:
            raise FontScalerError(f"Failed to write table to {full_table_path}: {e}")

    def _write_matrix_table(self, f, diameters):
        headers = ["Element", "Font"] + [str(d) for d in diameters]
        rows = []
        for task in self.font_tasks:
            el_text, font_text = self._humanize_names(task)
            row_data = [el_text, font_text]
            for d in diameters:
                size = self._calculate_size(task.reference_size, d)
                row_data.append(str(size))
            rows.append(row_data)
        alignments = [True, True] + [False] * len(diameters)
        self._write_formatted_table(f, headers, rows, alignments)

    def _write_resolution_list_table(self, f, diameters):
        headers = ["Resolution", "Element", "Font", "Size"]
        rows = []
        for d in diameters:
            for task in self.font_tasks:
                el_text, font_text = self._humanize_names(task)
                size = self._calculate_size(task.reference_size, d)
                rows.append({
                    "sort_dia": d,
                    "sort_elem": el_text,
                    "data": [f"{d} x {d}", el_text, font_text, str(size)]
                })
        rows.sort(key=lambda x: (x["sort_dia"], x["sort_elem"]))
        clean_rows = [r["data"] for r in rows]
        alignments = [False, True, True, False]
        self._write_formatted_table(f, headers, clean_rows, alignments)

    def _humanize_names(self, task) -> Tuple[str, str]:
        el_text = re.sub(r'font$', '', task.font_id, flags=re.IGNORECASE)
        el_text = re.sub(r'([a-z])([A-Z])', r'\1 \2', el_text)
        el_text = el_text.strip().capitalize()

        parts = task.font_name.split("-")
        if parts:
            base = parts[0]
            suffixes = [p.lower() for p in parts[1:]]
            font_text = " ".join([base] + suffixes)
        else:
            font_text = task.font_name
        return el_text, font_text

    def _write_formatted_table(self, f, headers, rows, is_left_align):
        col_widths = [len(h) for h in headers]
        for row in rows:
            for i, cell in enumerate(row):
                col_widths[i] = max(col_widths[i], len(cell), 3)

        def write_row(parts):
            formatted_parts = []
            for i, part in enumerate(parts):
                width = col_widths[i]
                if is_left_align[i]:
                    formatted_parts.append(f"{part:<{width}}")
                else:
                    formatted_parts.append(f"{part:>{width}}")
            f.write("| " + " | ".join(formatted_parts) + " |\n")

        write_row(headers)
        sep_parts = []
        for i in range(len(headers)):
            width = col_widths[i]
            sep_parts.append((":" + "-" * (width - 1)) if is_left_align[i] else ("-" * (width - 1) + ":"))
        f.write("| " + " | ".join(sep_parts) + " |\n")
        for row in rows:
            write_row(row)

    def _prepare_target(self, diameter):
        dir_name = TARGET_RESOURCES_DIR_TEMPLATE.format(diameter=diameter)
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

    def _calculate_size(self, original_size, target_diameter):
        return int(round(float(original_size) / self.reference_diameter * target_diameter))

    def _info(self, message):
        print(message, file=sys.stderr)

    def _warn(self, message):
        print(f"Warning: {message}", file=sys.stderr)