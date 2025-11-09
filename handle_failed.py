import pandas as pd
from main import main
# 1️⃣ Load the file that contains the IDs to keep
ids_df = pd.read_excel("Buick_failed_to_download.xlsx")

# 2️⃣ Extract the first column (excluding the header)
ids_to_keep = ids_df.iloc[:, 0].tolist()

# 3️⃣ Load the main file with all 1000 rows
df = pd.read_excel("Buick_2024_Yearly_1711241.xlsx")

# 4️⃣ Filter rows where the ID exists in the "to keep" list
# Replace "id_column_name" with the actual column name in the main file
filtered_df = df[df["id_column_name"].isin(ids_to_keep)]

# 5️⃣ Save the filtered result to a new Excel file
filtered_df.to_excel("Buick_filtered.xlsx", index=False)

print(f"✅ Filtered {len(filtered_df)} rows out of {len(df)}.")

main("Buick_filtered.xlsx")