#!/usr/bin/env python3
"""Convertit les xlsx tennis-data.co.uk en CSV agrégé exploitable."""
import csv
import glob
import os
import openpyxl

SRC = "/Users/maxenceleguay/Sites/winnaHisto/datasets/tennis"
OUT = "/Users/maxenceleguay/Sites/winnaHisto/datasets/tennis_all.csv"


def main():
    rows_out = []
    headers_out = ["tour", "date", "tournament", "winner", "loser", "B365W", "B365L", "PSW", "PSL"]
    for path in sorted(glob.glob(os.path.join(SRC, "*.xlsx"))):
        name = os.path.basename(path)
        tour = "WTA" if name.startswith("w") else "ATP"
        wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
        ws = wb.active
        header = None
        for i, row in enumerate(ws.iter_rows(values_only=True)):
            if i == 0:
                header = list(row)
                continue
            d = dict(zip(header, row))
            try:
                rows_out.append([
                    tour,
                    d.get("Date") or d.get("date"),
                    d.get("Tournament") or "",
                    d.get("Winner") or "",
                    d.get("Loser") or "",
                    d.get("B365W") or "",
                    d.get("B365L") or "",
                    d.get("PSW") or "",
                    d.get("PSL") or "",
                ])
            except Exception:
                continue
        wb.close()
    with open(OUT, "w", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(headers_out)
        w.writerows(rows_out)
    print(f"Écrit {len(rows_out)} matchs → {OUT}")


if __name__ == "__main__":
    main()
