import streamlit as st
import rdkit
from rdkit import Chem
from rdkit.Chem import Draw
from rdkit.Chem import AllChem
from rdkit.Chem import Descriptors
import py3Dmol
import requests
import json
import pandas as pd
import io
from PIL import Image

def fetch_from_pubchem(molecule_name):
    """Fetch molecule data from PubChem API"""
    try:
        # Search for the compound
        search_url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{molecule_name}/JSON"
        response = requests.get(search_url)
        if response.status_code != 200:
            return None
        
        data = response.json()
        cid = data['PC_Compounds'][0]['id']['id']['cid']
        
        # Get SMILES
        smiles_url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cid}/property/IsomericSMILES/JSON"
        smiles_response = requests.get(smiles_url)
        if smiles_response.status_code != 200:
            return None
        
        smiles_data = smiles_response.json()
        return smiles_data['PropertyTable']['Properties'][0]['IsomericSMILES']
    except Exception as e:
        st.error(f"Error fetching from PubChem: {str(e)}")
        return None

def calculate_properties(mol):
    """Calculate molecular properties"""
    if mol is None:
        return None
    
    properties = {
        'Molecular Weight': round(Descriptors.ExactMolWt(mol), 2),
        'LogP': round(Descriptors.MolLogP(mol), 2),
        'H-Bond Donors': Descriptors.NumHDonors(mol),
        'H-Bond Acceptors': Descriptors.NumHAcceptors(mol),
        'Rotatable Bonds': Descriptors.NumRotatableBonds(mol),
        'Molecular Formula': Chem.rdMolDescriptors.CalcMolFormula(mol),
        'TPSA': round(Descriptors.TPSA(mol), 2),
    }
    return properties

def generate_molecule_image(mol, size=(400, 400), style='ball'):
    """Generate 2D molecule image with options"""
    if mol is None:
        return None, "Invalid molecule"
    
    try:
        if style == 'ball':
            img = Draw.MolToImage(mol, size=size)
        else:
            drawer = Draw.rdDepictor.PrepareMolForDrawing(mol)
            img = Draw.MolToImage(mol, size=size, drawer=drawer)
        return img, None
    except Exception as e:
        return None, str(e)

# Streamlit UI
st.set_page_config(page_title="Advanced Molecule Visualizer", layout="wide")
st.title("Advanced Molecule Visualizer")

# Sidebar for options
st.sidebar.header("Visualization Options")
viz_style = st.sidebar.selectbox(
    "2D Visualization Style",
    ["ball", "stick"]
)

col1, col2 = st.columns([2, 1])

with col1:
    # Input section
    molecule_name = st.text_input("Enter molecule name:", "aspirin")
    
    # File upload
    uploaded_file = st.file_uploader("Or upload a mol/sdf file", type=['mol', 'sdf'])

# Process input
mol = None
if uploaded_file:
    try:
        mol = Chem.MolFromMolBlock(uploaded_file.getvalue().decode('utf-8'))
        if mol is None:
            st.error("Invalid molecule file")
    except Exception as e:
        st.error(f"Error reading file: {str(e)}")
elif molecule_name:
    # Try local database first
    molecule_dict = {
        "water": "O",
        "methane": "C",
        "ethanol": "CCO",
        "glucose": "C([C@@H]1[C@H]([C@@H]([C@H](C(O1)O)O)O)O)O",
        "aspirin": "CC(=O)OC1=CC=CC=C1C(=O)O",
        "caffeine": "CN1C=NC2=C1C(=O)N(C(=O)N2C)C",
    }
    
    smiles = molecule_dict.get(molecule_name.lower())
    if smiles is None:
        # Try PubChem
        smiles = fetch_from_pubchem(molecule_name)
    
    if smiles:
        mol = Chem.MolFromSmiles(smiles)
        st.write(f"SMILES: {smiles}")

if mol:
    # Calculate and display properties
    with col2:
        st.subheader("Molecular Properties")
        properties = calculate_properties(mol)
        if properties:
            for prop, value in properties.items():
                st.write(f"**{prop}:** {value}")
    
    # Generate and display 2D visualization
    img, error = generate_molecule_image(mol, style=viz_style)
    if error:
        st.error(f"Error generating visualization: {error}")
    else:
        st.image(img, caption=f"2D structure", use_column_width=True)
    
    # 3D Visualization
    st.subheader("3D Structure")
    try:
        mol = Chem.AddHs(mol)
        AllChem.EmbedMolecule(mol)
        AllChem.MMFFOptimizeMolecule(mol)
        
        viewer = py3Dmol.view(width=800, height=400)
        conf = mol.GetConformer()
        pdb = Chem.MolToPDBBlock(mol)
        viewer.addModel(pdb, "pdb")
        viewer.setStyle({'stick':{}, 'sphere':{'radius':0.5}})
        viewer.zoomTo()
        
        st.components.v1.html(viewer._repr_html_(), width=800, height=400)
    except Exception as e:
        st.error(f"Error generating 3D visualization: {str(e)}")

# Instructions
st.markdown("""
### Instructions:
1. Enter a molecule name or upload a mol/sdf file
2. View 2D and 3D visualizations
3. Explore molecular properties
4. Adjust visualization style in the sidebar

### Supported input methods:
- Common molecule names (e.g., water, methane, ethanol)
- PubChem compound names
- MOL/SDF file upload

### Available properties:
- Molecular Weight
- LogP
- H-Bond Donors/Acceptors
- Rotatable Bonds
- Molecular Formula
- TPSA (Topological Polar Surface Area)
""")