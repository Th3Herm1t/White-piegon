import pandas as pd
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 200)
pd.set_option('display.max_colwidth', 100)

# Read the Excel file
df_raw = pd.read_excel(r'c:\Users\abdel\Desktop\White piegon\FILLETTE  V3.xlsx', header=None)

# Save to text file
with open('xlsx_structure.txt', 'w', encoding='utf-8') as f:
    f.write("XLSX Structure Analysis\n")
    f.write("=" * 80 + "\n\n")
    
    f.write(f"Total rows: {len(df_raw)}\n")
    f.write(f"Total columns: {len(df_raw.columns)}\n\n")
    
    f.write("First 30 rows with non-null values:\n")
    f.write("-" * 80 + "\n")
    for i in range(min(30, len(df_raw))):
        f.write(f"\nRow {i}:\n")
        for j, val in enumerate(df_raw.iloc[i].tolist()):
            if pd.notna(val):
                f.write(f"  Col[{j}]: {val}\n")
    
    f.write("\n" + "=" * 80 + "\n")
    f.write("Sample of data rows (rows 5-15):\n")
    f.write("-" * 80 + "\n")
    for i in range(5, min(15, len(df_raw))):
        f.write(f"\nRow {i}: {[v for v in df_raw.iloc[i].tolist() if pd.notna(v)]}\n")

print("Output saved to xlsx_structure.txt")
