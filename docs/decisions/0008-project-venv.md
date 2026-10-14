0008 Use a project virtual environment; install with python -m pip

Status: accepted, 2026-10-13

Create `.venv` in the project with Python 3.14, activate it before working, and install packages with `python -m pip`. Record packages in `requirements.txt`.

The machine has two Pythons, and `pip` and `python3` pointed at different ones. `pip install beautifulsoup4` reported it already installed under `C:\Python314` and the 3.14 user site-packages. Running the script with `python3` failed with `ModuleNotFoundError: No module named 'bs4'`, and a traceback showed `python3` loading packages from `PythonSoftwareFoundation.Python.3.12...\Python312\site-packages`, the Microsoft Store install.

`python -m pip` always installs into the interpreter that `python` launches, and an activated venv makes `python` the project's interpreter regardless of what else is installed.

The import name differs from the install name: install `beautifulsoup4`, import `bs4`.

Dev NOTE: `beautifulsoup4` install and import process needs review and documentation! It may differ from what Claude believes and has listed above. -Klein