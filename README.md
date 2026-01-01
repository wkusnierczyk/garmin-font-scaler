# Garmin Font Scaler

[![CI](https://github.com/wkusnierczyk/garmin-font-scaler/actions/workflows/tests.yml/badge.svg)](https://github.com/wkusnierczyk/garmin-font-scaler/actions/workflows/tests.yml)

**Garmin Font Scaler** is a robust Python utility designed to automate the generation and scaling of bitmap fonts for Garmin Connect IQ watch faces. 
It adapts a watch face design to the wide variety of screen sizes and shapes in the Garmin ecosystem (round, semi-round, rectangle, etc.).

The project provides a command line tool, `garmin-font-scaler`.
Instead of manually calculating font sizes, running conversion tools one by one, and editing XML files for every single resolution, this tool reads your configuration directly from the source `fonts.xml` file and handles the entire pipeline automatically.

> Garmin Font Scaler is a **Build What You Need** (BWYN) project.
> 
> It came into existence as a hacky script to automate the process of adapting a watch face developed for Garmin Fenix 7X (280x280 pixel screen resolution) to a wide variety of devices with other screen resolutions.
> The watch face used several custom bitmap fonts, which do not automatically scale to different screen resolutions. 
> 
> Appropriate font sizes need to be calculated anew for each screen resolution, and new bitmap (`fnt` and `png`) font files need to be generated from the source True Type (`ttf`) font files.
> Maually, this process was very tedious.
> The script provided an immense help, and is therefore shared as a contribution to the Garmin Developer community. 
> 
> See the [`garmin-watch-faces`](https://github.com/wkusnierczyk/garmin-watch-faces) project for more information.

## Contents

* [Features](#features)
* [Scaling Logic](#scaling-logic)
* [Prerequisites](#prerequisites)
* [Installation](#installation)
* [Usage](#usage)
* [Build, Test, and Release](#build-test-and-release)
* [About](#about)
* [License](#license)

## Features

* **Zero-Config scaling** The `garmin-font-scaler` reads all information needed to perform the scaling (reference resolution, target resolutions, charsets) directly from JSON data files linked in the original `fonts.xml`.
* **Shape Aware** Supports round, semi-round, and rectangular screens.
* **Smart Scaling Heuristic** Uses a robust heuristic for scaling fonts between different aspect ratios (scaling based on the constraining dimension), ensuring text remains readable on 148x205 rectangles just as well as 454x454 round screens.
* **Batch Optimization** The `garmin-font-scaler` groups font generation tasks by source TTF file to minimize calls to the underlying conversion tool, speeding up the build process.
* **Documentation** The `garmin-font-scaler` generates a `fonts.md` report showing exact font sizes per resolution and a sorted list of all generated assets.
The output is provided as a neatly formatted Markdown table, suitable for inclusion in a documentation file for your watch face.  
* **Clean Artifacts** The `garmin-font-scaler` automatically generates the correct directory structure (e.g., `resources-rectangle-148x205/fonts`) and creates compliant `fonts.xml` files (stripped of the non-standard JSON configuration included in the original `fonts.xml` file).

## Scaling Logic

The scaler determines the new font size by calculating a scaling factor ($k$) that respects the constraints of the target screen shape relative to the reference screen.

### The Calculation

To ensure text content fits safely on the target device without clipping, the tool calculates the scaling ratio for both dimensions and applies the **constraining (smaller) dimension**:

$$
k = \min \left( \frac{W_{target}}{W_{ref}}, \frac{H_{target}}{H_{ref}} \right)
$$

Where:
* $W_{target}, H_{target}$ are the dimensions of the device you are generating fonts for.
* $W_{ref}, H_{ref}$ are the dimensions of the device you originally designed for.

### Example Scenario

If your reference device is a **280x280 (Round)** watch, and you are scaling to a **148x205 (Rectangle)** device:

1.  **Width Ratio:** $148 / 280 \approx 0.53$
2.  **Height Ratio:** $205 / 280 \approx 0.73$
3.  **Result:** The tool selects **0.53** as the scaling factor.

This ensures that a line of text that fits perfectly across the width of the round watch will be scaled down enough to fit across the width of the narrow rectangular watch.

## Prerequisites

* Python 3.7+
* The [`ttf2bmp` open-source command-line tool](https://github.com/wkusnierczyk/ttf2bmp)  

## Installation

You can install the package directly from source:

```bash
git clone https://github.com/wkusnierczyk/garmin-font-scaler.git
cd garmin-font-scaler

pip install .
```

For development (including test dependencies):

```bash
pip install -e .[dev]
```

You can also use the included `Makefile` to install the package with `make`:

```bash
make install
```

## Usage

The tool relies on a standard Garmin `fonts.xml` file augmented with custom `jsonData` tags that point to external JSON configuration files.

#### Create `resolutions.json`

Define your reference device (the one you designed for) and the target devices you want to support.

```json
{
    "reference": { "resolution": [260, 260], "shape": "round" },
    "targets": [
        { "resolution": [218, 218], "shape": "round" },
        { "resolution": [454, 454], "shape": "round" },
        { "resolution": [148, 205], "shape": "rectangle" },
        { "resolution": [215, 180], "shape": "semi-round" }
    ]
}
```

#### Create `charsets.json`

Map your Font IDs (from `fonts.xml`) to the specific characters they need to support.

```json
[
  { "fontId": "HourFont", "fontCharset": "0123456789" },
  { "fontId": "DataFont", "fontCharset": "0123456789%°C" }
]
```

#### Update `fonts.xml`

In your `fonts.xml`, add `jsonData` tags pointing to the files you just created.

```xml
<resources>
    <fonts>
        <font id="HourFont" filename="SUSEMono-Bold-30.fnt" antialias="true" />
        <font id="DataFont" filename="Roboto-Regular-18.fnt" antialias="true" />
    </fonts>
    
    <jsonData id="ScreenResolutions" filename="resolutions.json" />
    <jsonData id="FontCharsets" filename="charsets.json" />
</resources>    
```

#### Execute

Run the tool from your project root:

```bash
garmin-font-scaler
```

This will create directories like `resources-round-454x454/fonts` and `resources-rectangle-148x205/fonts`, generating all required assets.

#### Generate Report

To see a table of all the generated scaled fonts:

```bash
garmin-font-scaler --table
```

### CLI Options

```bash
garmin-font-scaler --help

options:
  -h, --help            show this help message and exit
  --about               Show about information and exit
  --version             show program's version number and exit
  --project-dir PROJECT_DIR
                        Base directory of the Garmin project (default: .)
  --xml-file XML_FILE   Filename of the fonts XML (default: fonts.xml)
  --tool-path TOOL_PATH
                        Path to ttf2bmp executable (default: ttf2bmp)
  --table [TABLE]       Generate markdown table of sizes
```

## Build, test, install

This project uses `make` for common development tasks.

```bash
# Build package
make build

# Install dependencies
make install

# Run tests
make test

# Run benchmarks
make perf

# Clean up code
make format lint

# Clean artifacts
make clean
```

## About

```text
garmin-font-scaler --about

garmin-font-scaler: bitmap font scaling automation for Garmin screen resolutions
├─ version:    0.2.2
├─ developer:  mailto:waclaw.kusnierczyk@gmail.com
├─ source:     https://github.com/wkusnierczyk/garmin-font-scaler
└─ licence:    MIT https://opensource.org/licenses/MIT
```

## License

[MIT License](LICENSE)
