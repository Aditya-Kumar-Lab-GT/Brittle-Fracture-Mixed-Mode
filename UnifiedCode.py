###########################################################################################################################################################################################################################
# Unified Fenics code: 
# # Contact Umar Khayaz (ukhayaz3@gatech.edu), Aditya Kumar (akumar355@gatech.edu) for questions.
###########################################################################################################################################################################################################################

from dolfin import *
import numpy as np
import time
import sys
import csv
from datetime import datetime
from dolfin import assemble, inner, grad, Point, MPI
import numpy as np
from pathlib import Path

#  Determine the start time for the analysis
startTime = datetime.now()

# Problem description
comm = MPI.comm_world 
comm_rank = MPI.rank(comm)



I1_correction = 1
#------------------------------------------------
# Material properties 
#------------------------------------------------
E   = float(sys.argv[1])
nu  = float(sys.argv[2])
Gc  = float(sys.argv[3])
sts = float(sys.argv[4])
scs = float(sys.argv[5])

#------------------------------------------------
# Regularization length and mesh refinement parameter
#------------------------------------------------
lch = 3 * Gc * E / (8 * (sts**2))
eps = float(sys.argv[6])
h   = float(sys.argv[7])

#------------------------------------------------
# Time-stepping parameters
#------------------------------------------------
T           = float(sys.argv[8])
Totalsteps  = int(sys.argv[9])
loadfactor  = float(sys.argv[10])

#------------------------------------------------
# Phase-field parameters
#------------------------------------------------
z_crit           = float(sys.argv[11])
z_penalty_factor = float(sys.argv[12])
eta              = float(sys.argv[13])
stag_iter_max    = int(sys.argv[14])

#------------------------------------------------
# Solver choices
#------------------------------------------------
linear_solver_for_u      = int(sys.argv[15])
non_linear_solver_choice = int(sys.argv[16])
paraview_at_step         = int(sys.argv[17])
v0_imp                   = float(sys.argv[18])
problem_dim              = int(sys.argv[19])

#------------------------------------------------
# Geometry parameters (for the single edge notch problem)
#------------------------------------------------
ac     = float(sys.argv[20])
W      = float(sys.argv[21])
L      = float(sys.argv[22])
Lz     = float(sys.argv[23])
CrackZ = float(sys.argv[24])

#------------------------------------------------
# Additional problem parameters
#------------------------------------------------
markBC_choice      = int(sys.argv[25])
mesh_choice        = int(sys.argv[26])
notch_angle_choice = int(sys.argv[27])
DirichletBC_choice = int(sys.argv[28])
problem_type       = int(sys.argv[29])



#------------------------------------------------
# Strength and calibration choices 
#------------------------------------------------
strength_surface_choice = int(sys.argv[30])
if strength_surface_choice == 1:
    folder_prefix = '_DP'
elif strength_surface_choice == 2:
    folder_prefix = '_MC'
else:
    raise ValueError("Invalid strength surface choice. Choose 1 for DP or 2 for MC.")

calibrationchoice = int(sys.argv[31])
shs_delta_choice = int(sys.argv[32])

#------------------------------------------------
# Criterion for phase_model == 2
#------------------------------------------------
vonMises_or_Rankine = int(sys.argv[33])
if vonMises_or_Rankine == 1:
    folder_prefix += '_vonMises'
elif vonMises_or_Rankine == 2:
    folder_prefix += '_Rankine'
else:
    raise ValueError("Invalid criterion choice. Choose 1 for von Mises or 2 for Rankine.")

#------------------------------------------------
# Phase field model
#------------------------------------------------
phase_model = int(sys.argv[34])
if phase_model == 1:
    folder_prefix += '_Nucleation'
elif phase_model == 2:
    folder_prefix += '_PF_CZM'
elif phase_model == 3:
    folder_prefix += '_Variational'
elif phase_model == 4:
    folder_prefix += '_Miehe_2015'
else:
    raise ValueError("Invalid Phase Field Model choice.")

#------------------------------------------------
# Variational model and stress state
#------------------------------------------------
variational_model = int(sys.argv[35])
stress_state_choice = int(sys.argv[36])
if stress_state_choice == 1:
    folder_prefix += '_PlaneStress'
elif stress_state_choice == 2:
    folder_prefix += '_PlaneStrain'
elif stress_state_choice == 3:
    folder_prefix += '_3D'
elif stress_state_choice == 4:
    folder_prefix += '_axi'
else:
    raise ValueError("Invalid stress state choice. Choose 1, 2, 3, or 4.")

# ___________________________________________________________________________________________________________________________________________________________

"""
===========================================================================
Mesh Conversion Pre-Processing Instructions for 2D Problems:
===========================================================================
Before running this FEniCS simulation code, you must first convert the 
Gmsh-generated .msh file into XDMF format for use with FEniCS. This is 
done using a separate Python script (2d_gmsh_convert.py) that employs 
the meshio library to generate two XDMF files:

  1. <filename>.xdmf: Contains the 2D mesh (e.g., triangle elements) of 
     the domain.
  2. facet_<filename>.xdmf: Contains the boundary facet data (e.g., line 
     elements) with physical markers as defined in your Gmsh script.

Example usage of the conversion script:
    python 2d_gmsh_convert.py crack 

This command reads the file 'crack.msh' and produces 'crack.xdmf' and 
'facet_crack.xdmf'. These files are then used by the FEniCS code below 
to load the mesh and boundary information.

Make sure that:
  - The physical groups in your Gmsh script (e.g., "Top", "Bottom", 
    "Left", "Right", "Crack", etc.) are correctly defined.
  - The conversion script properly extracts cell data and prunes the 
    z-coordinate (if a 2D mesh is desired).
  - The output XDMF files are placed in the appropriate location so that 
    they can be read by the FEniCS code (adjust the file paths as needed).

Once the conversion is complete, run this FEniCS code to perform the 
simulation.
===========================================================================
"""
if problem_type in (1, 3, 6, 9, 10):
    # -----------------------------------------------------
    # Mesh Loading
    # -----------------------------------------------------
    mesh = Mesh()

    # File names for the mesh (domain) and the boundary facets
    meshname = "crack.xdmf"
    facet_meshname = "facet_crack.xdmf"

    # Read the mesh from the XDMF file
    with XDMFFile(meshname) as infile:
        infile.read(mesh)

    # Get spatial coordinates (if needed)
    x = SpatialCoordinate(mesh)
    xm = SpatialCoordinate(mesh)

    # -----------------------------------------------------
    # Load Domain (Cell) Markers from the XDMF File
    # -----------------------------------------------------
    # Create a MeshValueCollection for 2D cell data.
    mvc = MeshValueCollection("size_t", mesh, 2)
    with XDMFFile(meshname) as infile:
        infile.read(mvc, "name_to_read")
    # Convert to a MeshFunction for use in integration over the domain.
    mf = cpp.mesh.MeshFunctionSizet(mesh, mvc)

    # -----------------------------------------------------
    # Load Boundary (Facet) Markers from the XDMF File
    # -----------------------------------------------------
    # Create a MeshValueCollection for 1D (facet) data.
    mvc_1d = MeshValueCollection("size_t", mesh, 1)
    with XDMFFile(facet_meshname) as infile:
        infile.read(mvc_1d, "name_to_read")
    # Convert to a MeshFunction for boundary integration.
    facets = cpp.mesh.MeshFunctionSizet(mesh, mvc_1d)

    # -----------------------------------------------------
    # Define Integration Measure for Boundary Facets
    # -----------------------------------------------------
    ds = Measure('ds', domain=mesh, subdomain_data=facets)

# ___________________________________________________________________________________________________________________________________________________________

if mesh_choice == 2:                                  # Mode I / Uniaxial Tension
	# Create mesh
	mesh=RectangleMesh(comm, Point(0.0,0.0), Point(W,L), int(W/(32*h)), int(L/(32*h)))
	domain1 = CompiledSubDomain("x[1]<100*h", lch=lch, h=h)
	ir=0
	while ir<2:
		d_markers = MeshFunction("bool", mesh, 2, False)
		domain1.mark(d_markers, True)
		mesh = refine(mesh,d_markers, True)
		ir+=1

	domain2 = CompiledSubDomain("x[1]<4*eps && x[0]<a+eps*10 && x[0]>a-eps*4", a=ac, eps=eps, h=h)
	ir=0
	while ir<3:
		d_markers = MeshFunction("bool", mesh, 2, False)
		domain2.mark(d_markers, True)
		mesh = refine(mesh,d_markers, True)
		ir+=1          


elif mesh_choice == 4:                                 # Mode III
    mesh = Mesh("crack.xml")
    domain2 = CompiledSubDomain("x[0]>12 && x[0]<19 && x[1]<(16) && x[1]>(9)")
    for _ in range(5):
        d_markers = MeshFunction("bool", mesh, 2, False)
        domain2.mark(d_markers, True)
        mesh = refine(mesh, d_markers, True)

elif mesh_choice == 7:                                 # 4-Point Bending
    mesh = Mesh("4P_bending30.xml")
    if notch_angle_choice == 45:                                                                         # 45-degree notch
        domain2 = CompiledSubDomain("x[0]>x[2]-1 && x[0]<x[2]+1 && x[1]<8 && x[1]>5.5")
    elif notch_angle_choice == 30:                                                                        # 30-degree notch
        domain2 = CompiledSubDomain("x[0]>x[2]/sqrt(3)-1 && x[0]<x[2]/sqrt(3)+1 && x[1]<8 && x[1]>5.5")
    
    for _ in range(6):
        d_markers = MeshFunction("bool", mesh, 2, False)
        domain2.mark(d_markers, True)
        mesh = refine(mesh, d_markers, True)

elif mesh_choice == 8:                      # Axisymmetric Indentation
    mesh = RectangleMesh(comm, Point(0.0, 0.0), Point(10.0, -5.0), int(10/(64*h)), int(5/(64*h)))

    domain1 = CompiledSubDomain("x[1]>-2.5 && x[0]<2.5")
    ir = 0
    while ir < 1:
        d_markers = MeshFunction("bool", mesh, 2, False)
        domain1.mark(d_markers, True)
        mesh = refine(mesh, d_markers, True)
        ir += 1

    domain2 = CompiledSubDomain("x[1]>-1.00 && x[0]<2")
    ir = 0
    while ir < 2:
        d_markers = MeshFunction("bool", mesh, 2, False)
        domain2.mark(d_markers, True)
        mesh = refine(mesh, d_markers, True)
        ir += 1

    domain3 = CompiledSubDomain("x[1]>-0.75 && x[0]<1.5")
    ir = 0
    while ir < 3:
        d_markers = MeshFunction("bool", mesh, 2, False)
        domain3.mark(d_markers, True)
        mesh = refine(mesh, d_markers, True)
        ir += 1


elif mesh_choice == 11:                                 # 3D Cylinder|| Compression Test
    mesh = Mesh("crack.xml")

    domain2 = CompiledSubDomain("x[1]>=0")   # CompiledSubDomain("true")

    for _ in range(4):
        d_markers = MeshFunction("bool", mesh, 2, False)
        domain2.mark(d_markers, True)
        mesh = refine(mesh, d_markers, True)




dx = Measure("dx", domain=mesh)
n = FacetNormal(mesh)
m = as_vector([n[1], -n[0]])
# ___________________________________________________________________________________________________________________________________________________________

#righttop = CompiledSubDomain("abs(x[0] - %f) < 1e-4 && abs(x[1] - %f) < 1e-4" % (W, L/2))
righttop = CompiledSubDomain("abs(x[0]-W)<1e-4 && abs(x[1]-L/2)<1e-4", W=W, L=L)
cracktip = CompiledSubDomain("abs(x[1]-0.0)<1e-4 && x[0]<ac+h && x[0]>ac-eps", ac=ac, h=h, eps=eps)
outer = CompiledSubDomain("x[1]>L/10", L=L)
leftbot = CompiledSubDomain("abs(x[1]+side)<1e-4 && abs(x[0]+side)<1e-4", side=W)

if markBC_choice == 2:                                # Mode_I
	# Mark boundary subdomians
	left =  CompiledSubDomain("near(x[0], side, tol) && on_boundary", side = 0.0, tol=1e-4)
	front =  CompiledSubDomain("near(x[0], side, tol) && on_boundary", side = W, tol=1e-4)
	top =  CompiledSubDomain("near(x[1], side, tol) && on_boundary", side = L, tol=1e-4)
	bottom = CompiledSubDomain("x[1]<1e-4 && x[0]>a-1e-4", a=ac)
	cracktip = CompiledSubDomain("x[1]<1e-4 && x[0]>a-eps*4 && x[0]<a+h ", a=ac, eps=eps, h=h)
	righttop = CompiledSubDomain("abs(x[1]-L)<1e-4 && abs(x[0]-W)<1e-4 ", L=L, W=W)
	outer= CompiledSubDomain("x[1]>L/10", L=L)

elif markBC_choice == 4:                                # Mode_III
    # Mark boundary subdomians
    left = CompiledSubDomain("x[0]<1e-4")
    right = CompiledSubDomain("x[0]>Lx-1e-4", Lx=W)
    top = CompiledSubDomain("x[1]>Ly-1e-4", Ly=L)
    bottom = CompiledSubDomain("x[1]<1e-4")
    outer= CompiledSubDomain("x[1]<7 or x[1]>18", Ly=L)
    crack = CompiledSubDomain("abs(x[1]-.5*Ly)<2*h && x[0]<CrackZ+2*h && x[0]>CrackZ-2*h", Ly=L, CrackZ=CrackZ, h=h)

elif markBC_choice == 5:                                # Biaxial Tension
    # Mark boundary subdomians
    left =  CompiledSubDomain("abs(x[0])<1e-4", side = 0, tol=1e-4)
    right =  CompiledSubDomain("abs(x[0]+x[1]-side)<1e-4", side = W, tol=1e-4)
    bottom = CompiledSubDomain("x[1]<1e-4 && x[0]>a-1e-4", a=ac)
    cracktip = CompiledSubDomain("x[1]<1e-4 && x[0]>a-eps*4 && x[0]<a+h ", a=ac, eps=eps, h=h)
    righttop = CompiledSubDomain("abs(x[1]-W)<1e-4 && abs(x[0]-0)<1e-4 ", W=W)
    outer= CompiledSubDomain("x[1]>W/10", W=W)

elif markBC_choice == 7:                                # 4-Point Bending
    if notch_angle_choice == 45:
        left = CompiledSubDomain("abs(x[0]-side)<1e-4", side=-W/2, tol=1e-4)
        right = CompiledSubDomain("abs(x[0]-side)<1e-4", side=W/2, tol=1e-4)
        Pleft = CompiledSubDomain("x[0]>(-20.25) && x[0]<(-20.0) && abs(x[1]-L)<1e-4", L=L)
        Pright = CompiledSubDomain("x[0]>(20) && x[0]<(20.25) && abs(x[1]-L)<1e-4", L=L)
        Rleft = CompiledSubDomain("x[0]>(-36.125) && x[0]<(-35.875) && abs(x[1]-L)<1e-4", L=0)
        Rright = CompiledSubDomain("x[0]>(35.875) && x[0]<(36.125) && abs(x[1]-L)<1e-4", L=0)
        outer = CompiledSubDomain("abs(x[0])>7", W=W, L=L, Lz=Lz)
    
    elif notch_angle_choice == 30:
        left = CompiledSubDomain("abs(x[0]-side)<1e-4", side=-W/2, tol=1e-4)
        right = CompiledSubDomain("abs(x[0]-side)<1e-4", side=W/2, tol=1e-4)
        Pleft = CompiledSubDomain("x[0]>(-20.25) && x[0]<(-20.0) && abs(x[1]-L)<1e-4", L=L)
        Pright = CompiledSubDomain("x[0]>(20) && x[0]<(20.25) && abs(x[1]-L)<1e-4", L=L)
        Rleft = CompiledSubDomain("x[0]>(-36.125) && x[0]<(-35.875) && abs(x[1]-L)<1e-4", L=0)
        Rright = CompiledSubDomain("x[0]>(35.875) && x[0]<(36.125) && abs(x[1]-L)<1e-4", L=0)
        outer = CompiledSubDomain("abs(x[0])>7", W=W, L=L, Lz=Lz)

elif markBC_choice == 8:  # Axisymmetric Indentation
    left = CompiledSubDomain("near(x[0], side, tol) && on_boundary", side=0.0, tol=1e-4)
    front = CompiledSubDomain("near(x[0], side, tol) && on_boundary", side=10.0, tol=1e-4)
    bottom = CompiledSubDomain("near(x[1], side, tol) && on_boundary", side=-5.0, tol=1e-4)
    top = CompiledSubDomain("near(x[1], side, tol) && on_boundary", side=0.0, tol=1e-4)

    def loadset(x):
        return 0.0 - 1e-4 < x[0] < 0.1 + 1e-4 and abs(x[1] - 0.0) < 1e-4

    def outer(x):
        return x[0] > 3.5 or x[1] < -2.0
    
    def loadsetz(x):
	    return x[0]>0-1e-4 and x[0]<-0.55+1e-4 #and abs(x[1]-0)<1e-4


elif markBC_choice == 11:                                # 3D Cylinder|| Compression Test
    # Mark boundary subdomians   
    top = CompiledSubDomain("on_boundary && near(x[1], L, tol)", L=L, tol=1e-4)
    bottom = CompiledSubDomain("on_boundary && near(x[1], 0.0, tol)", tol=1e-4)
    rightbot = CompiledSubDomain("abs(x[0]-W/2)<1e-4 && abs(x[1]-0)<1e-4 && abs(x[2]-0)<1e-4", W=W, L=L)

# ___________________________________________________________________________________________________________________________________________________________


#Don't need to change anything from here on.
########################################################

set_log_level(40)  #Error level=40, warning level=30
parameters["linear_algebra_backend"] = "PETSc"
parameters["form_compiler"]["quadrature_degree"] = 4
parameters["form_compiler"]["cpp_optimize"] = True
ffc_options = {"optimize": True, \
            "eliminate_zeros": True, \
            "precompute_basis_const": True, \
            "precompute_ip_const": True}


# ___________________________________________________________________________________________________________________________________________________________
# Define function space
V = VectorFunctionSpace(mesh, "CG", 1)   #Function space for u
Y = FunctionSpace(mesh, "CG", 1)         #Function space for z



if DirichletBC_choice == 1:   # Surfing Problem
    # Define displacement expressions (for u)
    c  = Expression("K1/(2*mu)*sqrt(sqrt(pow(x[0]-V*(t+0.1),2)+pow(x[1],2))/(2*pi))*(kap-cos(atan2(x[1], (x[0]-V*(t+0.1)))))*cos(atan2(x[1], (x[0]-V*(t+0.1)))/2)",
                    degree=4, t=0, V=20, K1=30, mu=4336.28, kap=2.54)
    r  = Expression("K1/(2*mu)*sqrt(sqrt(pow(x[0]-V*(t+0.1),2)+pow(x[1],2))/(2*pi))*(kap-cos(atan2(x[1], (x[0]-V*(t+0.1)))))*sin(atan2(x[1], (x[0]-V*(t+0.1)))/2)",
                    degree=4, t=0, V=20, K1=30, mu=4336.28, kap=2.54)
    c0 = Expression("(K1/(2*mu)*sqrt(sqrt(pow(x[0]-V*(t+0.1),2)+pow(x[1],2))/(2*pi))*(kap-cos(atan2(x[1], (x[0]-V*(t+0.1)))))*cos(atan2(x[1], (x[0]-V*(t+0.1)))/2))"
                    "-(K1/(2*mu)*sqrt(sqrt(pow(x[0]-V*(tau+0.1),2)+pow(x[1],2))/(2*pi))*(kap-cos(atan2(x[1], (x[0]-V*(tau+0.1)))))*cos(atan2(x[1], (x[0]-V*(tau+0.1)))/2))",
                    degree=4, t=0, tau=0, V=20, K1=30, mu=4336.28, kap=2.54)
    r0 = Expression("(K1/(2*mu)*sqrt(sqrt(pow(x[0]-V*(t+0.1),2)+pow(x[1],2))/(2*pi))*(kap-cos(atan2(x[1], (x[0]-V*(t+0.1)))))*sin(atan2(x[1], (x[0]-V*(t+0.1)))/2))"
                    "-(K1/(2*mu)*sqrt(sqrt(pow(x[0]-V*(tau+0.1),2)+pow(x[1],2))/(2*pi))*(kap-cos(atan2(x[1], (x[0]-V*(tau+0.1)))))*sin(atan2(x[1], (x[0]-V*(tau+0.1)))/2))",
                    degree=4, t=0, tau=0, V=20, K1=30, mu=4336.28, kap=2.54)
    
    # Displacement BCs: Fix x-displacement at "righttop" and prescribe y-displacement on Top and Bottom.
    bc_rt = DirichletBC(V.sub(0), Constant(0.0), righttop, method='pointwise')
    bc_bot = DirichletBC(V.sub(1), r, facets, 22)
    bc_top = DirichletBC(V.sub(1), r, facets, 21)
    bcs = [bc_rt, bc_bot, bc_top]
    
    # Phase-field BCs: Impose z = 1 on Top and Bottom and z = 0 on the Crack.
    cz   = Constant(1.0)
    cz2  = Constant(0.0)
    bcb_z = DirichletBC(Y, cz, facets, 22)
    bct_z = DirichletBC(Y, cz, facets, 21)
    bcc_z = DirichletBC(Y, cz2, cracktip)   # DirichletBC(Y, cz2, facets, 25)
    bcs_z = [bcb_z, bct_z, bcc_z]
    
    # Additional stabilization BCs for u_y (if needed)
    bcb_du = DirichletBC(V.sub(1), Constant(0.0), facets, 22)
    bct_du = DirichletBC(V.sub(1), Constant(0.0), facets, 21)
    bcs_du = [bc_rt, bcb_du, bct_du]

elif DirichletBC_choice == 2:   # Mode I
    # No displacement on u_y
    c = Expression("t*0.0", degree=1, t=0)
    bc_rt = DirichletBC(V.sub(0), Constant(0.0), righttop, method='pointwise')
    bc_bot = DirichletBC(V.sub(1), c, bottom)
    bcs = [bc_rt, bc_bot]
    
    cz = Constant(1.0)
    bct_z = DirichletBC(Y, cz, outer)
    cz2 = Constant(0.0)
    bct_z2 = DirichletBC(Y, cz2, cracktip)
    bcs_z = [bct_z, bct_z2]
    
    # Define Neumann BC (loading) for Mode I
    sigma_critical_crack = sqrt(E*Gc/np.pi/ac) / ((0.752 + 2.02*(ac/W) + 0.37*(1 - np.sin(np.pi*ac/2/W))**3) *
                                                   (sqrt(2*W/np.pi/ac * np.tan(np.pi*ac/2/W)))/(np.cos(np.pi*ac/2/W)))
    sigma_critical = sts if sigma_critical_crack > sts else sigma_critical_crack
    sigma_external = loadfactor * sigma_critical
    Tf = Expression(("t*0.0", "t*sigma"), degree=1, t=0, sigma=sigma_external)
	# marking boundary on which Neumann bc is applied
    boundary_subdomains = MeshFunction("size_t", mesh, 1)
    boundary_subdomains.set_all(0)
    top.mark(boundary_subdomains,1)	
    ds = ds(subdomain_data=boundary_subdomains) 

elif DirichletBC_choice == 3:   # Mode II
    c = Expression(("v0_imp * t", "t*0.0"), degree=1, t=0, v0_imp=v0_imp)
    bc_bot = DirichletBC(V, Constant((0.0, 0.0)), facets, 22)
    bc_top = DirichletBC(V, c, facets, 21)
    bcs = [bc_bot, bc_top]
    
    cz = Constant(1.0)
    bcb_z = DirichletBC(Y, cz, facets, 22)
    bct_z = DirichletBC(Y, cz, facets, 21)
    cz2 = Constant(0.0)
    bct_z2 = DirichletBC(Y, cz2, cracktip)
    bcs_z = []

elif DirichletBC_choice == 4:   # Mode III
    r = Expression("t*v0_imp",degree=1,t=0,v0_imp=v0_imp)
    r0 = Expression("(t-tau)*v0_imp",degree=1,t=0,tau=0, v0_imp=v0_imp)

    # Define Dirichlet boundary conditions
    c=Expression("0.0",degree=1,t=0)
                                    
    bct= DirichletBC(V.sub(2), r, top)
    bct2= DirichletBC(V.sub(1), c, top)
    bct3= DirichletBC(V.sub(0), c, top)
    bcb= DirichletBC(V.sub(0), c, bottom)
    bcb2= DirichletBC(V.sub(1), c, bottom)
    bcb3= DirichletBC(V.sub(2), c, bottom)
    bcs = [bct, bct2, bct3, bcb, bcb2, bcb3]

    bct0= DirichletBC(V.sub(2), r0, top)
    bcs_du0 = [bct0, bct2, bct3, bcb, bcb2, bcb3]

    bct1= DirichletBC(V.sub(2), c, top)
    bcs_du = [bct1, bct2, bct3, bcb, bcb2, bcb3]

    cz=Constant(1.0)
    cz2=Constant(0.0)
    bct_z = DirichletBC(Y, cz, outer)
    bct_z2 = DirichletBC(Y, cz2, crack)
    bcs_z=[bct_z]

    bct_dz = DirichletBC(Y, Constant(0.0), outer)
    bct_dz2 = DirichletBC(Y, Constant(0.0), crack)
    bcs_dz=[bct_dz]

elif DirichletBC_choice == 5:   # Biaxial
    # Define Dirichlet boundary conditions
    c=Expression("t*0.0",degree=1,t=0)
    								
    #bcl= DirichletBC(V.sub(0), Constant(0.0), righttop, method='pointwise'  )
    bcl = DirichletBC(V.sub(0), c, left)
    bcb = DirichletBC(V.sub(1), c, bottom)
    bcs = [bcl, bcb]
    
    cz=Constant(1.0)
    bct_z = DirichletBC(Y, cz, outer)
    cz2=Constant(0.0)
    bct_z2 = DirichletBC(Y, cz2, cracktip)
    bcs_z=[]
    
    sigma_external = 1.05 * sqrt(E * Gc / np.pi / ac)
    Tf = Expression("t*sigma", degree=1, t=0, sigma=sigma_external)

elif DirichletBC_choice == 6:   # Pure Shear
    c = Expression(("t*0.0", "t*0.0"), degree=1, t=0)
    bc_lb = DirichletBC(V, c, leftbot, method='pointwise')
    bcs = [bc_lb]
    
    cz = Constant(1.0)
    bct_z = DirichletBC(Y, cz, outer)
    cz2 = Constant(0.0)
    bct_z2 = DirichletBC(Y, cz2, cracktip)
    bcs_z = []
    
    sigma_external = 1.1 * sqrt(E * Gc / np.pi / ac)
    Tf = Expression("t*sigma", degree=1, t=0, sigma=sigma_external)

elif DirichletBC_choice == 7:   # 4-P Bending
    cr = Expression(("t*0.0", "t*0.0", "t*0.0"), degree=1, t=0)
    crr = Expression("t*0.0", degree=1, t=0)
    cl = Expression("-v0_imp*t", degree=1, t=0, v0_imp=v0_imp)
    
    bcrl = DirichletBC(V, cr, Rleft)             # Left Reaction Restraint
    bcrry = DirichletBC(V.sub(1), crr, Rright)   # Right Reaction Restraint
    bcrrz = DirichletBC(V.sub(2), crr, Rright)   # Right Reaction Restraint
    bcll = DirichletBC(V.sub(1), cl, Pleft)      # Left Loading Point
    bclr = DirichletBC(V.sub(1), cl, Pright)     # Right Loading Point
    bcs = [bcrl, bcrry, bcrrz, bcll, bclr]

    bcrl0 = DirichletBC(V, cr, Rleft)             # Left Reaction Restraint
    bcrry0 = DirichletBC(V.sub(1), Constant(0.0), Rright)   # Right Reaction Restraint
    bcrrz0 = DirichletBC(V.sub(2), Constant(0.0), Rright)   # Right Reaction Restraint
    bcll0 = DirichletBC(V.sub(1), Constant(0.0), Pleft)      # Left Loading Point
    bclr0 = DirichletBC(V.sub(1), Constant(0.0), Pright)     # Right Loading Point
    bcs_du = [bcrl0, bcrry0, bcrrz0, bcll0, bclr0]

    cz = Constant(1.0)
    bct_z = DirichletBC(Y, cz, outer)
    cz2 = Constant(0.0)
    bct_z2 = DirichletBC(Y, cz2, cracktip)
    bcs_z = [bct_z]

elif DirichletBC_choice == 8: # Axisymmetric Indentation
    c=Expression("t*0.0",degree=1,t=0)
    r=Expression("-t*0.05",degree=1,t=0)
    r0=Expression("-(t-tau)*0.05",degree=1,t=0,tau=0)
								
    bcl = DirichletBC(V.sub(0), c, left )
    bcb = DirichletBC(V.sub(1), c, bottom )
    bct = DirichletBC(V.sub(1), r, loadset)
    bcs = [bcl, bcb, bct]

    cz=Constant(1.0)
    bct_z = DirichletBC(Y, cz, outer)
    bct_z2 = DirichletBC(Y, cz, loadsetz)
    cz2=Constant(0.0)
    bcs_z=[bct_z, bct_z2]

    bct_du=DirichletBC(V.sub(1),Constant(0.0),loadset)
    bct_du0=DirichletBC(V.sub(1), r0, loadset)
    bcs_du = [bcl, bcb, bct_du]
    cs_du0 = [bcl, bcb, bct_du0]

    d_dz=Constant(0.0)
    bct_dz = DirichletBC(Y, d_dz, outer)
    bct_dz2 = DirichletBC(Y, d_dz, loadsetz)
    bcs_dz=[bct_dz, bct_dz2]

elif DirichletBC_choice == 9:   # Mode I, Displacement BCs
    cp = Expression(("0 * t", "v0_imp * t"), degree=1, t=0, v0_imp=v0_imp)
    cn = Expression(("0 * t", "v0_imp * t"), degree=1, t=0, v0_imp=-v0_imp)

    bc_rt = DirichletBC(V.sub(0), Constant(0.0), righttop, method='pointwise')
    bc_top = DirichletBC(V, cp, facets, 21)
    bc_bot = DirichletBC(V, cn, facets, 22)
    bcs = [bc_rt, bc_bot, bc_top]
    
    cz = Constant(1.0)
    bcb_z = DirichletBC(Y, cz, facets, 22)
    bct_z = DirichletBC(Y, cz, facets, 21)
    cz2 = Constant(0.0)
    bct_z2 = DirichletBC(Y, cz2, cracktip)
    bcs_z = []    

elif DirichletBC_choice == 10:   # Compression Test, Section 3.5.4
    test_type=1

    if test_type==1: 
        cn = Expression(("0 * t", "v0_imp * t"), degree=1, t=0, v0_imp=-v0_imp)

        bc_top = DirichletBC(V, cn, facets, 21)
        bc_bot = DirichletBC(V, Constant((0.0, 0.0)), facets, 22)
        bcs = [bc_bot, bc_top]
        
        bc0_top = DirichletBC(V, Constant((0.0, 0.0)), facets, 21)
        bc0_bot = DirichletBC(V, Constant((0.0, 0.0)), facets, 22)
        bcs_du = [bc0_bot, bc0_top]

    elif test_type == 3: 
        cn = Expression("v0_imp * t", degree=1, t=0, v0_imp=-v0_imp)
        
        bc_rt = DirichletBC(V.sub(0), Constant(0.0), righttop, method='pointwise')
        bc_top = DirichletBC(V.sub(1), cn, facets, 21)
        bc_bot = DirichletBC(V.sub(1), Constant(0.0), facets, 22)
        bcs = [bc_rt, bc_bot, bc_top]

        bc0_top = DirichletBC(V.sub(1), Constant(0.0), facets, 21)
        bc0_bot = DirichletBC(V.sub(1), Constant(0.0), facets, 22)
        bcs_du = [bc_rt, bc0_bot, bc0_top]


    cz = Constant(1.0)
    bcb_z = DirichletBC(Y, cz, facets, 22)
    bct_z = DirichletBC(Y, cz, facets, 21)
    cz2 = Constant(0.0)
    bct_z2 = DirichletBC(Y, cz2, cracktip)
    bcs_z = []    

elif DirichletBC_choice == 11:   # Compression Test, Section 3.5.4 # 3D Cylinder
    test_type=1

    if test_type==1: 
        cn = Expression(("0 * t", "v0_imp * t", "0 * t"), degree=1, t=0, v0_imp=-v0_imp)
        cn0 = Expression(("0 * (t-tau)", "v0_imp * (t-tau)", "0 * (t-tau)"), degree=1, t=0, tau=0.0, v0_imp=-v0_imp)

        bc_top = DirichletBC(V, cn, top)
        bc_bot = DirichletBC(V, Constant((0.0, 0.0, 0.0)), bottom)
        bcs = [bc_bot, bc_top]

        bc00_top = DirichletBC(V, cn0, top)
        bc00_bot = DirichletBC(V, Constant((0.0, 0.0, 0.0)), bottom)
        bcs_du0 = [bc00_bot, bc00_top]

        bc0_top = DirichletBC(V, Constant((0.0, 0.0, 0.0)), top)
        bc0_bot = DirichletBC(V, Constant((0.0, 0.0, 0.0)), bottom)
        bcs_du = [bc0_bot, bc0_top]

    elif test_type == 3: 
        cn = Expression("v0_imp * t", degree=1, t=0, v0_imp=-v0_imp)
        
        bc_rb = DirichletBC(V.sub(0), Constant(0.0), rightbot, method='pointwise')
        bc_top = DirichletBC(V.sub(1), cn, top)
        bc_bot = DirichletBC(V.sub(1), Constant(0.0), bottom)
        bcs = [bc_rb, bc_bot, bc_top]

        bc0_top = DirichletBC(V.sub(1), Constant(0.0), top)
        bc0_bot = DirichletBC(V.sub(1), Constant(0.0), bottom)
        bcs_du = [bc_rb, bc0_bot, bc0_top]

    cz = Constant(1.0)
    bcb_z = DirichletBC(Y, cz, top)
    bct_z = DirichletBC(Y, cz, bottom)
    
    bcs_z = []    
# ___________________________________________________________________________________________________________________________________________________________


# Define functions
du = TrialFunction(V)            # Incremental displacement
v  = TestFunction(V)             # Test function
u  = Function(V)                 # Displacement from previous iteration
u_inc = Function(V)
dz = TrialFunction(Y)            # Incremental phase field
y  = TestFunction(Y)             # Test function
z  = Function(Y)                 # Phase field from previous iteration
z_inc = Function(Y)
d = u.geometric_dimension()
B  = Constant((0.0, 0.0))  # Body force per unit volume

# ___________________________________________________________________________________________________________________________________________________________


# Common initialization for displacement field (u) and phase field (z)
# Set problem dimension: 2 for 2D, 3 for 3D

if comm_rank == 0: 
    print(" mesh topological dim:", mesh.topology().dim())
    print(" mesh geometric  dim:", mesh.geometry().dim())


# Set the dimension-specific constant for displacement initialization.
u_dim = (0.0, 0.0) if problem_dim == 2 else (0.0, 0.0, 0.0)

# ---------------------------
# Common initialization for displacement (u) and phase field (z)
# ---------------------------
u_init = Constant(u_dim)
u.interpolate(u_init)
for bc in bcs:
    bc.apply(u.vector())

z_init = Constant(1.0)
z.interpolate(z_init)
for bc in bcs_z:
    bc.apply(z.vector())

z_ub = Function(Y)
z_ub.interpolate(Constant(1.0))
z_lb = Function(Y)
z_lb.interpolate(Constant(-0.0))

u_prev = Function(V)
assign(u_prev, u)
z_prev = Function(Y)
assign(z_prev, z)

z_trial = Function(Y)
assign(z_trial,z)

# ---------------------------
# Helper function: Extract DOFs on boundary
# ---------------------------
if problem_type in (1, 3, 6, 9, 10):
    def extract_dofs_boundary(V, facets, bsubd):
        # Use a constant vector of ones whose length depends on the problem dimension
        bc_val = Constant((1, 1)) if problem_dim == 2 else Constant((1, 1, 1))
        # For 3D, use method='pointwise'; for 2D the default is sufficient.
        label_bc = DirichletBC(V, bc_val, facets, bsubd)
        label = Function(V)
        label_bc.apply(label.vector())
        return np.where(label.vector() == 1)[0]

else: 
    def extract_dofs_boundary(V, bsubd):	
        label = Function(V)
        label_bc_bsubd = DirichletBC(V, Constant((1,1,1)), bsubd)
        label_bc_bsubd.apply(label.vector())
        bsubd_dofs = np.where(label.vector()==1)[0]
        return bsubd_dofs
# ---------------------------
# Helper function: Evaluate a field at a given point
# ---------------------------
def evaluate_function(u, x):
    comm = u.function_space().mesh().mpi_comm()
    if comm.size == 1:
        return u(*x)
    cell, distance = mesh.bounding_box_tree().compute_closest_entity(Point(*x))
    u_eval = u(*x) if distance < DOLFIN_EPS else None
    comm = mesh.mpi_comm()
    computed_u = comm.gather(u_eval, root=0)
    if comm.rank == 0:
        global_u_evals = np.array([y for y in computed_u if y is not None], dtype=np.double)
        # Ensure consistency across processes.
        assert np.all(np.abs(global_u_evals[0] - global_u_evals) < 1e-9)
        computed_u = global_u_evals[0]
    else:
        computed_u = None
    computed_u = comm.bcast(computed_u, root=0)
    return computed_u


# ___________________________________________________________________________________________________________________________________________________________

def local_project(v, V, u=None):
    """Element-wise projection using LocalSolver"""
    dv = TrialFunction(V)
    v_ = TestFunction(V)
    a_proj = inner(dv, v_)*dx
    b_proj = inner(v, v_)*dx
    solver = LocalSolver(a_proj, b_proj)
    solver.factorize()
    if u is None:
        u = Function(V)
        solver.solve_local_rhs(u)
        return u
    else:
        solver.solve_local_rhs(u)
        return
    

# ___________________________________________________________________________________________________________________________________________________________

# Condition-specific code
if problem_type == 1:                                                  # Surfing problem
    top_dofs = extract_dofs_boundary(V, facets, 21)
    y_dofs_top = top_dofs[1::d]

elif problem_type == 2:                                                # Mode I
    top_dofs = extract_dofs_boundary(V, top)
    y_dofs_top = top_dofs[1::d]

elif problem_type == 3:                                                # Mode II
    top_dofs = extract_dofs_boundary(V, facets, 21)
    y_dofs_top = top_dofs[0::d]

elif problem_type == 4:                                                # Mode III
    top_dofs=extract_dofs_boundary(V, top)
    y_dofs_top = top_dofs[2::d]

elif problem_type == 5:                                                # Biaxial
    top_dofs = extract_dofs_boundary(V, facets, 24)
    y_dofs_top = top_dofs[1::d]

elif problem_type == 6:                                                # Pure Shear
    top_dofs = extract_dofs_boundary(V, facets, 21)
    y_dofs_top = top_dofs[0::d]

elif problem_type == 7:                                                 # 4-P Bending
    Rleft_dofs = extract_dofs_boundary(V, Rleft)
    y_dofs_Rleft = Rleft_dofs[1::d]

    Rright_dofs = extract_dofs_boundary(V, Rright)
    y_dofs_Rright = Rright_dofs[1::d]

    Pleft_dofs = extract_dofs_boundary(V, Pleft)
    y_dofs_Pleft = Pleft_dofs[1::d]

    Pright_dofs = extract_dofs_boundary(V, Pright)
    y_dofs_Pright = Pright_dofs[1::d]

elif problem_type == 8:
    top_dofs = extract_dofs_boundary(V, loadset)
    y_dofs_top = top_dofs[1::d]

elif problem_type == 9:                                                  # Mode I, Displacement BCs
    top_dofs = extract_dofs_boundary(V, facets, 21)
    bot_dofs = extract_dofs_boundary(V, facets, 22)
    y_dofs_top = top_dofs[1::d]
    y_dofs_bot = top_dofs[1::d]

elif problem_type == 10:                                                  # Compression Test, Section 3.5.4
    top_dofs = extract_dofs_boundary(V, facets, 21)
    bot_dofs = extract_dofs_boundary(V, facets, 22)
    y_dofs_top = top_dofs[1::d]
    y_dofs_bot = top_dofs[1::d]

elif problem_type == 11:                                                # Compression Test, Section 3.5.4 || 3D Cylinder
    top_dofs = extract_dofs_boundary(V, top)
    bot_dofs = extract_dofs_boundary(V, bottom)
    y_dofs_top = top_dofs[1::d]  
    y_dofs_bot = top_dofs[1::d]  

# ___________________________________________________________________________________________________________________________________________________________


# Elasticity parameters
mu, lmbda, kappa = Constant(E/(2*(1 + nu))), Constant(E*nu/((1 + nu)*(1 - 2*nu))), Constant(E/(3*(1 - 2*nu))) 

# Set stress state parameters based on choice
if stress_state_choice == 1:  # Plane stress

    def epsilon(v):
        return sym(grad(v))

    def tr_modified(eps):
        return (1 - 2 * nu) / (1 - nu) * tr(eps)

    def energy(v):
        eps = epsilon(v)
        return mu * (inner(eps, eps) + ((nu / (1 - nu)) ** 2) * (tr(eps)) ** 2) + 0.5 * lmbda * (tr_modified(eps)) ** 2

    def sigma(v):
        eps = epsilon(v)
        return 2.0 * mu * eps + lmbda * tr_modified(eps) * Identity(len(v))

    def epsilon_dev(v):
        eps = epsilon(v)
        return eps - (1 / 3) * tr_modified(eps) * Identity(len(v))

    def sigmavm(sig, v):
        dev_stress = sig - (1 / 3) * tr(sig) * Identity(len(v))
        return sqrt(0.5 * (inner(dev_stress, dev_stress) + (1 / 9) * tr(sig) ** 2))

elif stress_state_choice in [2, 3]:  # Plane strain or 3D

    def epsilon(v):
        return sym(grad(v))
    
    def tr_modified(eps):
        return tr(eps)

    def energy(v):
        eps = epsilon(v)
        return mu * inner(eps, eps) + 0.5 * lmbda * (tr_modified(eps)) ** 2

    def sigma(v):
        eps = epsilon(v)
        return 2.0 * mu * eps + lmbda * tr_modified(eps) * Identity(len(v))

    def epsilon_dev(v):
        eps = epsilon(v)
        return eps - (1 / 3) * tr_modified(eps) * Identity(len(v))

    def sigmavm(sig, v):
        
        if stress_state_choice == 2:
            dev_stress = sig - 1/3*(1+nu)*tr(sig)*Identity(len(v))
            return sqrt(0.5 * (inner(dev_stress, dev_stress) + ((2 * nu / 3 - 1 / 3) ** 2) * tr(sig) ** 2))
        else:  # 3D
            dev_stress = sig - 1/3*tr(sig)*Identity(len(v))
            return sqrt(0.5 * inner(dev_stress, dev_stress))

elif stress_state_choice == 4:  # Axisymmetric
    xm = SpatialCoordinate(mesh)

    def epsilon(v):
        return sym(as_tensor([
            [v[0].dx(0), v[0].dx(1), 0.0],
            [v[1].dx(0), v[1].dx(1), 0.0],
            [0.0,0.0,v[0]/xm[0]]
        ]))

    def energy(v):
        eps = epsilon(v)
        return mu * inner(eps, eps) + 0.5 * lmbda * (tr(eps)) ** 2

    def sigma(v):
        eps = epsilon(v)
        return 2.0 * mu * eps + lmbda * tr(eps) * Identity(3)

    def sigmavm(sig, v):
        dev_stress = sig - (1 / 3) * tr(sig) * Identity(3)
        return sqrt(0.5 * inner(dev_stress, dev_stress))


else:
    raise ValueError("Invalid stress state. Choose 1 (Plane stress), 2 (Plane strain), 3 (3D), or 4 (Axisymmetric).")



def safe_sqrt(x):
    # A safe square root that avoids negative arguments
    return sqrt(x + 1.0e-16)

def compute_eigenvalues(A, problem_dim=None):
    
    if problem_dim == 2:
        # 2D case: closed-form solution for a 2x2 tensor
        eig1 = (tr(A) + sqrt(abs(tr(A)**2 - 4 * det(A)))) / 2
        eig2 = (tr(A) - sqrt(abs(tr(A)**2 - 4 * det(A)))) / 2 
        return eig1, eig2

    elif problem_dim == 3:
        # 3D case: analytical solution based on invariants.
        Id = Identity(3)
        I1 = tr(A)
        I2 = (tr(A)**2 - tr(A*A)) / 2.0  # second invariant (not used here)
        I3 = det(A)                     # third invariant
        
        # Parameters for eigenvalue computation
        d_par = I1 / 3.0
        e_par = safe_sqrt(tr((A - d_par*Id)*(A - d_par*Id)) / 6.0)
        
        # Define f_par carefully to avoid division by zero
        zero = 0 * Id
        f_par_expr = (1.0 / e_par) * (A - d_par * Id)
        f_par = conditional(eq(e_par, 0), zero, f_par_expr)
        
        # Compute the argument of the acos, and bound it to [-1, 1]
        g_par0 = det(f_par) / 2.0
        tol = 3.e-16  # tolerance to avoid acos issues at the boundaries
        g_par1 = conditional(ge(g_par0, 1.0 - tol), 1.0 - tol, g_par0)
        g_par = conditional(le(g_par1, -1.0 + tol), -1.0 + tol, g_par1)
        
        # Angle for the eigenvalue formulas
        h_par = acos(g_par) / 3.0
        
        # Compute the eigenvalues (ordered such that eig1 >= eig2 >= eig3)
        eig3 = d_par + 2.0 * e_par * cos(h_par + 2.0 * np.pi / 3.0)
        eig2 = d_par + 2.0 * e_par * cos(h_par + 4.0 * np.pi / 3.0)
        eig1 = d_par + 2.0 * e_par * cos(h_par + 6.0 * np.pi / 3.0)
        return eig1, eig2, eig3

    else:
        raise ValueError("Dimension not supported. Only 2D and 3D cases are implemented.")



# ---------------------------------------------------------------------------------------------------------------------------------------------
# 1. Kumar JMPS2020        
# ---------------------------------------------------------------------------------------------------------------------------------------------
if phase_model == 1:
    
    shs_DP = (2*scs*sts)/(3*(scs-sts))
    shs_MC = (scs*sts)/(scs-sts)
    
    if(shs_delta_choice==2 and strength_surface_choice==2):
        shs_delta = shs_MC        
    else:
        shs_delta = shs_DP    
    
    Wts = 0.5*(sts**2)/E
    if strength_surface_choice == 1:
        delta = (1+3*h/(8*eps))**(-2) * ((sts+(1+2*sqrt(3))*shs_delta)/((8+3*sqrt(3))*shs_delta)) * 3*Gc/(16*Wts*eps) + (1+3*h/(8*eps))**(-1) * (2/5)
    elif strength_surface_choice == 2:
        delta = (1+3*h/(8*eps))**(-2) * (5/(3+8*sqrt(3))) * 3*Gc/(16*Wts*eps) + (1+3*h/(8*eps))**(-1) * (9/(8*sqrt(3)))
    
    alpha_tc = sts/scs
    alpha_ct = 1/alpha_tc
    Wcs = (alpha_ct**2)*Wts
    
    omega_eps = (3*Gc*delta)/8/eps
    
    #Chockalingam JAM 2025
    if(strength_surface_choice==1): #DP
        shs = (2*scs*sts)/(3*(scs-sts))
        Whs = 0.5*(shs**2)/kappa
        alpha_th = sts/shs
        alpha_tb = 1.5 - 0.5*alpha_tc 
        sbs = sts/alpha_tb
        alpha_bt = 1/alpha_tb
        alpha_ts = 0.5*sqrt(3)*(1+alpha_tc)
        alpha_st = 1/alpha_ts
        sss = sts/alpha_ts
        Wbs = ((alpha_bt**2)/6)*(sts**2)*(1/mu + 4/3/kappa)
        Wss = 0.5*(sts**2.0)*((alpha_st**2.0)/mu)
        if(calibrationchoice==1): #sts sss
            beta1_eps = (1-alpha_ts/sqrt(3)) - (2/omega_eps)*(Wts - alpha_ts*Wss/sqrt(3))
            beta2_eps = alpha_ts*(1-2*Wss/omega_eps)
            fname_prefix = 'DP_sts_sss'
        elif(calibrationchoice==2): #sts sbs
            beta1_eps = (alpha_tb-1) - (2/omega_eps)*(alpha_tb*Wbs - Wts)
            beta2_eps = sqrt(3)*(2 - alpha_tb) -(2*sqrt(3)/omega_eps)*(2*Wts - alpha_tb*Wbs)
            fname_prefix = 'DP_sts_sbs'
        elif(calibrationchoice==3): #sts shs
            beta1_eps = alpha_th/3 - (2*alpha_th/3)*(Whs/omega_eps)
            beta2_eps = sqrt(3) - alpha_th/sqrt(3) - 2*sqrt(3)*(Wts/omega_eps) + (2*alpha_th/sqrt(3))*(Whs/omega_eps)
            fname_prefix = 'DP_sts_shs'        
    
    elif(strength_surface_choice==2):  #MC   
        alpha_bt = 1
        Wbs = ((alpha_bt**2)/6)*(sts**2)*(1/mu + 4/3/kappa)
        alpha_ts = 1 + alpha_tc
        alpha_st = 1/alpha_ts
        Wss = 0.5*(sts**2.0)*((alpha_st**2.0)/mu)
        if(calibrationchoice==1): #sts sss     
            beta1_eps = 1 - 2*(Wts/omega_eps)
            beta2_eps = (1 - alpha_ts) + alpha_ts*(2*Wss/omega_eps) - 2*(Wts/omega_eps)
            fname_prefix = 'MC_sts_sss'
        elif(calibrationchoice==2): #sts scs                
            beta1_eps = 1 - 2*(Wts/omega_eps)
            beta2_eps = -alpha_tc*(1- 2*(Wcs/omega_eps))
            fname_prefix = 'MC_sts_scs'
        elif(calibrationchoice==3): #sss sbs
            beta1_eps = 1 - 2*(Wbs/omega_eps)
            beta2_eps = (1 - alpha_ts) + alpha_ts*(2*Wss/omega_eps) - 2*(Wbs/omega_eps)
            fname_prefix = 'MC_sss_sbs'

    beta1 =  -beta1_eps*(omega_eps)/sts
    beta2  = -beta2_eps*(omega_eps)/sts

    pen=1000*(3*Gc/8/eps) * conditional(lt(delta, 1), 1, delta)
    
    # Stored strain energy density (compressible L-P model)
    psi1 =(z**2+eta)*(energy(u))    
    psi11=energy(u)
    stress=(z**2+eta)*sigma(u)
    
    # Total potential energy
    if problem_type in (1, 3, 4, 7, 9, 10, 11):
        Pi = psi1*dx

    if problem_type == 2:
        Pi = psi1*dx - dot(Tf, u)*ds(1)

    elif problem_type == 5:
        Pi = psi1*dx - dot(Tf*n, u)*ds(1)

    elif problem_type == 6: 
        Pi = psi1*dx - (dot(-Tf*m, u)*ds(23) + dot(-Tf*m, u)*ds(24) + dot(Tf*m, u)*ds(21) + dot(Tf*m, u)*ds(22))
    
    elif problem_type == 8:
        Pi = psi1*2*np.pi*xm[0]*dx


    I1_d = (z**2)*tr(sigma(u))
    if strength_surface_choice==1: #DP
        I1_d = (z**2)*tr(sigma(u))
        SQJ2_d = (z**2)*sigmavm(sigma(u),u)
        ce = beta2*SQJ2_d + beta1*I1_d

    elif strength_surface_choice == 2: #MC
        # Determine the tensor dimension from σ(u)
        # dim = sigma(u).ufl_shape()[0]
        
        if stress_state_choice == 1:                                                                # Plane Stress
            # For a 2D problem: compute the two eigenvalues.
            eig1_val, eig2_val = compute_eigenvalues(sigma(u), problem_dim)
            sigma_p1 = eig1_val
            sigma_p2 = eig2_val
			
			# Only consider positive part for tensile and negative part for compressive response.
            sigma_max_d = (z**2) * conditional(gt(sigma_p1, 0), sigma_p1, 0)
            sigma_min_d = (z**2) * conditional(lt(sigma_p2, 0), sigma_p2, 0)

        if stress_state_choice == 2:                                                                # Plane Strain
            # For a 2D problem: compute the two eigenvalues.
            eig1_val, eig2_val = compute_eigenvalues(sigma(u), problem_dim)
            eig3_val = nu * tr(sigma(u))
            sigma_p1 = max(eig1_val, eig2_val, eig3_val)
            sigma_p2 = min(eig1_val, eig2_val, eig3_val)
            sigma_max_d = (z**2) * sigma_p1
            sigma_min_d = (z**2) * sigma_p2

        elif stress_state_choice in [3,4]:                                                              # 3D, Axisymmetric 
            # For a 3D problem: compute the three eigenvalues.
            eig1_val, eig2_val, eig3_val = compute_eigenvalues(sigma(u), problem_dim)
            sigma_p1 = eig1_val   # largest eigenvalue (tensile candidate)
            sigma_p2 = eig3_val   # smallest eigenvalue (compressive candidate)
            sigma_max_d = (z**2) * sigma_p1
            sigma_min_d = (z**2) * sigma_p2
			
        
        
        # Combine contributions with the calibration coefficients.
        ce = beta1 * sigma_max_d + beta2 * sigma_min_d



    if I1_correction==1:
        ce = ce + z*(1-sqrt(I1_d**2)/I1_d)*psi11  

    
    # Compute first variation of Pi (directional derivative about u in the direction of v)
    R = derivative(Pi, u, v)

    # Compute Jacobian of R
    Jac = derivative(R, u, du)

    #To use later for memory allocation for these tensors
    A=PETScMatrix()
    b=PETScVector()

    #Balance of configurational forces PDE
    if stress_state_choice in [1,2,3]: #Plane stress, Plane strain, 3D
        Wv=pen/2*((abs(z)-z)**2 + (abs(1-z) - (1-z))**2 )*dx
        Wv2=conditional(le(z, 0.25), 1, 0)*z_penalty_factor*pen/2*( 1/4*( abs(z_prev-z)-(z_prev-z) )**2 )*dx
        R_z = y*2*z*(psi11)*dx - y*(ce)*dx + 3*delta*Gc/8*(y*(-1)/eps + 2*eps*inner(grad(z),grad(y)))*dx + derivative(Wv,z,y) +  derivative(Wv2,z,y)   # Complete Model
    
    elif stress_state_choice == 4: #Axisymmetric
        Wv=pen/2*((abs(z)-z)**2 + (abs(1-z) - (1-z))**2 )*2*np.pi*xm[0]*dx
        R_z = y*2*z*(psi11)*2*np.pi*xm[0]*dx - y*(ce)*2*np.pi*xm[0]*dx + 3*delta*Gc/8*(y*(-1)/eps + 2*eps*inner(grad(z),grad(y)))*2*np.pi*xm[0]*dx + derivative(Wv,z,y) # +  derivative(Wv2,z,y)

    # Compute Jacobian of R_z
    Jac_z = derivative(R_z, z, dz)


# -----------------------------------------------------------------------------
# 2. Phase field Cohesive Zone Model 
# -----------------------------------------------------------------------------

elif phase_model == 2:

    pen = 1000 * Gc / eps
    
    pho_c = scs / sts
    a1 = 4 * E * Gc / (pi * eps * sts**2)
    a2, a3 = -0.5, 0.0
    
    w_z = z**2 / (z**2 + a1 * (1 - z) * (1 + a2 * (1 - z) * (1 + a3 * (1 - z))))
    stress = (w_z + eta) * sigma(u)
    
    J2 = sigmavm(sigma(u), u)**2
    
    # Condition to choose between von Mises and Rankine criterion
    if vonMises_or_Rankine == 1:
        # von Mises criterion (Wu 2020)
        sigma_eq = (1 / (2 * pho_c)) * ((pho_c - 1) * tr(sigma(u)) + sqrt((pho_c - 1) ** 2 * (tr(sigma(u))) ** 2 + 12 * pho_c * J2))
        folder_prefix += '_vonMises'
    elif vonMises_or_Rankine == 2:
        # Rankine criterion
        # dim = sigma(u).ufl_shape[0]
        if stress_state_choice == 1:                                                                                     # Plain Stress
            # For a 2D problem: compute the two eigenvalues and take the largest.
            eig1_val, _ = compute_eigenvalues(sigma(u), problem_dim)
            sigma_eq = (eig1_val + abs(eig1_val)) / 2.0

        if stress_state_choice == 2:                                                                                # Plain Strain case
            # For a 2D problem: compute the two eigenvalues and take the largest.
            eig1_val, _ = compute_eigenvalues(sigma(u), problem_dim)
            eig3_val = nu * tr(sigma(u))
            eig_max = max(eig1_val, eig3_val)
            sigma_eq = (eig_max + abs(eig_max)) / 2.0

        elif stress_state_choice == 3:                                                                                   # 3D
            # For a 3D problem: compute the three eigenvalues and take the largest.
            eig1_val, eig2_val, eig3_val = compute_eigenvalues(sigma(u), problem_dim)
            sigma_eq = (eig1_val + abs(eig1_val)) / 2.0
        folder_prefix += '_Rankine'

    
    y_czm = sigma_eq**2 / (2 * E)
    Y_czm = -(a1 * z * (2 + 2 * a2 * (1 - z) - z)) / (z**2 + a1 * (1 - z) + a1 * a2 * (1 - z)**2)**2 * y_czm
    
    # Stored strain energy density
    psi1 = (w_z + eta) * energy(u)
    psi11 = energy(u)
    
     # Total potential energy
    if problem_type == 1 or 3 or 4 or 7:
        Pi = psi1*dx

    if problem_type == 2:
        Pi = psi1*dx - dot(Tf, u)*ds(1)

    elif problem_type == 5:
        Pi = psi1*dx - dot(Tf*n, u)*ds(1)

    elif problem_type == 6: 
        Pi = psi1*dx - (dot(-Tf*m, u)*ds(23) + dot(-Tf*m, u)*ds(24) + dot(Tf*m, u)*ds(21) + dot(Tf*m, u)*ds(22))
    
    # Compute first variation of Pi (directional derivative about u in the direction of v)
    R = derivative(Pi, u, v)
    
    # Compute Jacobian of R
    Jac = derivative(R, u, du)
    
    # Memory allocation for tensors
    A = PETScMatrix()
    b = PETScVector()
    
    # Balance of configurational forces PDE
    Wv = pen / 2 * ((abs(z) - z)**2 + (abs(1 - z) - (1 - z))**2) * dx
    Wv2 = conditional(le(z, 0.05), 1, 0) * z_penalty_factor * pen / 2 * (1 / 4 * (abs(z_prev - z) - (z_prev - z))**2) * dx
    R_z = -Y_czm * y * dx + (1 / (1 + h / (pi * eps))) * Gc / pi * (y * (-2 * z) / eps + 2 * eps * inner(grad(z), grad(y))) * dx + derivative(Wv, z, y) + derivative(Wv2, z, y)
    
    # Compute Jacobian of R_z
    Jac_z = derivative(R_z, z, dz)

# ---------------------------------------------------------------------------------------------------------------------------------------------
# 3. Classical Variational Models (Volumetric-deviatoric, Star-Convex, Spectral splits)   
# ---------------------------------------------------------------------------------------------------------------------------------------------
elif phase_model == 3:
    # Set the variational model and update folder_prefix and gamma accordingly
    if variational_model == 1:
        folder_prefix += '_StarConvex'
        gamma = (3 * (sts / scs)**2 - 2 * (nu + 1)) / (2 * nu - 1)  # Star Convex model
    elif variational_model == 2:
        folder_prefix += '_VolDev'
        gamma = 0.0  # Vol-Dev model
    elif variational_model == 3:
        folder_prefix += '_Spec_Split'
    else:
        raise ValueError("Invalid variational_model choice. Choose 1 (StarConvex), 2 (VolDev) or 3 (Spec_Split).")


    # For models 1 and 2, use the same energy split functions (with gamma)
    if variational_model in [1, 2]: #Volumetric-deviatoric and star convex models. 1 for Plane stress, 2 for plan strain and 3D. gamma=0 for volumetric-deviatoric
        def energy_pos(v):
            strain = epsilon(v)
            strain_dev = epsilon_dev(v)
            # For plain stress use a modified trace; for plane strain and 3D use the standard trace.
            trstrain = tr(strain) * (1 - 2 * nu) / (1 - nu) if stress_state_choice == 1 else tr(strain)
            tr_eps_plus = 0.5 * (trstrain + abs(trstrain))
            tr_eps_neg  = 0.5 * (trstrain - abs(trstrain))
            # Use different contributions for plain stress versus plane strain/3D
            if stress_state_choice == 1:  # Plane Stress
                energy_density = 0.5 * kappa * (tr_eps_plus)**2 + mu * (inner(strain_dev, strain_dev) + ((1+nu)/(3*(nu-1))*tr(strain))**2) - gamma * 0.5 * kappa * (tr_eps_neg)**2
            elif stress_state_choice ==2:   # Plane Strain
                energy_density = 0.5*kappa*(tr_eps_plus)**2 + mu*(inner(strain_dev,strain_dev) + 1/9 * trstrain**2)-gamma*0.5*kappa*(tr_eps_neg)**2
            else:  # 3D
                energy_density = 0.5*kappa*(tr_eps_plus)**2 + mu*(inner(strain_dev,strain_dev))-gamma*0.5*kappa*(tr_eps_neg)**2

            return energy_density

        def energy_neg(v):
            strain = epsilon(v)
            trstrain = tr(strain) * (1 - 2 * nu) / (1 - nu) if stress_state_choice == 1 else tr(strain)
            tr_eps_neg = 0.5 * (trstrain - abs(trstrain))
            energy_density = (1 + gamma) * 0.5 * kappa * (tr_eps_neg)**2
            return energy_density

    elif variational_model == 3: #Spectral split
        
        # Helper functions for Spec_Split energy
        def spec_split_energy_pos(trstrain, eigenvals):
            tr_eps_plus = 0.5 * (trstrain + abs(trstrain))
            _sum = sum((0.5 * (eig + abs(eig)))**2 for eig in eigenvals)
            return 0.5 * lmbda * tr_eps_plus**2 + mu *_sum

        def spec_split_energy_neg(trstrain, eigenvals):
            tr_eps_neg = 0.5 * (trstrain - abs(trstrain))
            _sum = sum((0.5 * (eig - abs(eig)))**2 for eig in eigenvals)
            return 0.5 * lmbda * tr_eps_neg**2 + mu * _sum

        # Compute common strain quantities
        strain = epsilon(v)
        trstrain = tr(strain) * (1 - 2*nu)/(1-nu) if stress_state_choice == 1 else tr(strain)
        
        # Determine eigenvalues based on the stress state and problem dimension.
        # Here we assume that:
        #   - For plain stress (stress_state_choice==1): we use a 2D eigenvalue calculation and take the out‐of‐plane component from strain[2,2].
        #   - For plain strain (stress_state_choice==2): we use the 2D eigenvalue calculation.
        #   - Otherwise (3D case): we use the 3D eigenvalue calculation.
        if stress_state_choice == 1:
            eig1_val, eig2_val = compute_eigenvalues(strain, problem_dim)
            eig3_val = -nu/E * tr(sigma(u))                                    # Out-of-plane stress component
            eigenvals = [eig1_val, eig2_val, eig3_val]
        elif stress_state_choice == 2:
            eigenvals = list(compute_eigenvalues(strain, problem_dim))
        elif sigma(u).ufl_shape()[0] == 3:
            eigenvals = list(compute_eigenvalues(strain, problem_dim))
        else:
            raise ValueError("Dimension not supported. dim must be 2 or 3.")
        
        def energy_pos(v):
            return spec_split_energy_pos(trstrain, eigenvals)

        def energy_neg(v):
            return spec_split_energy_neg(trstrain, eigenvals)

    else:
        raise ValueError("Invalid variational model selected.")

    pen = 1000 * Gc / eps

    psi1 = (z ** 2 + eta) * energy_pos(u) + energy_neg(u)
    psi11 = energy_pos(u)
    stress = (z ** 2 + eta) * sigma(u)

    # Total potential energy
    if problem_type == 1 or 3 or 4 or 7:
        Pi = psi1*dx

    if problem_type == 2:
        Pi = psi1*dx - dot(Tf, u)*ds(1)

    elif problem_type == 5:
        Pi = psi1*dx - dot(Tf*n, u)*ds(1)

    elif problem_type == 6: 
        Pi = psi1*dx - (dot(-Tf*m, u)*ds(23) + dot(-Tf*m, u)*ds(24) + dot(Tf*m, u)*ds(21) + dot(Tf*m, u)*ds(22))

    elif problem_type == 8:
        Pi = psi1*2*np.pi*x[0]*dx

    R = derivative(Pi, u, v)
    Jac = derivative(R, u, du)

    # Balance of configurational forces PDE
    Wv = pen / 2 * ((abs(z) - z) ** 2 + (abs(1 - z) - (1 - z)) ** 2) * dx
    Wv2 = z_penalty_factor * pen / 2 * (1 / 4 * (abs(z_prev - z) - (z_prev - z)) ** 2) * dx

    R_z = y * 2 * z * psi11 * dx + (1 / (1 + 3 * h / (8 * eps))) * 3 * Gc / 8 * (y * (-1) / eps + 2 * eps * inner(grad(z), grad(y))) * dx \
          + derivative(Wv, z, y) + derivative(Wv2, z, y)

    Jac_z = derivative(R_z, z, dz)

    # Allocate PETSc matrices/vectors for later use
    A = PETScMatrix()
    b = PETScVector()

# ---------------------------------------------------------------------------------------------------------------------------------------------
# 4. Miehe model with stress-based driving force
# ---------------------------------------------------------------------------------------------------------------------------------------------

elif phase_model == 4:
    pen = 1000 * Gc / eps
    stress = (z**2 + eta) * sigma(u)
    psi_c = sts**2 / (2 * E)
    
    # Determine the dimension of the stress tensor σ(u)
    # dim = sigma(u).ufl_shape()[0]
    
    if stress_state_choice == 1:                                                                                                    # Plain Stress case
        # For a 2D problem: compute the two eigenvalues.
        eig1_val, eig2_val = compute_eigenvalues(sigma(u), problem_dim)
        eig1_ = (eig1_val + abs(eig1_val)) / 2.0
        eig2_ = (eig2_val + abs(eig2_val)) / 2.0
        # Compute D_d using the two eigenvalues
        D_d = 0.5 * ((((eig1_**2 + eig2_**2) / sts**2) - 1) + abs(((eig1_**2 + eig2_**2) / sts**2) - 1)) / 2.0

    if stress_state_choice == 2:                                                                                                    # Plain Strain case
        # For a 2D problem: compute the two eigenvalues.
        eig1_val, eig2_val = compute_eigenvalues(sigma(u), problem_dim)
        eig1_ = (eig1_val + abs(eig1_val)) / 2.0
        eig2_ = (eig2_val + abs(eig2_val)) / 2.0
        eig3_ = nu * tr(sigma(u))
        # Compute D_d using the three eigenvalues
        D_d = 0.5 * ((((eig1_**2 + eig2_**2 + eig3_**2) / sts**2) - 1) + abs(((eig1_**2 + eig2_**2 + eig3_**2) / sts**2) - 1)) / 2.0
        
    elif stress_state_choice == 3:                                                                                                   # 3D case
        # For a 3D problem: compute the three eigenvalues.
        eig1_val, eig2_val, eig3_val = compute_eigenvalues(sigma(u), problem_dim)
        eig1_ = (eig1_val + abs(eig1_val)) / 2.0
        eig2_ = (eig2_val + abs(eig2_val)) / 2.0
        eig3_ = (eig3_val + abs(eig3_val)) / 2.0
        # Compute D_d using the three eigenvalues.
        D_d = 0.5 * ((((eig1_**2 + eig2_**2 + eig3_**2) / sts**2) - 1) + abs(((eig1_**2 + eig2_**2 + eig3_**2) / sts**2) - 1)) / 2.0
    
    # Stored strain energy density
    psi1 = (z**2 + eta) * energy(u)
    psi11 = energy(u)
    
    # Total potential energy
    if problem_type == 1 or 3 or 4 or 7:
        Pi = psi1*dx

    if problem_type == 2:
        Pi = psi1*dx - dot(Tf, u)*ds(1)

    elif problem_type == 5:
        Pi = psi1*dx - dot(Tf*n, u)*ds(1)

    elif problem_type == 6: 
        Pi = psi1*dx - (dot(-Tf*m, u)*ds(23) + dot(-Tf*m, u)*ds(24) + dot(Tf*m, u)*ds(21) + dot(Tf*m, u)*ds(22))
    
    elif problem_type == 8:
        Pi = psi1*2*np.pi*x[0]*dx

    # Compute the first variation of Pi (directional derivative about u in the direction of v)
    R = derivative(Pi, u, v)
    
    # Compute the Jacobian of R
    Jac = derivative(R, u, du)
    
    # Allocate PETSc matrices/vectors for later use
    A = PETScMatrix()
    b = PETScVector()
    
    # Balance of configurational forces PDE
    Wv = pen/2 * (((abs(z) - z)**2) + ((abs(1 - z) - (1 - z))**2)) * dx
    Wv2 = conditional(le(z, 0.05), 1, 0) * z_penalty_factor * pen/2 * (1/4 * (abs(z_prev - z) - (z_prev - z))**2) * dx
    R_z = z * D_d * y * dx + (y * (z - 1) + eps**2 * inner(grad(z), grad(y))) * dx  # + derivative(Wv, z, y) + derivative(Wv2, z, y)
    
    # Compute the Jacobian of R_z
    Jac_z = derivative(R_z, z, dz)


# ___________________________________________________________________________________________________________________________________________________________


# Choose preconditioner based on problem type
if problem_dim == 3:
    precond = "petsc_amg"
else:
    precond = "amg"

# Set nonlinear solver parameters based on the solver choice
if non_linear_solver_choice == 1:
    snes_solver_parameters = {
        "nonlinear_solver": "snes",
        "snes_solver": {
            "linear_solver": "cg",
            "preconditioner": precond,
            "maximum_iterations": 10,
            "report": True,
            "error_on_nonconvergence": False
        }
    }
elif non_linear_solver_choice == 2:
    # Create a Krylov solver and set its parameters
    solver_u = KrylovSolver('cg', precond)
    max_iterations = 200
    solver_u.parameters["maximum_iterations"] = max_iterations
    solver_u.parameters["error_on_nonconvergence"] = False

    snes_solver_parameters = {
        "nonlinear_solver": "snes",
        "snes_solver": {
            "linear_solver": "cg",
            "preconditioner": precond,
            "maximum_iterations": 10,
            "absolute_tolerance": 1e-8,
            "report": True,
            "error_on_nonconvergence": False
        }
    }
elif non_linear_solver_choice == 3:
    snes_solver_parameters = {
        "nonlinear_solver": "snes",
        "snes_solver": {
            "linear_solver": "mumps",
            "maximum_iterations": 20,
            "report": True,
            "error_on_nonconvergence": False
        }
    }

# Set linear solver parameters if required
if linear_solver_for_u == 1:
    linear_solver_parameters = {"monitor_convergence": True}


#time-stepping parameters

if problem_type == 7: 
    stepsize=5e-3/v0_imp
    Totalsteps=int(1/stepsize)
    startstepsize=1/Totalsteps
    stepsize=startstepsize
    t=stepsize
    step=1
    rtol=1e-9

else: 
    startstepsize=1/Totalsteps
    stepsize=startstepsize
    t=stepsize
    step=1
    rtol=1e-9
    tau=0

# other time stepping parameters
samesizecount = 1
terminate = 0
stag_flag = 0
gfcount = 0
nrcount = 0
minstepsize = startstepsize/10000
maxstepsize = startstepsize

# Initial reference point (e.g., notch root)
crack_length_prev = 0


while t-stepsize < T:

    if comm_rank==0:
        print('Step= %d' %step, 't= %f' %t, 'Stepsize= %e' %stepsize)
        sys.stdout.flush()

    if problem_type == 1:                                                            # Surfing
        c.t=t; c0.t=t; r.t=t; r0.t=t; c0.tau=tau; r0.tau=tau; 

    elif problem_type in (2, 5):                                                     # Mode I, Biaxial
        c.t=t; Tf.t=t; 
    
    elif problem_type == 3:                                                          # Mode II
        c.t=t; 
    
    elif problem_type == 4:                                                          # Mode III
        r.t=t; r0.t=t; r0.tau=tau; 

    elif problem_type == 6:                                                          # Pure Shear
        Tf.t=t; 
    
    elif problem_type == 7:                                                          # 4-P Bending
        cl.t=t; 

        if t>0.5:
            stepsize = 5e-4 / v0_imp

    elif problem_type == 8:                                                          # Axisymmetric Indentation
        Tf.t=t; c.t=t; r.t=t; r0.t=t; r0.tau=tau

    elif problem_type == 9:                                                          # Mode I, Displacement BCs
        cp.t=t; cn.t=t

    elif problem_type == 10:                                                       # Compression Test, Section 3.5.4
        cn.t=t

    elif problem_type == 11:                                                   # Compression Test, Section 3.5.4
        cn.t=t; cn0.t=t; cn0.tau=tau

    stag_iter=1
    rnorm_stag=1
    zdiffnorm=1
    terminate = 0
    stag_flag = 0


    while stag_iter<stag_iter_max and zdiffnorm > 1e-10:                
        start_time=time.time()
        ##############################################################
        #First PDE
        ##############################################################        

        if linear_solver_for_u == 1:
            # Linear solver: solve the displacement equation using a Krylov method.
            a_u = inner(stress, epsilon(v)) * dx
            L_u = inner(Tf, v) * ds(1)
            Jac_u, Res_u = assemble_system(a_u, L_u, bcs)
            linearsolver = KrylovSolver("cg", precond)
            linearsolver.parameters.update(linear_solver_parameters)
            linearsolver.solve(Jac_u, u.vector(), Res_u)
            converged_u = True
        else:
            # Nonlinear solver branch
            if non_linear_solver_choice == 1 or non_linear_solver_choice == 3:
                # Use a full nonlinear solve with SNES.
                Problem_u = NonlinearVariationalProblem(R, u, bcs, J=Jac)
                solver_u = NonlinearVariationalSolver(Problem_u)
                solver_u.parameters.update(snes_solver_parameters)
                (iter, converged_u) = solver_u.solve()
                
            elif non_linear_solver_choice == 2:
                # Use an iterative (staggered) nonlinear approach.
                nIter = 0
                rnorm = 1e4  # Initialize residual norm high.
                while nIter < 10:
                    nIter += 1
                    if nIter == 1 and stag_iter == 1:
                        A, b = assemble_system(Jac, -R, bcs_du0)
                    else:
                        A, b = assemble_system(Jac, -R, bcs_du)
                    rnorm = b.norm('l2')
                    if comm_rank == 0:
                        print('Iteration number= %d, Residual= %e' % (nIter, rnorm))
                        sys.stdout.flush()
                    if rnorm < rtol:
                        break
                    converged = solver_u.solve(A, u_inc.vector(), b)
                    if comm_rank == 0:
                        print(converged)
                        sys.stdout.flush()
                    u.vector().axpy(1, u_inc.vector())
                converged_u = (rnorm < rtol)

        assign(z_trial,z)
		##############################################################
		#Second PDE
		##############################################################
        Problem_z = NonlinearVariationalProblem(R_z, z, bcs_z, J=Jac_z)
        solver_z  = NonlinearVariationalSolver(Problem_z)
        solver_z.parameters.update(snes_solver_parameters)
        (iter, converged) = solver_z.solve() 


        min_z = z.vector().min(); 
        zmin = MPI.min(comm, min_z)
        if comm_rank==0:
            print(zmin)
            sys.stdout.flush()
            
        if comm_rank==0:
            print("--- %s seconds ---" % (time.time() - start_time))
            sys.stdout.flush()


        ###############################################################
        #Residual check for stag loop
        ###############################################################
        b=assemble(-R, tensor=b)
        fint=b.copy() #assign(fint,b) 
        for bc in bcs_du:
            bc.apply(b)
        rnorm_stag=b.norm('l2')	

        zdiffnorm = norm(z.vector() - z_trial.vector())
        
        if comm_rank==0:
            print(f"Stag Iteration no={stag_iter}   Residual_u={rnorm_stag}   zdiffnorm={zdiffnorm}")

        stag_iter+=1 

        if zdiffnorm > 1e6:
            terminate = 1
            break
    
    if comm_rank==0:
            print(f"___________________________________________________________________")

    ######################################################################
    #Post-Processing
    ######################################################################
    if terminate == 1:
        assign(u, u_prev)
        assign(z, z_prev)
    else:
        assign(u_prev, u)
        assign(z_prev, z)


    # ———————————————————————————————————————————————————————————————————————————————————————————————————————
    # # ——— compute and report determinant of deformation gradient ———
    # # deformation gradient F = I + ∇u, then detF = det(F)
    # F_expr   = Identity(d) + grad(u)
    # detF_expr = det(F_expr)

    # total_detF = assemble(detF_expr*dx)
    # total_vol  = assemble(Constant(1.0)*dx)
    # avg_detF   = total_detF/total_vol
    # if comm_rank == 0:
    #     print(f"[Step= {step:3d}, t= {t:.4f}]  ⟨det F⟩ = {avg_detF:.6f}")
    # ———————————————————————————————————————————————————————————————————————————————————————————————————————


    # If maximum stag iterations reached, flag stag_flag and exit time stepping
    if stag_iter == stag_iter_max-1:
        stag_flag = 1
        break


    # ___________________________________________________________________________________________________________________________________________________________


    # Common post-processing steps
    def calculate_reaction(fint, y_dofs_top):
        return MPI.sum(comm, sum(fint[y_dofs_top]))

    def evaluate_z_at_point(z, point):
        return evaluate_function(z, point)

    def write_to_file(filename, data, mode='a'):
        with open(filename, mode) as rfile:
            rfile.write("{} {} {}\n".format(*data))

    def save_xdmf(ac, step, u, z, t):
        file_results = XDMFFile("Paraview_ac=" + str(ac) + "/SENT_" + str(step) + ".xdmf")
        file_results.parameters["flush_output"] = True
        file_results.parameters["functions_share_mesh"] = True
        u.rename("u", "displacement field")
        z.rename("z", "phase field")
        file_results.write(u, t)
        file_results.write(z, t)

        # now project det(F) to a CG1 nodal space and write it
        # V_det  = FunctionSpace(mesh, "CG", 1)
        V_det = FunctionSpace(mesh, "DG", 0)
        detF_e = det(Identity(d) + grad(u))
        detF   = local_project(detF_e, V_det)
        detF.rename("detF", "det F")
        file_results.write(detF, t)

        file_results.close()


    # Post-processing based on problem_type
    if problem_type == 1:                                                                      # Surfing problem
        Fx = calculate_reaction(fint, y_dofs_top)
        JI1 = (psi1 * n[0] - dot(dot(stress, n), u.dx(0))) * ds(24)
        JI2 = (-dot(dot(stress, n), u.dx(0))) * ds(21)
        Jintegral = 2*(assemble(JI1)+assemble(JI2))

        if comm_rank == 0:
            write_to_file('Surfing_ce.txt', [t, Jintegral])

        if step % paraview_at_step == 0:
            save_xdmf("FullModel/Surfing_ce", step, u, z, t)

    elif problem_type == 2:                                                                    # Mode I
        Fx = calculate_reaction(fint, y_dofs_top)
        z_x = evaluate_z_at_point(z, (ac + eps, 0.0))

        if comm_rank == 0:
            print(Fx)
            print(z_x)
            write_to_file('Alumina_SENT_AT2.txt', [t, zmin, z_x])

        if step % paraview_at_step == 0:
            save_xdmf(ac, step, u, z, t)

        if z_x < z_crit:
            t1 = t
            break

        if t > 0.997:
            t1 = 1

    elif problem_type == 3:                                                                    # Mode II
        Fx = calculate_reaction(fint, y_dofs_top)
        z_x = evaluate_z_at_point(z, (0.9 + eps, -0.5))        # 23, -12.5 are inputs, define as var

        traction = dot(sigma(u), n) 
        traction_top_x = assemble(traction[0]*ds(21))

        if comm_rank == 0:
            print(Fx)
            print(z_x)
            write_to_file('SENT_Shear.txt', [t, zmin, z_x])
            write_to_file('F_int.txt', [t, Fx])
            write_to_file('F_sig_dot_n.txt', [t, traction_top_x])

        if step % paraview_at_step == 0:
            save_xdmf("Paraview/SENT", step, u, z, t)

        # if z_x < z_crit:
        #     break

    elif problem_type == 4:                                                                    # Mode III
        Fx = calculate_reaction(fint, y_dofs_top)

        if comm_rank == 0:
            printdata = [t, t * v0_imp, Fx]
            with open('Results.csv', 'a', newline='') as csvfile:
                csvwriter = csv.writer(csvfile, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
                csvwriter.writerow(printdata)

        if step % paraview_at_step == 0:
            save_xdmf("Paraview/4P", step, u, z, t)

    elif problem_type == 5:                                                                    # Biaxial
        Fx = calculate_reaction(fint, y_dofs_top)
        z_x = evaluate_z_at_point(z, (ac + eps, 0.0))

        if comm_rank == 0:
            print(Fx)
            print(z_x)
            write_to_file('Graphite_Biaxial.txt', [t, zmin, z_x])

        if step % paraview_at_step == 0:
            save_xdmf(f"Paraview_ac={2 * ac}/SENT", u, z, t, step)

        # if z_x < z_crit:
        #     t1 = t
        #     break

        if t > 0.997:
            t1 = 1

    elif problem_type == 6:                                                                    # Pure Shear
        Fx = calculate_reaction(fint, y_dofs_top)
        z_x = [evaluate_z_at_point(z, (ac + 2 * eps * np.cos(angle), 2 * eps * np.sin(angle))) for angle in np.linspace(5 / 4 * np.pi, 2 * np.pi, 100)]

        if comm_rank == 0:
            print(Fx)
            print(z_x)
            write_to_file('SENT_Shear.txt', [t, zmin, min(z_x)])
            write_to_file('Traction.txt', [t, Fx])

        if step % paraview_at_step == 0:
            save_xdmf("Paraview/4P", step, u, z, t)

        # if min(z_x) < z_crit:
        #     t1 = t
        #     break

        if t > 0.997:
            t1 = 1

    elif problem_type == 7:                                                                    # 4-P Bending
        Fx_Rleft = calculate_reaction(fint, y_dofs_Rleft)
        Fx_Rright = calculate_reaction(fint, y_dofs_Rright)
        Fx_Pleft = calculate_reaction(fint, y_dofs_Pleft)
        Fx_Pright = calculate_reaction(fint, y_dofs_Pright)

        z_x = evaluate_z_at_point(z, (0.0, 7.0, 0.0))

        if comm_rank == 0:
            print(Fx_Rleft)
            print(Fx_Rright)
            print(Fx_Pleft)
            print(Fx_Pright)
            print(z_x)
            write_to_file('Graphite_Biaxial.txt', [t, zmin, z_x])
            write_to_file('Traction.txt', [t, Fx_Rleft, Fx_Rright, Fx_Pleft, Fx_Pright])

        if step % paraview_at_step == 0:
            save_xdmf("Paraview/4P", step, u, z, t)

    elif problem_type == 8:  # Indentation problem
        Fx = calculate_reaction(fint, y_dofs_top)
        if comm_rank == 0:
            print(Fx)
            with open('Indent.txt', 'a') as rfile:
                rfile.write("%s %s %s\n" % (str(t), str(Fx), str(zmin)))

        if step % paraview_at_step == 0:
            file_results = XDMFFile("a5/IndentAxia5_" + str(step) + ".xdmf")
            file_results.parameters["flush_output"] = True
            file_results.parameters["functions_share_mesh"] = True
            u.rename("u", "displacement field")
            z.rename("z", "phase field")
            file_results.write(u, t)
            file_results.write(z, t)

    elif problem_type == 9:                                                                    # Mode I, Displacement BCs
        Fy_top = calculate_reaction(fint, y_dofs_top)
        Fy_bot = calculate_reaction(fint, y_dofs_bot)
        z_x = evaluate_z_at_point(z, (ac + eps, 0.0))

        traction = dot(sigma(u), n)
        traction_top_y = assemble(traction[1]*ds(21))
        traction_bot_y = assemble(traction[1]*ds(22))

        if comm_rank == 0:
            write_to_file('Alumina_SENT_AT2.txt', [t, zmin, z_x])
            write_to_file('F_int.txt', [t, Fy_top, Fy_bot])
            write_to_file('F_sig_dot_n.txt', [t, traction_top_y, traction_bot_y])

        if step % paraview_at_step == 0:
            save_xdmf(ac, step, u, z, t)

    elif problem_type == 10:                                                                   # Compression Test, Section 3.5.4
        Fy_top = calculate_reaction(fint, y_dofs_top)
        Fy_bot = calculate_reaction(fint, y_dofs_bot)

        traction = dot(sigma(u), n)
        traction_top_y = assemble(traction[1]*ds(21))
        traction_bot_y = assemble(traction[1]*ds(22))

        if comm_rank == 0:
            write_to_file('F_int.txt', [t, Fy_top, Fy_bot])
            write_to_file('F_sig_dot_n.txt', [t, traction_top_y, traction_bot_y])

        if step % paraview_at_step == 0:
            save_xdmf(ac, step, u, z, t)


    elif problem_type == 11:                                                                   # Compression Test, Section 3.5.4
        Fy_top = calculate_reaction(fint, y_dofs_top)
        Fy_bot = calculate_reaction(fint, y_dofs_bot)

        if comm_rank == 0:
            write_to_file('F_int.txt', [t, Fy_top, Fy_bot])
        
        # only save in the time window 0.30 < t < 0.34
        if 0.30 < t < 0.34:
            # first condition: every step
            if step % 1 == 0:
                save_xdmf(ac, step, u, z, t)
            # second condition: every paraview_at_step
        elif step % paraview_at_step == 0:
            save_xdmf(ac, step, u, z, t)

    # ___________________________________________________________________________________________________________________________________________________________

    # ——————————————————————————————————————————————————————————————————————————————————————————————————
    # # --- Crack length and velocity calculation ---
    # # 1) Crack‐length indicator integral
    # integrand = (3.0/8.0)*((1.0 - z)/eps + eps*inner(grad(z), grad(z)))*dx
    # local_length = assemble(integrand)
    # # sum over subdomains/processes
    # crack_length = mesh.mpi_comm().allreduce(local_length, op=MPI.SUM)

    # # 2) Crack‐tip location via damaged DOFs
    # # Reference point for distance measurement
    # ref_pt = np.array([10.0, 0.0])  # change as needed

    # # Get global DOF coordinates and local z‐values
    # dof_coords = Y.tabulate_dof_coordinates().reshape((-1, mesh.geometry().dim()))
    # z_vals     = z.vector().get_local()

    # # Mask DOFs where z ≤ 0.01 (damaged)
    # idx = np.where(z_vals <= 0.01)[0]
    # if idx.size > 0:
    #     pts = dof_coords[idx]
    #     dists = np.linalg.norm(pts - ref_pt, axis=1)
    #     local_tip = dists.max()
    # else:
    #     local_tip = 0.0

    # # global maximum tip distance across MPI ranks
    # crack_tip = MPI.max(mesh.mpi_comm(), local_tip)

    # # 3) Velocity
    # if step == 1:
    #     crack_velocity = crack_tip / t
    # else:
    #     dt = stepsize
    #     crack_velocity = (crack_tip - crack_length_prev) / dt if dt > 0.0 else 0.0

    # crack_length_prev = crack_tip

    # # 4) Log to file from rank 0
    # if comm_rank == 0:
    #     write_to_file('CrackVelocity.txt', [t, crack_tip, crack_velocity])
    # ——————————————————————————————————————————————————————————————————————————————————————————————————
    
    # Time-stepping update (combined)
    ######################################################################
    if terminate:
        # If termination flagged, reduce the time step if possible
        if stepsize > minstepsize:
            t = t - stepsize
            stepsize /= 2
            t = t + stepsize
            samesizecount = 1
        else:
            break
    else:
        # If no termination, either repeat the same step or increase the step size
        if samesizecount < 2:
            step += 1
            if t + stepsize <= T:
                samesizecount += 1
                tau = t
                t += stepsize
            else:
                samesizecount = 1
                stepsize = T - t
                tau = t
                t += stepsize
        else:
            step += 1
            if stepsize * 2 <= maxstepsize and t + stepsize * 2 <= T:
                stepsize *= 2
                tau = t
                t += stepsize
            elif stepsize * 2 > maxstepsize and t + maxstepsize <= T:
                stepsize = maxstepsize
                tau = t
                t += stepsize
            else:
                stepsize = T - t
                tau = t
                t += stepsize
            samesizecount = 1


    # if stag_flag:
    #     # If termination flagged, reduce the time step for the next update.
    #     if stepsize > minstepsize:
    #         stepsize /= 2
    #         samesizecount = 1
    #         t += stepsize
    #     else:
    #         break
    # else:
    #     # If no termination, either repeat the same step or increase the step size.
    #     if samesizecount < 2:
    #         step += 1
    #         if t + stepsize <= T:
    #             samesizecount += 1
    #             t += stepsize
    #         else:
    #             samesizecount = 1
    #             stepsize = T - t
    #             t += stepsize
    #     else:
    #         step += 1
    #         if stepsize * 2 <= maxstepsize and t + stepsize * 2 <= T:
    #             stepsize *= 2
    #             t += stepsize
    #         elif stepsize * 2 > maxstepsize and t + maxstepsize <= T:
    #             stepsize = maxstepsize
    #             t += stepsize
    #         else:
    #             stepsize = T - t
    #             t += stepsize
    #         samesizecount = 1      
            
            


    

def write_and_print_critical_stress(sigma_critical, notch_length, filename='Critical_stress.txt'):
    if comm_rank == 0:
        with open(filename, 'a') as rfile:
            rfile.write(f'Critical stress = {sigma_critical:.4f} (MPa), at Notch Length = {notch_length:.2f} mm\n')
        print(f'Critical stress = {sigma_critical:.4f} (MPa), at Notch Length = {notch_length:.2f} mm')

# Common variables
# sigma_critical = t1 * sigma_external

# Condition-specific code
if problem_type == 2:                                                     # Mode I
    write_and_print_critical_stress(sigma_critical, ac)

elif problem_type == 5:                                                   # Biaxial
    write_and_print_critical_stress(sigma_critical, 2 * ac)

elif problem_type == 6:                                                   # Pure Shear
    write_and_print_critical_stress(sigma_critical, 2 * ac)


#######################################################end of all loops
if comm_rank==0:	
	print("--- %s seconds ---" % (time.time() - start_time))


if comm_rank == 0: 
    endTime = datetime.now()
    elapseTime = endTime - startTime
    print("------------------------------------")
    print("Elapsed real time:  {}".format(elapseTime))
    print("------------------------------------")
