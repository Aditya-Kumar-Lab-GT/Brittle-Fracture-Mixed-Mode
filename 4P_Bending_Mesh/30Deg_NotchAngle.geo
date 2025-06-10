SetFactory("OpenCASCADE");
Mesh.MeshSizeMin = 1e-8;
Lx = 80;
Ly = 20;
Lz = 10;


// Define the points for the cuboid
Point(1) = {-Lx/2, 0, Lz/2, 1.6};     
Point(2) = {-Lx/2, 0, -Lz/2, 1.6};    
Point(3) = {-Lx/2, Ly, -Lz/2, 1.6};   
Point(4) = {-Lx/2, Ly, Lz/2, 1.6};     
Point(5) = {Lx/2, 0, Lz/2, 1.6};     
Point(6) = {Lx/2, 0, -Lz/2, 1.6};    
Point(7) = {Lx/2, Ly, -Lz/2, 1.6};   
Point(8) = {Lx/2, Ly, Lz/2, 1.6};   
Point(9) = {(5/Sqrt(3)-1), 0, 5, 1.6};     
Point(10) = {(5/Sqrt(3)+1), 0, 5, 1.6};    
Point(11) = {(5/Sqrt(3)-1), 3.58578643763, 5, 1.6};  
Point(12) = {(5/Sqrt(3)+1), 3.58578643763, 5, 1.6};  
Point(13) = {-(5/Sqrt(3)+1), 0, -5, 1.6};     
Point(14) = {-(5/Sqrt(3)-1), 0, -5, 1.6};    
Point(15) = {-(5/Sqrt(3)+1), 3.58578643763, -5, 1.6};  
Point(16) = {-(5/Sqrt(3)-1), 3.58578643763, -5, 1.6};
Point(17) = {(5/Sqrt(3)), 6, 5, 1.6};    
Point(18) = {-(5/Sqrt(3)), 6, -5, 1.6};   

// Define lines for the cuboid
Line(1) = {1, 2};
Line(2) = {2, 3};
Line(3) = {3, 4};
Line(4) = {4, 1};
Line(5) = {5, 6};
Line(6) = {6, 7};
Line(7) = {7, 8};
Line(8) = {8, 5};
Line(9) = {4, 8};
Line(10) = {3, 7};
Line(11) = {1, 9};
Line(12) = {10, 5};
Line(13) = {2, 13};
Line(14) = {14, 6};
Line(15) = {9, 13};
Line(16) = {10, 14};
Line(17) = {11, 15};
Line(18) = {12, 16};
Line(19) = {17, 18};
Line(20) = {9, 11};
Line(21) = {10, 12};
Line(22) = {11, 17};
Line(23) = {12, 17};
Line(24) = {13, 15};
Line(25) = {14, 16};
Line(26) = {15, 18};
Line(27) = {16, 18};

// Define surfaces for the cuboid
Line Loop(1) = {1, 2, 3, 4};
Plane Surface(1) = {1};
Line Loop(2) = {5, 6, 7, 8};
Plane Surface(2) = {2};
Line Loop(3) = {1, 13,-15,-11};
Plane Surface(3) = {3};
Line Loop(4) = {16, 14, -5, -12};
Plane Surface(4) = {4};
Line Loop(5) = {-3, 10, 7, -9};
Plane Surface(5) = {5};
Line Loop(12) = {15, 24, -17, -20};
Plane Surface(12) = {12};
Line Loop(13) = {17, 26, -19, -22};
Plane Surface(13) = {13};
Line Loop(8) = {19, -27, -18, 23};
Plane Surface(8) = {8};
Line Loop(9) = {18, -25, -16, 21};
Plane Surface(9) = {9};
Line Loop(10) = {-4, 9, 8, -12, 21, 23, -22, -20, -11};
Plane Surface(10) = {10};
Line Loop(11) = {13, 24, 26, -27, -25, 14, -6, -10, -2};
Plane Surface(11) = {11};

// Define volume for the cuboid
Surface Loop(1) = {1, 2, 3, 4, 5, 8, 9, 10, 11, 12, 13};
Volume(1) = {1};

//+
Field[1] = Box;
Field[1].VIn = 1.6;
Field[1].VOut = 1.6;
Field[1].XMin = -6;
Field[1].XMax = 6;
Field[1].YMin = 5.5;
Field[1].YMax = 8;
Field[1].ZMin = -Lz/2;
Field[1].ZMax = Lz/2;
Field[1].Thickness = 5;
//+
Field[2] = Box;
Field[2].Thickness = 5;
Field[2].VIn = 0.1;
Field[2].VOut = 1.6;
Field[2].XMin = -36.125;
Field[2].XMax = -35.875;
Field[2].YMin = 0;
Field[2].YMax = 0.5;
Field[2].ZMin = -Lz/2;
Field[2].ZMax = Lz/2;
//+
Field[3] = Box;
Field[3].Thickness = 5;
Field[3].VIn = 0.1;
Field[3].VOut = 1.6;
Field[3].XMin = 35.875;
Field[3].XMax = 36.125;
Field[3].YMin = 0.0;
Field[3].YMax = 0.5;
Field[3].ZMin = -Lz/2;
Field[3].ZMax = Lz/2;
//+
Field[4] = Box;
Field[4].Thickness = 5;
Field[4].VIn = 0.1;
Field[4].VOut = 1.6;
Field[4].XMin = -20.25;
Field[4].XMax = -20;
Field[4].YMin = 19.5;
Field[4].YMax = 20.0;
Field[4].ZMin = -Lz/2;
Field[4].ZMax = Lz/2;
//+
Field[5] = Box;
Field[5].Thickness = 5;
Field[5].VIn = 0.1;
Field[5].VOut = 1.6;
Field[5].XMin = 20;
Field[5].XMax = 20.25;
Field[5].YMin = 19.5;
Field[5].YMax = 20.0;
Field[5].ZMin = -Lz/2;
Field[5].ZMax = Lz/2;
//+
Field[6] = Min;
Field[6].FieldsList = {1,2,3,4,5};
Background Field = 6;

// Mesh the structure
Mesh.ElementOrder = 1;
Mesh 3;

Mesh.MshFileVersion = 2.0;
Save "crack.msh";