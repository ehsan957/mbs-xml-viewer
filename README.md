MBS XML Viewer

A small desktop GUI for browsing the Australian Medicare Benefits Schedule (MBS) XML data file. Search for an item number, and see every field for that item laid out with a plain-English explanation of what each field means and which other fields it's related to.

Built because the raw MBS XML file has 1000+ repeated records with 30+ fields each, and the official field dictionary is a separate PDF you'd otherwise have to cross-reference by hand.

Features
Fast search — type an item number to filter the list live.
Full field table for the selected item: field name, value, and a short description of what that field means.
Field detail panel — click any row to see the full (unwrapped) value plus which other fields it's related to (e.g. selecting ScheduleFee shows you should also check FeeType, FeeStartDate, and the Benefit75/85/100 fields).
Resizable layout — drag the divider between the field table and the detail panel to resize either one.
Handles the file via streaming XML parsing, so it stays responsive even with thousands of records.
Requirements
Python 3.8+
No external dependencies — uses only the standard library (tkinter, xml.etree.ElementTree).

On most systems tkinter ships with Python already. On some Linux distros you may need to install it separately, e.g.:

bash
sudo apt install python3-tk
Usage
bash
python mbs_viewer.py                        # then use File > Open
python mbs_viewer.py MBS-XML-20260701.XML   # open a file directly
Use File > Open (or pass the file as a command-line argument) to load an MBS XML file.
Type in the search box to filter by item number.
Click an item in the left list to see all of its fields on the right.
Click any field row to see its full value and description in the panel below.
Getting the data file

This repo does not include the MBS XML data file. It's Commonwealth of Australia data, updated quarterly, and best downloaded fresh rather than committed to source control.

Download the current file from the official MBS Online downloads page:

https://www.mbsonline.gov.au/internet/mbsonline/publishing.nsf/Content/downloads

Look for the XML Data File section and download MBS-XML-YYYYMMDD.XML (right-click the link and "Save link as", since it opens as XML in most browsers rather than downloading directly).

The official field dictionary this tool's descriptions are based on is here:

https://www.mbsonline.gov.au/internet/mbsonline/publishing.nsf/Content/FAQ-XML_Help

Data licensing

The MBS data itself is © Commonwealth of Australia. This project only provides a viewer for that data — check the MBS Online site for the applicable copyright and usage terms before redistributing the data file itself.

License

MIT
