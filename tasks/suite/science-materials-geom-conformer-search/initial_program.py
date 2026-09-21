"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
from rdkit import Chem
from rdkit.Chem import AllChem
import numpy as np

def conformers(molecular_graph_smiles, stereochemistry, budget):
    mol = Chem.AddHs(Chem.MolFromSmiles(molecular_graph_smiles))
    settings = AllChem.ETKDGv3()
    settings.randomSeed = 271
    expected = {atom.GetIdx(): atom.GetProp("_CIPCode") for atom in mol.GetAtoms() if atom.HasProp("_CIPCode")}
    def preserves_stereo(coordinates):
        trial = Chem.Mol(mol)
        trial.RemoveAllConformers()
        conformer = Chem.Conformer(mol.GetNumAtoms())
        for index, xyz in enumerate(coordinates):
            conformer.SetAtomPosition(index, xyz)
        trial.AddConformer(conformer)
        Chem.AssignStereochemistryFrom3D(trial)
        Chem.AssignStereochemistry(trial, cleanIt=True, force=True)
        return all(trial.GetAtomWithIdx(index).HasProp("_CIPCode") and trial.GetAtomWithIdx(index).GetProp("_CIPCode") == code for index, code in expected.items())
    ids = AllChem.EmbedMultipleConfs(mol, numConfs=budget, params=settings)
    output = []
    for i in ids:
        embedded = mol.GetConformer(i).GetPositions().copy()
        AllChem.UFFOptimizeMolecule(mol, confId=i, maxIters=200)
        relaxed = mol.GetConformer(i).GetPositions()
        # Unconstrained UFF may invert a strained cage stereocenter. Preserve
        # the valid embedded geometry when relaxation changes molecular identity.
        coordinates = relaxed if preserves_stereo(relaxed) else embedded
        if preserves_stereo(coordinates):
            output.append(coordinates)
    return np.array(output)
# EVOLVE-BLOCK-END
