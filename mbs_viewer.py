#!/usr/bin/env python3
"""
mbs_viewer.py

Simple GUI to browse a large MBS-style XML file (repeated <Data> records
under <MBS_XML>) and inspect every field for a chosen ItemNum.

Usage:
    python mbs_viewer.py                     # then use File > Open
    python mbs_viewer.py MBS-XML-20260701.XML

Left side : searchable list of ItemNum / SubItemNum
Right side: table of every field/value for the selected record
"""

import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from xml.etree import ElementTree as ET
from collections import OrderedDict


def strip_ns(tag):
    if isinstance(tag, str) and tag.startswith("{"):
        return tag.split("}", 1)[1]
    return tag


# Field descriptions sourced from the official MBS Online XML field
# dictionary: https://www.mbsonline.gov.au/internet/mbsonline/publishing.nsf/Content/FAQ-XML_Help
# "related" lists other field names whose value depends on / governs this one,
# so you can see at a glance which fields to check together.
FIELD_INFO = {
    "ItemNum": {
        "desc": "The MBS item number.",
        "related": ["SubItemNum"],
    },
    "SubItemNum": {
        "desc": "Sub-item number for precedent items (e.g. 30000-series items). Not populated in current files.",
        "related": ["ItemNum"],
    },
    "ItemStartDate": {
        "desc": "Date the item commenced.",
        "related": ["ItemEndDate", "NewItem"],
    },
    "ItemEndDate": {
        "desc": "Date the item ceased, if it has one.",
        "related": ["ItemStartDate"],
    },
    "Category": {
        "desc": "The MBS Category the item belongs to.",
        "related": ["Group", "SubGroup", "SubHeading"],
    },
    "Group": {
        "desc": "The Group the item relates to, within its Category.",
        "related": ["Category", "SubGroup"],
    },
    "SubGroup": {
        "desc": "The SubGroup the item relates to, within its Group.",
        "related": ["Group", "SubHeading"],
    },
    "SubHeading": {
        "desc": "The SubHeading the item relates to.",
        "related": ["SubGroup"],
    },
    "ItemType": {
        "desc": "Item type: S = standard, P = precedent, D = covered under a 3C determination.",
        "related": [],
    },
    "FeeType": {
        "desc": "Fee type: N = normal fee, D = derived fee. Controls whether ScheduleFee or DerivedFee appears.",
        "related": ["ScheduleFee", "FeeStartDate", "DerivedFee", "DerivedFeeStartDate"],
    },
    "ProviderType": {
        "desc": "Provider category applicable to the item (e.g. G = GP, S = Specialist, HR = Hospital Recognised).",
        "related": [],
    },
    "NewItem": {
        "desc": "Y if this is a new item (ItemStartDate after the base report date), N if existing.",
        "related": ["ItemStartDate"],
    },
    "ItemChange": {
        "desc": "Y if there has been any change to the item since the last release, N otherwise.",
        "related": ["FeeChange", "DescriptorChange", "AnaesChange", "EMSNChange"],
    },
    "AnaesChange": {
        "desc": "Y if the anaesthetic basic units changed for this item, N otherwise.",
        "related": ["BasicUnits", "Anaes"],
    },
    "DescriptorChange": {
        "desc": "Y if the item's description/wording changed, N otherwise.",
        "related": ["Description", "DescriptionStartDate"],
    },
    "FeeChange": {
        "desc": "Y if the fee changed, N if not, blank if the item is new (so there's no prior fee to compare).",
        "related": ["ScheduleFee", "FeeStartDate"],
    },
    "EMSNChange": {
        "desc": "Y if the EMSN cap changed, N if not, NULL/blank if the item has no current EMSN cap.",
        "related": ["EMSNCap", "EMSNChangeDate"],
    },
    "EMSNCap": {
        "desc": ("Whether the item has an EMSN cap and what type: N = no cap, P = normal-fee percentage "
                 "cap, F = fixed cap. Governs whether the other EMSN* fields are populated."),
        "related": ["EMSNStartDate", "EMSNEndDate", "EMSNFixedCapAmount", "EMSNPercentageCap",
                    "EMSNMaximumCap", "EMSNDescription", "EMSNChangeDate"],
    },
    "BenefitType": {
        "desc": ("Which benefit level(s) apply: A=75% only, B=85% only, C=75%&85%, D=75%&100%, "
                 "E=100% only. Controls which of Benefit75/Benefit85/Benefit100 appear."),
        "related": ["Benefit75", "Benefit85", "Benefit100", "BenefitStartDate"],
    },
    "BenefitStartDate": {
        "desc": "Date the current benefit level(s) commenced.",
        "related": ["BenefitType"],
    },
    "FeeStartDate": {
        "desc": "Date the current Schedule fee commenced. Only present when FeeType = N.",
        "related": ["ScheduleFee", "FeeType"],
    },
    "ScheduleFee": {
        "desc": "The Schedule fee amount. Only present when FeeType = N.",
        "related": ["FeeStartDate", "FeeType", "Benefit75", "Benefit85", "Benefit100"],
    },
    "Benefit75": {
        "desc": "The 75% benefit amount. Only present when FeeType = N and BenefitType is A, C or D.",
        "related": ["BenefitType", "ScheduleFee"],
    },
    "Benefit85": {
        "desc": "The 85% benefit amount. Only present when FeeType = N and BenefitType is B or C.",
        "related": ["BenefitType", "ScheduleFee"],
    },
    "Benefit100": {
        "desc": "The 100% benefit amount. Only present when FeeType = N and BenefitType is D or E.",
        "related": ["BenefitType", "ScheduleFee"],
    },
    "BasicUnits": {
        "desc": ("The Anaesthetic Basic Unit value. Values only occur for items in the range "
                 "20100 to 25020 (the anaesthesia items); otherwise blank."),
        "related": ["Anaes", "AnaesChange"],
    },
    "EMSNStartDate": {
        "desc": "Date the current EMSN cap commenced, if the item has one.",
        "related": ["EMSNCap"],
    },
    "EMSNEndDate": {
        "desc": "Date the EMSN cap ends, if it ends in the future.",
        "related": ["EMSNCap"],
    },
    "EMSNFixedCapAmount": {
        "desc": "The fixed EMSN cap amount, only present if EMSNCap = F.",
        "related": ["EMSNCap"],
    },
    "EMSNPercentageCap": {
        "desc": "The EMSN percentage cap, only present if EMSNCap = P.",
        "related": ["EMSNCap", "EMSNMaximumCap"],
    },
    "EMSNMaximumCap": {
        "desc": "The maximum cap amount for a percentage EMSN cap, only present if EMSNCap = P.",
        "related": ["EMSNCap", "EMSNPercentageCap"],
    },
    "EMSNDescription": {
        "desc": "Description of the EMSN derived cap, only present for derived fees with a current percentage cap.",
        "related": ["EMSNCap", "FeeType"],
    },
    "EMSNChangeDate": {
        "desc": "Date on which a change to the EMSN cap became effective, if it changed.",
        "related": ["EMSNChange", "EMSNCap"],
    },
    "DerivedFeeStartDate": {
        "desc": "Date the current derived fee commenced. Only present when FeeType = D.",
        "related": ["DerivedFee", "FeeType"],
    },
    "DerivedFee": {
        "desc": "Text description of how the derived fee is calculated. Only present when FeeType = D.",
        "related": ["DerivedFeeStartDate", "FeeType"],
    },
    "Anaes": {
        "desc": "Anaesthetic indicator. Only present (value Y) if the item attracts an anaesthetic.",
        "related": ["BasicUnits", "AnaesChange"],
    },
    "DescriptionStartDate": {
        "desc": "Date the current item description commenced.",
        "related": ["Description", "DescriptorChange"],
    },
    "Description": {
        "desc": "The full text description of the item (often long / multi-line).",
        "related": ["DescriptionStartDate", "DescriptorChange"],
    },
    "QFEStartDate": {
        "desc": "Commencement date of a Time Limited Listing evaluation, if this item is time-limited.",
        "related": ["QFEEndDate"],
    },
    "QFEEndDate": {
        "desc": "End date of a Time Limited Listing evaluation, if this item is time-limited.",
        "related": ["QFEStartDate"],
    },
}


def load_records(xml_path):
    """
    Stream-parse the file and return a list of OrderedDict, one per
    top-level record element (assumed to be the repeated child of the
    root, e.g. <Data> under <MBS_XML>). Field order is preserved.
    """
    records = []
    context = ET.iterparse(xml_path, events=("start", "end"))
    depth = 0
    record_tag = None
    current = None

    for event, elem in context:
        tag = strip_ns(elem.tag)

        if event == "start":
            depth += 1
            # the record tag is whatever sits directly under the root (depth 2)
            if depth == 2:
                record_tag = tag
                current = OrderedDict()

        elif event == "end":
            if depth == 3 and current is not None:
                # a field inside the current record
                text = (elem.text or "").strip()
                current[tag] = text
            elif depth == 2 and current is not None:
                records.append(current)
                current = None
                elem.clear()
            depth -= 1

    return records, record_tag


class MBSViewer(tk.Tk):
    def __init__(self, xml_path=None):
        super().__init__()
        self.title("MBS XML Viewer")
        self.geometry("1200x650")

        self.records = []
        self.record_tag = ""
        self.filtered_indices = []
        self._current_record = {}

        self._build_menu()
        self._build_layout()

        if xml_path:
            self.load_file(xml_path)

    # ---------- UI construction ----------

    def _build_menu(self):
        menubar = tk.Menu(self)
        filemenu = tk.Menu(menubar, tearoff=0)
        filemenu.add_command(label="Open XML...", command=self.open_file_dialog)
        filemenu.add_separator()
        filemenu.add_command(label="Exit", command=self.destroy)
        menubar.add_cascade(label="File", menu=filemenu)
        self.config(menu=menubar)

    def _build_layout(self):
        # top: search box
        top_frame = ttk.Frame(self, padding=6)
        top_frame.pack(side=tk.TOP, fill=tk.X)

        ttk.Label(top_frame, text="Search ItemNum:").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *args: self.apply_filter())
        search_entry = ttk.Entry(top_frame, textvariable=self.search_var)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=6)

        self.status_var = tk.StringVar(value="No file loaded")
        ttk.Label(top_frame, textvariable=self.status_var).pack(side=tk.RIGHT)

        # main: paned window with list on left, detail table on right
        main_pane = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        main_pane.pack(fill=tk.BOTH, expand=True)

        # left: listbox of items
        left_frame = ttk.Frame(main_pane, padding=6)
        self.item_list = tk.Listbox(left_frame, activestyle="dotbox", width=14)
        self.item_list.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        left_scroll = ttk.Scrollbar(left_frame, orient=tk.VERTICAL, command=self.item_list.yview)
        left_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.item_list.config(yscrollcommand=left_scroll.set)
        self.item_list.bind("<<ListboxSelect>>", self.on_select_item)
        main_pane.add(left_frame, weight=1)

        # right: table of field/value/description, plus a wrapped detail panel below.
        # Uses a vertical PanedWindow so the user can drag the divider to resize
        # the detail area.
        right_frame = ttk.Frame(main_pane, padding=6)
        right_pane = ttk.PanedWindow(right_frame, orient=tk.VERTICAL)
        right_pane.pack(fill=tk.BOTH, expand=True)

        table_frame = ttk.Frame(right_pane)
        columns = ("field", "value", "description")
        self.detail_tree = ttk.Treeview(table_frame, columns=columns, show="headings")
        self.detail_tree.heading("field", text="Field")
        self.detail_tree.heading("value", text="Value")
        self.detail_tree.heading("description", text="What is this?")
        self.detail_tree.column("field", width=150, anchor=tk.W)
        self.detail_tree.column("value", width=220, anchor=tk.W)
        self.detail_tree.column("description", width=350, anchor=tk.W)
        self.detail_tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        right_scroll = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.detail_tree.yview)
        right_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.detail_tree.config(yscrollcommand=right_scroll.set)
        self.detail_tree.bind("<<TreeviewSelect>>", self.on_select_field)
        right_pane.add(table_frame, weight=3)

        # bottom: full, wrapped detail for whichever field row is selected above
        # (long text like Description or DerivedFee is easier to read here than
        # squeezed into a single table row). Drag the pane divider above to resize.
        detail_frame = ttk.LabelFrame(right_pane, text="Field detail (drag divider above to resize)", padding=6)
        self.detail_text = tk.Text(detail_frame, height=8, wrap=tk.WORD, state=tk.DISABLED)
        self.detail_text.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        detail_scroll = ttk.Scrollbar(detail_frame, orient=tk.VERTICAL, command=self.detail_text.yview)
        detail_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.detail_text.config(yscrollcommand=detail_scroll.set)
        self.detail_text.tag_configure("heading", font=("TkDefaultFont", 10, "bold"))
        right_pane.add(detail_frame, weight=1)

        main_pane.add(right_frame, weight=4)

    # ---------- data loading ----------

    def open_file_dialog(self):
        path = filedialog.askopenfilename(filetypes=[("XML files", "*.xml *.XML"), ("All files", "*.*")])
        if path:
            self.load_file(path)

    def load_file(self, path):
        try:
            self.records, self.record_tag = load_records(path)
        except Exception as e:
            messagebox.showerror("Error loading XML", str(e))
            return

        self.status_var.set(f"{len(self.records)} records loaded ({self.record_tag})")
        self.apply_filter()

    # ---------- filtering / selection ----------

    def apply_filter(self):
        query = self.search_var.get().strip().lower()
        self.item_list.delete(0, tk.END)
        self.filtered_indices = []

        for idx, rec in enumerate(self.records):
            item_num = rec.get("ItemNum", "")
            sub_item = rec.get("SubItemNum", "")
            label = item_num if not sub_item else f"{item_num} ({sub_item})"

            if query and query not in item_num.lower():
                continue

            self.filtered_indices.append(idx)
            self.item_list.insert(tk.END, label)

    def on_select_item(self, event):
        selection = self.item_list.curselection()
        if not selection:
            return
        list_pos = selection[0]
        record_idx = self.filtered_indices[list_pos]
        record = self.records[record_idx]

        self.detail_tree.delete(*self.detail_tree.get_children())
        self._clear_detail_text()
        for field, value in record.items():
            info = FIELD_INFO.get(field, {})
            short_desc = info.get("desc", "")
            # keep the table row on one line; full text is shown below on click
            display_value = value.replace("\n", " ").strip()
            self.detail_tree.insert("", tk.END, values=(field, display_value, short_desc))

        self._current_record = record

    def on_select_field(self, event):
        selection = self.detail_tree.selection()
        if not selection:
            return
        field, _value_col, _desc_col = self.detail_tree.item(selection[0], "values")
        full_value = getattr(self, "_current_record", {}).get(field, "")
        info = FIELD_INFO.get(field, {"desc": "No description available for this field.", "related": []})

        self.detail_text.config(state=tk.NORMAL)
        self.detail_text.delete("1.0", tk.END)
        self.detail_text.insert(tk.END, field + "\n", "heading")
        self.detail_text.insert(tk.END, info["desc"] + "\n\n")
        if info.get("related"):
            self.detail_text.insert(tk.END, "Related fields: ", "heading")
            self.detail_text.insert(tk.END, ", ".join(info["related"]) + "\n\n")
        self.detail_text.insert(tk.END, "Value:\n", "heading")
        self.detail_text.insert(tk.END, full_value if full_value else "(empty)")
        self.detail_text.config(state=tk.DISABLED)

    def _clear_detail_text(self):
        self.detail_text.config(state=tk.NORMAL)
        self.detail_text.delete("1.0", tk.END)
        self.detail_text.config(state=tk.DISABLED)


def main():
    xml_path = sys.argv[1] if len(sys.argv) > 1 else None
    app = MBSViewer(xml_path)
    app.mainloop()


if __name__ == "__main__":
    main()