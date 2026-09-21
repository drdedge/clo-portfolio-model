# Using this repository

Download the complete reviewed package from the [v0.2.0 release](https://github.com/drdedge/clo-portfolio-model/releases/tag/v0.2.0), or clone this private repository.

Start with [README.md](README.md), then [QUICK_START.md](QUICK_START.md). The ready-to-review workbook is [examples/Example_CLO.xlsx](examples/Example_CLO.xlsx); the blank template is [templates/CLO_Template.xlsx](templates/CLO_Template.xlsx).

## Runtime requirements

The saved Excel workbooks can be opened directly. Generating a new workbook requires Python, Node.js and the separately provisioned `@oai/artifact-tool` renderer. Installing `requirements.txt` alone does not install the Excel renderer. Runtime binaries and that renderer are not redistributed in this repository. Follow the runtime section of the README and have the approved local environment provisioned before a full run. The Python engine and tests are usable separately.

## Local calibration

Keep real portfolio data and all generated results inside the approved local calibration environment. `local_data/` and root-level generated workbooks/results are ignored by Git as an extra guard, but review every proposed commit before publishing it. The committed examples are fictional.

This is a development model, not an agency rating. [Outstanding work](docs/OUTSTANDING_AND_NEXT_STEPS.md) documents missing S&P SDR and Fitch PCM functionality and the remaining validation work.

`MANIFEST.json` covers the original delivered model files. Repository-only setup files are outside that manifest. The release ZIP preserves the reviewed package exactly.
