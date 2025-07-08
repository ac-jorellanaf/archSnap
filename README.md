# archSnap

A Blender-based tool for the standardised visualisation of archaeological artefacts. 📷🏺

This tool creates renders of 3D objects (meshes) from all 6 orthogonal directions

## Requirements

Important! Before running this tool, you need to manually install the following:
- Blender 4.4.x from the [Blender website](https://www.blender.org/download/) ([alternative link](https://download.blender.org/release/Blender4.4/))
- In order to run the Blender Python module (`bpy==4.4.\*`), you need to install and use [`Python==3.11.\*`](https://www.python.org/downloads/).

## Installation and usage

### From [PyPI package page]()

- Installation from PyPI: In a console, run `pip install archsnap` to install the package, and `python -m archsnap` to run the tool.

### Direct download

- To run the tool without installing from PyPi, download the contents of the repository to your computer (be it a release or with `git clone {URL}`). Open a console and navigate it to the downloaded repository's base folder (i.e. the one containing the `README.md` file), then the `src/` directory, and from there run `python -m archSnap`. The GUI should launch from there.

## License

This work is an open source work licensed according to the terms of the GNU General Public License version 3 (GPL3; see [license file](LICENSE))
