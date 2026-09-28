import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter
BLUE=PatternFill('solid',fgColor='DCE6F2'); GREY=PatternFill('solid',fgColor='EFEFEF')
TY="2026/27"
tabs=[]
tabs.append(("Summary","Written by Nomad Pro after every count. Edits here are ignored.",
 [("Item",0),("Value",0),("Source rows",0),("As of",0)],
 [("UK days this tax year (2026/27)","1 of 16","D-2026-09-14","2026-09-21"),
  ("Schengen days in the last 180","11 of 90","D-2026-09-10–D-2026-09-12, D-2026-09-14–D-2026-09-21","2026-09-21"),
  ("Days not logged this tax year","1","D-2026-09-13","2026-09-21"),
  ("Other stay limits in use","None right now","","2026-09-21"),
  ("Last updated","2026-09-21 21:04","","")],[32,18,52,12]))
P=lambda c:{"PT":"Portugal (PT)","GB":"United Kingdom (GB)","ES":"Spain (ES)","TH":"Thailand (TH)","":""}[c]
d=[("10","PT","Lisbon","","","R-0002","Has a record","Setup"),
   ("11","PT","Lisbon","","","R-0002","Has a record","Setup"),
   ("12","PT","Lisbon","","","R-0002","Has a record","Daily check-in"),
   ("13","","","","","","Not logged",""),
   ("14","GB","London","PT","No","R-0001","Has a record","Daily check-in"),
   ("15","ES","Madrid","GB","","","You told me","Daily check-in"),
   ("16","ES","Madrid","","","","You told me","Daily check-in"),
   ("17","ES","Toledo","","","","You told me","Daily check-in"),
   ("18","ES","Toledo","","","","You told me","Daily check-in"),
   ("19","PT","Porto","ES","","","You told me","Daily check-in"),
   ("20","PT","Porto","","","","You told me","Daily check-in"),
   ("21","PT","Porto","","","","You told me","Daily check-in")]
days=[(f"D-2026-09-{x[0]}",f"2026-09-{x[0]}",TY,P(x[1]),x[2],P(x[3]),x[4],x[5],x[6],x[7],"") for x in d]
tabs.append(("Days","Blue columns are yours to edit; I read them before every count. Grey columns come from the log.",
 [("Row ID",0),("Date",0),("Tax year",0),("Country",1),("Place",1),("Also in (travel day)",1),("UK work over 3h",1),("Records",0),("Confidence",0),("Logged via",0),("Locked",0)],
 days,[14,12,10,20,11,20,16,10,14,15,8]))
tabs.append(("Records","Blue columns are yours to edit; add a row for a new record and I'll give it an ID.",
 [("Record ID",0),("Proves days",1),("Type",1),("Description",1),("File or link",1)],
 [("R-0001","D-2026-09-14","Email","Example Air flight booking, Lisbon to London","Email link (Gmail)"),
  ("R-0002","D-2026-09-10–D-2026-09-12","Document","Rental agreement, Lisbon flat (example)","evidence/2026-09-01-rental-example.pdf")],[13,28,11,44,38]))
tabs.append(("Trips","Blue columns are yours to edit. I recheck saved trips weekly.",
 [("Trip ID",0),("Country",1),("Place",1),("First night",1),("Last night",1),("Status",1),("Result when saved",0),("Saved on",0),("Last checked",0)],
 [("T-001","United Kingdom (GB)","London","2026-12-18","2026-12-27","Idea (what if)","UK 11 of 16","2026-09-20","2026-09-21"),
  ("T-002","Thailand (TH)","Bangkok","2027-01-05","2027-02-20","Booked","Thailand 47 of 60","2026-09-21","2026-09-21")],[10,20,10,12,12,15,21,12,15]))
tabs.append(("Profile","Blue column is yours to edit; I'll read changes back to you before using them.",
 [("Section",0),("Item",0),("Value",1),("Tax year",0),("Agreed on",0),("Source",0)],
 [("Prior years","UK resident","Yes","2025/26","2026-09-10","Setup"),
  ("Prior years","UK resident","No","2024/25","2026-09-10","Setup"),
  ("Prior years","UK resident","No","2023/24","2026-09-10","Setup"),
  ("Left the UK","Date","2026-03-20","2025/26","2026-09-10","You told me"),
  ("Passports","British passport, expires","2031-05-14","","2026-09-11","You told me"),
  ("UK ties","Family","No","2026/27","2026-09-14","You told me"),
  ("UK ties","Accommodation","Yes: parents' home (label: Family home)","2026/27","2026-09-14","You told me"),
  ("UK ties","Work","Not sure","2026/27","2026-09-14","You told me"),
  ("Work-day rule","Version 1 (from 2026-09-10)","Remote job: weekdays are work days; weekends and UK bank holidays are not; ask me on travel days","","2026-09-14","You told me"),
  ("Check-in","Time and timezone","21:00, Europe/Lisbon; weekly line on Sunday","","2026-09-10","Setup"),
  ("Backup delivery","Monthly backup","In chat","","2026-09-10","Setup")],[16,28,58,10,12,13]))
tabs.append(("Changes","Every change to your log, newest last. Edits here are ignored.",
 [("Day changed",0),("Field",0),("From",0),("To",0),("Via",0),("Reason",0),("Changed at",0)],
 [("D-2026-09-10–D-2026-09-12","Records","","R-0002","Record added","Rental agreement filed at setup","2026-09-12 21:02"),
  ("D-2026-09-14","Records","","R-0001","Record added","Booking email attached after you said yes","2026-09-15 21:03"),
  ("D-2026-09-17","Place","Madrid","Toledo","Your correction","edited in sheet","2026-09-20 09:14"),
  ("T-001","Status","","Idea (what if)","Trip saved","You saved this trip","2026-09-20 18:30")],[28,10,10,16,16,40,17]))
tabs.append(("Outputs","Every export, PDF and backup, newest last. Edits here are ignored.",
 [("Output ID",0),("Date",0),("Type",0),("Date range",0),("Rows used",0),("File location",0)],
 [("O-0001","2026-09-21","Travel and day log (PDF + CSV)","2026-04-06 to 2026-09-21","D-2026-09-10–D-2026-09-21","exports/Travel and day log 2026-27.pdf, .csv"),
  ("O-0002","2026-09-21","Dashboard","2026-04-06 to 2026-09-21","D-2026-09-10–D-2026-09-21","exports/dashboard.html")],[13,11,28,24,28,42]))
wb=openpyxl.Workbook(); wb.remove(wb.active); wb.properties.title="Nomad Pro – Travel log"
for name,note,heads,rows,widths in tabs:
    ws=wb.create_sheet(name)
    ws.append([note]); ws.merge_cells(start_row=1,start_column=1,end_row=1,end_column=len(heads))
    ws['A1'].font=Font(italic=True,color='555555'); ws['A1'].alignment=Alignment(vertical='center')
    ws.append([h for h,_ in heads])
    for i,(h,ed) in enumerate(heads,1):
        c=ws.cell(row=2,column=i); c.fill=BLUE if ed else GREY; c.font=Font(bold=True,color='1F3A5F' if ed else '7F7F7F')
    for r in rows: ws.append(list(r))
    ws.freeze_panes='A3'
    for i,w in enumerate(widths,1): ws.column_dimensions[get_column_letter(i)].width=w
    for row in ws.iter_rows():
        for c in row: c.number_format='@'
wb.save('sample-travel-log.xlsx')
