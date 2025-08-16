import csv
import os
from collections import defaultdict

csv_files = [f for f in os.listdir('.') if f.endswith('.csv')]
file_columns = {}

for file in csv_files:
    with open(file, 'r', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        headers = next(reader, None)
        if headers:
            headers = [h.strip() for h in headers if h.strip()]
            file_columns[file] = headers

columns_to_files = defaultdict(list)
for file, columns in file_columns.items():
    columns_key = tuple(columns)
    columns_to_files[columns_key].append(file)

print(f"Totale file CSV analizzati: {len(csv_files)}\n")
print(f"Numero di strutture di colonne diverse trovate: {len(columns_to_files)}\n")

for i, (columns, files) in enumerate(columns_to_files.items(), 1):
    print(f"\n{'='*80}")
    print(f"GRUPPO {i} - {len(files)} file con questa struttura:")
    print(f"{'='*80}")
    print(f"Colonne: {list(columns)}")
    print(f"\nFile:")
    for file in sorted(files):
        print(f"  - {file}")

print("\n\nRIEPILOGO DIFFERENZE:")
print("="*80)

base_columns = ['PR', 'COMUNE', 'MAIL BIBLIOTECA', 'MAIL UFF CULTURA', 'MAIL GENERICA']

for file, columns in sorted(file_columns.items()):
    extra_cols = [c for c in columns if c not in base_columns and c not in ['', 'CR', '6']]
    if extra_cols or len(columns) != 5:
        print(f"\n{file}:")
        print(f"  Numero colonne: {len(columns)}")
        if extra_cols:
            print(f"  Colonne aggiuntive: {extra_cols}")