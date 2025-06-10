Mesh.MshFileVersion = 2.0;
// This code was created by pygmsh v0.7.5.
SetFactory("OpenCASCADE");
// Mesh.CharacteristicLengthMin = 1.0;
// Mesh.CharacteristicLengthMax = 1.0;

Point(2) = {0.0, 300*Sqrt(2),  0, 2};
Point(3) = {300*Sqrt(2), 0, 0, 2};
Point(5) = {0.0, 0.0, 0, 2};
//+

Line(8) = {2, 3};
Line(9) = {3, 5};
Line(11) = {5, 2};
Line Loop(12) = {8, 9, 11};
Plane Surface(13) = {12};
Physical Surface(14) = {13};
//+

Field[1] = Box;
Field[1].VIn = 0.005;
Field[1].VOut = 3;
Field[1].XMin = 0;
Field[1].XMax = 2.0;
Field[1].YMin = 0.0;
Field[1].YMax = 1.0;
Field[1].Thickness = 2;
//+

Field[6] = Min;
Field[6].FieldsList = {1};
Background Field = 6;
//+
Mesh.ElementOrder = 1;
Mesh 2;

//+
Save "crack.msh";

