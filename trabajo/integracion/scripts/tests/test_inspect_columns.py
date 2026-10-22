import re
import pandas as pd

with open('scripts/src/reforestacion_pipeline.py', encoding='utf-8') as f:
    text = f.read()

df_accesses = set(re.findall(r'df(?:_sp|_species|_cat)\[[\'\"](\w+)[\'\"]\]', text))
row_accesses = set(re.findall(r'row\[[\'\"](\w+)[\'\"]\]', text))

print("DataFrame column accesses:", sorted(df_accesses))
print("Row item accesses:", sorted(row_accesses))

cat = pd.read_csv('data/semiraw/catalogo_especies_consolidado.csv')
print("Catalogue columns:", sorted(cat.columns))
