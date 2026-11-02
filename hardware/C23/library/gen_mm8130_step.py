# Usage (Windows, Git Bash): MM8130_OUT=3d_models/Murata_MM8130-2600.step "/c/Program Files/FreeCAD 1.0/bin/FreeCAD.exe" gen_mm8130_step.py
# The GUI build is needed so ImportGui exports the colours. The window closes by itself.
# Murata MM8130-2600 (SWF) switch receptacle, from spec NMM04-PW0001E rev E and the DigiKey photo.
# Female: gold shell (top plate, 4 corner legs, ring dia. 2.1), black insulator with a funnel to the
# dia. 0.6 centre opening, black body below the plate, gold signal tabs on the two pad sides (+-y).
# Total height 1.4, ring height 0.8. Run with FreeCAD's GUI python so the colours are exported.
import os
import FreeCAD as App
import FreeCADGui as Gui
import Part
import ImportGui

OUT = os.environ['MM8130_OUT']
V = App.Vector
doc = App.newDocument('MM8130')

H, RING_H, PLATE_T, LEG_T = 1.4, 0.8, 0.12, 0.12
z_plate = H - RING_H - PLATE_T           # plate bottom (0.48)
z_ring = H - RING_H                      # plate top / ring bottom (0.6)

# black plastic body under the plate
body = Part.makeBox(2.3, 2.3, z_plate, V(-1.15, -1.15, 0))

# gold shell: plate + ring + 4 corner legs with feet on the ground pads
plate = Part.makeBox(2.5, 2.5, PLATE_T, V(-1.25, -1.25, z_plate))
ring = Part.makeCylinder(1.05, RING_H, V(0, 0, z_ring)).cut(Part.makeCylinder(0.92, RING_H, V(0, 0, z_ring)))
shell = plate.fuse(ring)
for sx in (-1, 1):
	for sy in (-1, 1):
		x0 = 0.65 if sx > 0 else -1.25
		leg = Part.makeBox(0.6, LEG_T, z_plate, V(x0, sy * 1.25 - (LEG_T if sy > 0 else 0), 0))
		foot = Part.makeBox(0.6, 0.35, 0.1, V(x0, (0.9 if sy > 0 else -1.25), 0))
		shell = shell.fuse(leg).fuse(foot)
shell = shell.removeSplitter()

# black insulator inside the ring: funnel down to the dia. 0.6 opening
ins_top = H - 0.15
ins = Part.makeCylinder(0.92, ins_top - z_ring, V(0, 0, z_ring))
funnel = Part.makeCone(0.3, 0.75, 0.35, V(0, 0, ins_top - 0.35))
hole = Part.makeCylinder(0.3, ins_top - z_ring, V(0, 0, z_ring))
ins = ins.cut(funnel).cut(hole).removeSplitter()

# gold signal tabs in the middle of the +-y sides (pads 1 and 2), and the contact inside the opening
tabs = []
for sy in (-1, 1):
	tabs.append(Part.makeBox(0.4, 0.35, 0.1, V(-0.2, (0.95 if sy > 0 else -1.3), 0)))
contact = Part.makeCylinder(0.22, 0.12, V(0, 0, z_ring))
gold = Part.makeCompound(tabs + [contact])

GOLD = (0.86, 0.70, 0.30)
BLACK = (0.08, 0.08, 0.08)
objs = []
for name, shape, col in (('Shell', shell, GOLD), ('Body', body, BLACK), ('Insulator', ins, BLACK), ('Contacts', gold, GOLD)):
	o = doc.addObject('Part::Feature', name)
	o.Shape = shape
	objs.append((o, col))
doc.recompute()
for o, col in objs:
	o.ViewObject.ShapeColor = col
ImportGui.export([o for o, _ in objs], OUT)
print('wrote', OUT)
App.closeDocument(doc.Name)
Gui.getMainWindow().close()
os._exit(0)
