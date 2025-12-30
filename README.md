# Garmin Font Scaler

**Garmin Font Scaler** is a robust Python utility designed to automate the generation and scaling of bitmap fonts for Garmin Connect IQ watch faces. It streamlines the process of adapting a watch face design to the wide variety of screen sizes in the Garmin ecosystem (e.g., 218px, 260px, 280px, 454px).

Instead of manually calculating font sizes, running conversion tools one by one, and editing XML files for every single resolution, this tool reads your configuration directly from your source `fonts.xml` and handles the entire pipeline automatically.

## Key Features

* **Zero-Config scaling**: Reads source configuration (reference size, target diameters, charsets) directly from embedded JSON blocks in your `fonts.xml`.
* **Mathematical Precision**: Scales font pixel sizes proportionally based on screen diameter ratios (e.g., `NewSize = OldSize * (TargetDia / RefDia)`).
* **Batch Optimization**: Intelligently groups font generation tasks by source TTF file to minimize calls to the underlying conversion tool, significantly speeding up the build process.
* **Documentation**: Automatically generates a `fonts.md` report showing exact font sizes per resolution and a sorted list of all generated assets.
* **Clean Artifacts**: Automatically generates the correct directory structure (e.g., `resources-round-454x454/fonts`) and creates compliant `fonts.xml` files stripped of non-standard JSON configuration for the final build.

## Prerequisites

* Python 3.7+
* The `ttf2bmp` command-line tool (part of the Garmin Connect IQ SDK or similar font conversion utilities).

## Installation

You can install the package directly from source:

```bash
# Clone the repository
git clone [https://github.com/yourusername/garmin-font-scaler.git](https://github.com/yourusername/garmin-font-scaler.git)
cd garmin-font-scaler

# Install using pip
pip install .
```

For development (including test dependencies):

```bash
pip install -e .[dev]
```

## Configuration

The tool relies on a standard Garmin `fonts.xml` file, augmented with custom `<jsonData>` blocks. This allows your source file to remain the "single source of truth."

**File Location:** `resources/fonts/fonts.xml`

### Example `fonts.xml`

```xml
<resources>
    <fonts>
        <font id="TimeFont" filename="Ubuntu-Bold-60.fnt" antialias="true" />
        <font id="DateFont" filename="Ubuntu-Regular-20.fnt" antialias="true" />
    </fonts>

    <jsonData id="ScreenDiameters">{
        "referenceDiameter": 280,
        "targetDiameters": [218, 260, 416, 454]
    }</jsonData>

    <jsonData id="DefaultCharset">"0123456789"</jsonData>

    <jsonData id="FontCharsets">[
        {
            "fontId": "DateFont",
            "fontCharset": "0123456789: MTWTFSS"
        }
    ]</jsonData>
</resources>
```

**Note:** The build tool will automatically remove the `<jsonData>` blocks in the generated target directories, ensuring the final XML is fully compliant with the Garmin Connect IQ compiler.

## Usage

Once configured, simply run the tool from your project root.

### Basic Run
Assumes `ttf2bmp` is in your PATH or the default location.

```bash
garmin-font-scaler
```

### Generate Documentation Table
Generate a markdown table of all font sizes:

```bash
garmin-font-scaler --table
```

### Specifying the Tool Path
If `ttf2bmp` is located elsewhere (e.g., in a specific SDK folder):

```bash
garmin-font-scaler --tool-path /path/to/connectiq-sdk/bin/ttf2bmp
```

### Overriding Configuration
You can override settings from the command line for testing purposes:

```bash
# Only generate for the 454px screen
garmin-font-scaler --target-diameters 454

# Use a different source directory
garmin-font-scaler --resources-dir my_resources
```

## Build & Test (Development)

This project uses `make` for common development tasks.

```bash
# Install dependencies
make install

# Run Unit and Integration Tests
make test

# Run Performance Benchmarks
make perf

# Clean up generated artifacts
make clean
```

## License

[MIT License](LICENSE)