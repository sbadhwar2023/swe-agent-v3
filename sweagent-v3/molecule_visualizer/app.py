import streamlit as st
from rdkit import Chem
from rdkit.Chem import Draw
from PIL import Image
import io

def generate_molecule_image(smiles_or_name):
    try:
        # First try to convert the input as a SMILES string
        mol = Chem.MolFromSmiles(smiles_or_name)
        
        # If that doesn't work, try to convert from name using IUPAC name (requires internet)
        if mol is None:
            from rdkit.Chem import AllChem
            # Note: This is a simplified approach. For production, you might want to use a chemical name lookup service
            mol = Chem.MolFromIUPACName(smiles_or_name)
        
        if mol is None:
            return None
            
        # Generate 2D depiction
        img = Draw.MolToImage(mol)
        return img
    except Exception as e:
        st.error(f"Error generating molecule: {str(e)}")
        return None

def main():
    st.title("Molecule Visualizer")
    st.write("Enter a molecule name or SMILES string to visualize it!")
    
    # Input for molecule name or SMILES
    molecule_input = st.text_input("Enter molecule name or SMILES:", "aspirin")
    
    if molecule_input:
        # Generate and display the molecule
        molecule_image = generate_molecule_image(molecule_input)
        if molecule_image:
            st.image(molecule_image, caption=f"Visualization of {molecule_input}")
        else:
            st.error("Could not generate molecule visualization. Please check your input.")
        
        st.info("Note: This app accepts both SMILES strings and common molecule names. For best results with names, use IUPAC nomenclature.")

if __name__ == "__main__":
    main()