# Innoslate screenshots for the Chapter 8 + 9 report

Save the screenshots here under these names, then run `python docs/ch8-ch9/build/build_report.py`.
A file that exists replaces the figure rendered from the model data; a missing file leaves the rendered figure.

| File | Content | Need |
|---|---|---|
| idef0_first.png | First-level IDEF0 of F.2 with the eight mechanisms C.0.0-C.0.7 | required |
| idef0_second.png | Second-level IDEF0 of F.2.2 with mechanisms C.0.2.1-C.0.2.4 | required |
| hier_overall.png | Asset hierarchy from the Universe down to C.0.2.x | required |
| hier_universe.png | Universe with C.0 and X.1-X.7 | required |
| hier_c0.png | C.0 with C.0.0-C.0.7 | required |
| hier_c02.png | C.0.2 with C.0.2.1-C.0.2.4 | required |
| asset_context.png | Context asset diagram (generated from the Metafunction IDEF0) | required |
| asset_first.png | First-level asset diagram (generated from the first-level IDEF0) | required |
| i2_first.png | I2 diagram, first level | required |
| i2_second.png | I2 diagram, C.0.2 | recommended |
| n2_second.png | N2 diagram of F.2.2.1-F.2.2.4 | recommended |
| spider_c02.png | Spider diagram of C.0.2 | required |
| metafunction_idef0.png | Metafunction IDEF0 (open F.2 > Open > Parent Diagram) with no `( )` tunnel marks; see the note below | required if the old one shows `( )` |

Tunnel check: the lab manual (Figure 7-1, ATM case study) shows a finished Metafunction with the Universe asset at the bottom joined to every mechanism and no `( )` marks. If the Metafunction of the project still shows `( )` at the foot of the mechanism arrows, relate F.0 to the Universe asset (F.0 > Entity View > Relationships > performed by > Relate Existing Entities > 0 Universe), reopen the diagram and retake the screenshot.
