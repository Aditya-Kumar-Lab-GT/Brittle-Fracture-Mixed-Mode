Mesh.MshFileVersion = 2.0;
// This code was created by pygmsh v0.7.5.
SetFactory("OpenCASCADE");

// ------------------------------
// Geometry: Define Points
// ------------------------------
W=30;
L=10;
h=5;

Point(1) = {0.0, L/2,  0.0, h};
Point(2) = {W, L/2,  0, h};
Point(3) = {W, -L/2, 0, h};
Point(4) = {0.0, -L/2, 0, h};
Point(5) = {0.0, 0.00, 0, h};
Point(6) = {L/2, 0.00, 0, h};

// ------------------------------
// Geometry: Define Outer Boundary and Surface
// ------------------------------
Line(7) = {1, 2};
Line(8) = {2, 3};
Line(9) = {3, 4};
Line(10) = {4, 5};
Line(11) = {5, 1};
Line Loop(12) = {7, 8, 9, 10, 11};
Plane Surface(13) = {12};
Physical Surface(14) = {13};

// ------------------------------
// Geometry: Define Internal Crack
// ------------------------------
Line(15) = {5, 6};
Curve{15} In Surface{13};
Physical Curve(16) = {15};
Physical Point(17) = {5};

// ------------------------------
// Mark Boundary Subdomains (Physical Lines)
// ------------------------------
Physical Point("rightTop", 20) = {2};    	// RighTop boundary point (x, y = W, L/2)
Physical Curve("top", 21)    = {7};    	// Top boundary (y = L/2)
Physical Curve("bottom", 22) = {9};    	// Bottom boundary (y = -L/2)
Physical Curve("left", 23)   = {10,11};   	// Left boundary (x = 0)
Physical Curve("right", 24)  = {8};   	// Right boundary (x = W)
Physical Curve("crack", 25)  = {15};   	// Crack (y = 0)

// ------------------------------
// Mesh Refinement Field
// ------------------------------
Field[1] = Box;
Field[1].VIn = 0.035;
Field[1].VOut = 0.5;
Field[1].XMin = 0;
Field[1].XMax = 30;
Field[1].YMin = -1.0;
Field[1].YMax = 1;
Field[1].ZMin = 0.0;
Field[1].ZMax = 0.0;
Field[1].Thickness = 1;
Field[6] = Min;
Field[6].FieldsList = {1};
Background Field = 6;

// ------------------------------
// Mesh Settings
// ------------------------------
Mesh.ElementOrder = 1;
Mesh 2;

// ------------------------------
// Crack Plugin Settings
// ------------------------------
Plugin(Crack).Dimension = 1;
Plugin(Crack).PhysicalGroup = 16;
Plugin(Crack).OpenBoundaryPhysicalGroup = 17;
Plugin(Crack).Run;

// ------------------------------
// Save Mesh
// ------------------------------
Save "meshmark.msh";
