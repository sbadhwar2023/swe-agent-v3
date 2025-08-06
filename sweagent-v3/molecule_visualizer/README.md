# Molecule Visualizer

A simple web application that visualizes molecules based on their names or SMILES strings using Streamlit and RDKit.

## Features

- Visualize molecules using either their common names or SMILES notation
- Interactive web interface
- 2D molecular structure visualization

## Installation

1. Create a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
```

2. Install the required dependencies:
```bash
pip install -r requirements.txt
```

## Usage

1. Run the Streamlit app:
```bash
streamlit run app.py
```

2. Open your web browser and navigate to the URL shown in the terminal (typically http://localhost:8501)

3. Enter either a molecule name (e.g., "aspirin") or a SMILES string in the input field

## Notes

- For best results with molecule names, use IUPAC nomenclature
- The app also accepts SMILES strings for more precise molecular structure input
- Internet connection may be required for name-to-structure conversion

## Requirements

- Python 3.7+
- Streamlit
- RDKit
- Pillow