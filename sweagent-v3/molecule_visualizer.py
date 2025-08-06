import streamlit as st
import py3Dmol
from rdkit import Chem
from rdkit.Chem import AllChem
from rdkit.Chem import Draw
import requests
import io
from PIL import Image
import pandas as pd

def get_pubchem_smiles(molecule_name):
    """Fetch SMILES from PubChem API using compound name"""
    try:
        url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{molecule_name}/property/IsomericSMILES/JSON"
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()['PropertyTable']['Properties'][0]['IsomericSMILES']
        return None
    except:
        return None

def calculate_properties(mol):
    """Calculate molecular properties using RDKit"""
    if mol is None:
        return None
    
    props = {}
    props['Molecular Weight'] = round(Chem.Descriptors.ExactMolWt(mol), 2)
    props['LogP'] = round(Chem.Descriptors.MolLogP(mol), 2)
    props['H-Bond Donors'] = Chem.Descriptors.NumHDonors(mol)
    props['H-Bond Acceptors'] = Chem.Descriptors.NumHAcceptors(mol)
    props['Rotatable Bonds'] = Chem.Descriptors.NumRotatableBonds(mol)
    props['TPSA'] = round(Chem.Descriptors.TPSA(mol), 2)
    props['Molecular Formula'] = Chem.rdMolDescriptors.CalcMolFormula(mol)
    
    return props

def generate_3d_structure(mol):
    """Generate 3D coordinates for the molecule"""
    mol = Chem.AddHs(mol)
    AllChem.EmbedMolecule(mol, randomSeed=42)
    AllChem.MMFFOptimizeMolecule(mol)
    return mol

def mol_to_html(mol):
    """Convert molecule to HTML for 3D viewing"""
    return Chem.MolToMolBlock(mol)

st.set_page_config(page_title="Molecule Visualizer", layout="wide")
st.title("🧬 Molecule Visualizer")

# Sidebar
st.sidebar.header("Input Options")
input_method = st.sidebar.radio("Choose input method:", 
                              ["Molecule Name", "SMILES String"])

# Main input
if input_method == "Molecule Name":
    molecule_input = st.text_input("Enter molecule name (e.g., aspirin, caffeine):")
    if molecule_input:
        smiles = get_pubchem_smiles(molecule_input)
        if smiles is None:
            st.error("Molecule not found in PubChem database!")
        else:
            st.success(f"SMILES: {smiles}")
else:
    smiles = st.text_input("Enter SMILES string:")

# Process molecule if input is provided
if 'smiles' in locals() and smiles:
    try:
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            st.error("Invalid SMILES string!")
        else:
            # Create two columns for visualization
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("2D Structure")
                img = Draw.MolToImage(mol)
                st.image(img)
            
            with col2:
                st.subheader("3D Structure")
                mol_3d = generate_3d_structure(mol)
                viewer = py3Dmol.view(width=400, height=400)
                viewer.addModel(mol_to_html(mol_3d), "mol")
                viewer.setStyle({'stick':{}})
                viewer.zoomTo()
                viewer.show()
                st.components.v1.html(viewer._repr_html_(), height=400)
            
            # Display molecular properties
            st.subheader("Molecular Properties")
            props = calculate_properties(mol)
            if props:
                df = pd.DataFrame(list(props.items()), 
                                columns=['Property', 'Value'])
                st.table(df)

    except Exception as e:
        st.error(f"Error processing molecule: {str(e)}")

# Add instructions
with st.sidebar.expander("Instructions"):
    st.write("""
    1. Choose input method (Molecule Name or SMILES)
    2. Enter molecule name or SMILES string
    3. View 2D and 3D structures
    4. Explore molecular properties
    """)