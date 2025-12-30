# Garmin Font Scaler

**Garmin Font Scaler** is a robust Python utility designed to automate the generation and scaling of bitmap fonts for Garmin Connect IQ watch faces. 
It streamlines the process of adapting a watch face design to the wide variety of screen sizes in the Garmin ecosystem (e.g., 218px, 260px, 280px, 454px).

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

## Key Features

* **Zero-Config scaling**  
The `garmin-font-scaler` reads all information needed to perform the scaling (reference font size, target diameters, charsets) directly from JSON blocks embedded in the original `fonts.xml` file.
No additional configuration files or command line options are required.  
The tool does enable the user to _override_ the `fonts.xml` settings with command line options. 
* **Mathematical Precision**  
The `garmin-font-scaler` scales font pixel sizes proportionally based on screen diameter ratios.  
* **Batch Optimization**  
The `garmin-font-scaler` groups font generation tasks by source TTF file to minimize calls to the underlying conversion tool, speeding up the build process.
* **Documentation**  
The `garmin-font-scaler` generates a `fonts.md` report showing exact font sizes per resolution and a sorted list of all generated assets.
The output is provided as a neatly formatted Markdown table, suitable for inclusion in a documentation file for your watch face.  
* **Clean Artifacts**  
The `garmin-font-scaler` automatically generates the correct directory structure (e.g., `resources-round-454x454/fonts`) and creates compliant `fonts.xml` files (stripped of the non-standard JSON configuration included in the original `fonts.xml` file).

## Prerequisites

* Python 3.7+
* The [`ttf2bmp` open-source command-line tool](https://github.com/wkusnierczyk/ttf2bmp)  
You may be able to use another command line conversion tool, but you'll need to dive into the source code of `garmin-font-scaler` to adapt all the invocation details.  
Why would you ;)

## Installation

You can `garmin-font-scaler` the package directly from source:

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

## Configuration

The tool relies on a standard Garmin `fonts.xml` file augmented with custom JSON data blocks. 
This allows your source file to remain the single source of truth while still complying with the format constraints of Garmin Connect IQ SDK project files.

### Development process

1. **Design** and implement your watch face (or another application) with custom bitmap fonts appropriate for a specific device.
2. **Augment** the `fonts.xml` file with custom JSON data blocks specifying the charsets for each bitmap font and the target screen resolutions.
3. **Execute** the `garmin-scaler-tool`.
4. **Explore** the results by building your project for various devices and testing it visually in the simulator or on actual devices.

#### Design

Generate bitmap fonts for a specific screen resoltion. 
This may be an intuitive, manual, trial and error process, possibly automated with some heuristic (e.g., estimating the longest string and calculating the font size to match 90% of the screen width).

By default, `garmin-scaler-tool` assumes your _reference_ device has a screen resolution of 280x280 pixels.

> The 280x280 screen resolution is the default simply because `garmin-font-scaler` was conceived while porting to other devices watch faces developed specifically for Garmin fenix 7X Solar, which has a screen of that resolution.
> If you happen to have a different device, you can specify the default (reference) screen resolution through a command line option.
> 
> See further below for the details.

The bitmap fonts files and the font map `fonts.xml` file will by default reside in the `resources/fonts/` directory under your Garmin watch project root.
(If you prefer a different layout, you will be able to override it with command line options of `garmin-scaler-tool`. Note that the Garmin Connect IQ SDK assumes all resource files are under `resources` and per-resolution files are under `resources-*`, so you will not want to depart from that part of the layout.)

For example, if you use the fonts SUSEMono bold at 25 and 30 pixels, and Ubuntu at 30 pixels, your directory would look like:

```bash
Project root
├── resources
│   ├── fonts
│   │   ├── OFL.txt                  # Open font licence file (for SUSEMono)
│   │   ├── SUSEMono-Bold-25.fnt     # FNT file for SUSEMono bold at 25 pixels
│   │   ├── SUSEMono-Bold-25.png     # PNG file for SUSEMono bold at 25 pixels
│   │   ├── SUSEMono-Bold-30.fnt     # ...
│   │   ├── SUSEMono-Bold-30.png
│   │   ├── SUSEMono-Bold.ttf        # Original TTF file for SUSEMono bold
│   │   ├── Ubuntu-Regular-30.fnt    # ...
│   │   ├── Ubuntu-Regular-30.png
│   │   ├── Ubuntu-Regular.ttf
│   │   ├── UFL.txt                  # Ubuntu font licence (for Ubuntu)
│   │   └── fonts.xml                # Font map (font id used in source code => font file)
```

#### Augment

Your `fonts.xml` file will provide a mapping from font ids, used in the source code, to font file names, used to load the font definitions.
Following the example above, your `font.xml` might look like:

```xml
<resources>

    <fonts>
        <font id="HourFont" filename="SUSEMono-Bold-30.fnt" antialias="true" />
        <font id="MinutesFont" filename="SUSEMono-Regular-25.fnt" antialias="true" />
        ...
    </fonts>
    
</resource>
```

This maps `HourFont` to `SUSEMono-Bold-30.fnt`, etc.
In addition to that, you need to specify:
* the charset for each of the fonts usd in the source code;
* the target screen resolutions for which you want to scale the watch face to.

Augment your `fonts.xml` file with the following stanzas:

```xml
<resources>

    <fonts>
       ...
    </fonts>
    
    <!-- Specify charsets for each font id -->
    <jsonData id="FontCharsets">[
        {
            "fontId": "HourFont",
            "fontCharset": "0123456789"
        },
        {
            "fontId": "MinutesFont",
            "fontCharset": "0123456789"
        },
        ...
    ]</jsonData>
    
    <!-- Specify the target screen resolutions (diameters) -->
    <jsonData id="ScreenDiameters">{
        "referenceDiameter": 280,
        "targetDiameters": [
            218, 
            240, 
            260, 
            280, 
            360, 
            390, 
            416, 
            454
        ]
    }</jsonData>

</resources>    

```

If you have several fonts that use the same charset, you do not need to repeat the charset specification for each font separately.
You can provide the _default_ charset for all fonts, and only override it explicitly for those that use a different charset.

For example,

```xml
    <!-- Specify the default charset for all fonts (e.g., hour, minutes, seconds) -->
    <jsonData id="DefaultCharset">"0123456789"</jsonData>

    <!-- Override for fonts needing a different charset -->
    <jsonData id="FontCharsets">[
        {
            "fontId": "AMPMFont",
            "fontCharset": "AMP "
        },
    ]</jsonData>

```

**Note**  
The `garmin-font-scaler` tool will automatically remove all the `<jsonData>` blocks in `fonts.xml` files in the generated target directories.
Only the original `fonts.xml` file needs to provide them.


> Why **diameter**, not resolution? Historical reasons; `garmin-font-scaler` was developed for round watches, where a single parameter---the diameter---is enough to specify the resolution ( it always is diameter x diameter).
>
> Also, upgrading the functionality to work for devices with dmensions where width differs from hight would require some code modifications, [left for the willing contributor as an exercise](https://github.com/wkusnierczyk/garmin-font-scaler/issues/1) ;)  

#### Execute


In the simplest case, you just run `garmin-font-scaler` from your project root.

```bash
cd <your garmin watch project>

# assuming garmin-font-scaler is installed and on PATH
garmin-font-scaler
```

You can also invoke `garmin-font-scaler` from within an arbitrary directory, and provide the root directory of your project as an option:

```bash
garmin-font-scaler --project-dir <path to your garmin project root>
```

To see a table of all the generated scaled fonts, run:

```bash
# write table to fonts.md
garmin-font-scaler --table

# write table to a specified file
garmin-font-scaler --table table.md
```

There are several options available to override the defaults; see:

```bash
garmin-font-scaler --help

# output
usage: garmin-font-scaler [options]

Garmin Font Scaler

options:
  -h, --help            show this help message and exit
  --project-dir PROJECT_DIR
                        Base directory of the Garmin project containing the 'resources' directory (default: .)
  --resources-dir RESOURCES_DIR
                        Relative path to resources directory (default: resources)
  --fonts-subdir FONTS_SUBDIR
                        Relative path to fonts subdirectory (default: fonts)
  --xml-file XML_FILE   Filename of the fonts XML (default: fonts.xml)
  --reference-diameter REFERENCE_DIAMETER
                        Reference screen diameter (default: 280)
  --target-diameters TARGET_DIAMETERS
                        Comma-separated list of target diameters (default: None)
  --tool-path TOOL_PATH
                        Path to ttf2bmp executable (default: ttf2bmp)
  --table [TABLE]       Generate markdown table of sizes (default: fonts.md)
```

#### Explore

Follow the standard process of building a Monkey C project and running the simulator or sideloading the `.prg` file to your device.

See [developer.garmin.com/connect-iq/connect-iq-basics/your-first-app](https://developer.garmin.com/connect-iq/connect-iq-basics/your-first-app/) for the details.

---

## Build, test, install

This project uses `make` for common development tasks.

```bash
# Install dependencies
make install

# Run unit and integration tests
make test

# Run performance benchmarks
# Note: these do not include actual font conversion
make perf

# Clean up generated artifacts
make clean
```

Consult the included [`Makefile`](Makefile) for further details.

## License

[MIT License](LICENSE)