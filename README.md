The codes, finite element meshes, and data for the paper "A comparison of phase field models of brittle fracture incorporating strength, I: Mixed-mode loading" published in Engineering Fracture Mechanics, 330, 111679 (2025), are available in this repository.


1. Input Parameters ( sys.argv[] ):
All command-line arguments can be supplied in either of two ways :

a. SBATCH script (recommended): Develop a [Filename].sbatch as your own job script

b. Directly in UnifiedCode.py : Default values near the top

2. Mesh Requirements: (For reference use the available example files in the folder)
   
For problems 1, 3, 6 (Surfing, Mode II, Pure Shear), Mesh types needed are mesh.xdmf & facet.xdmf : Use the Jupyter notebook mesh_convert.ipynb to convert your Gmsh.msh into XDMF (via meshio)

For all other problem examples, the code requires .xml file: Generate .xml using dolfin convert or meshio convert .msh

3. Benchmark Problems : This driver reproduces eight mixed-mode specimens:

| ID | Test                                       |
| -- | ------------------------------------------ | 
| 1  | Mode I surfing                             |      
| 2  | SENT (single-edge notch uniaxial tension)  |
| 3  | In-plane shear (Mode II)                   |
| 4  | Anti-plane shear (Mode III)                |                    
| 5  | Biaxial tension                            |                     
| 6  | Pure shear                                 |                     
| 7  | 4-point bending beam  (30° / 45° notch)    |                     
| 8  | Axisymmetric indentation                   |
| 9  | Wing crack nucleation                      |

4. Stress-State Options
Choose any constitutive kinematics:

a. Plane stress

b. Plane strain

c. Full 3-D

All three paths are implemented consistently in both elasticity and fracture driving terms.

5. Phase-Field Formulations:

a. Complete Nucleation model with Drucker–Prager (DP) and Mohr–Coulomb (MC) strength surfaces. Each with three independent calibration tracks.

b. PF-CZM (phase-field cohesive zone model)

c. Classic variational models with volumetric–deviatoric split, star-convex, and spectral split

d. Miehe et al. (2015) – stress-driven phase field model

6. Solvers: 
Native MPI + PETSc (linear solvers and different types of non-linear solvers are incorporated in the code).

7. Post-Processing
Automatic J-integral, reaction forces, critical stress.
Ready-to-plot XDMF for ParaView.

8. Citing This Work:
@article{Khayaz et al. 2025,   title={A comparison of phase field models of brittle fracture incorporating strength: I—Mixed-mode loading}}

















