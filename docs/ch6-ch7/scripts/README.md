# Build scripts

Run from this folder with Python 3.12, `lxml`, `matplotlib`, `pillow` and `python-docx`:

```
python figs3.py        # sequence diagram (the one figure drawn outside Innoslate)
python build_report.py # writes ../EcoCommute_Team6_Ch6-Ch7_Architecture_Definition_Function.docx
```

`mdata.py` holds the first-level function architecture and checks it against an Innoslate export (`python mdata.py <export.xml>`). The Innoslate screenshots in `../diagrams/` are inputs; the traced versions were made by adding coloured lines and number badges to them. The table of contents is a Word field: update it in Word before exporting the PDF.
