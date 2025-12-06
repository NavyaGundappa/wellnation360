import sqlite3

db_path = r"D:\wellnation360\wellnation360\instance\wellness.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# ✅ Check existing columns in pricing_plan
cursor.execute("PRAGMA table_info(pricing_plan);")
columns = cursor.fetchall()

print("✅ Current columns in pricing_plan:")
for col in columns:
    print(col)

existing_column_names = [col[1] for col in columns]

# ✅ If old INT column exists, migrate it safely
if "months" in existing_column_names:
    print("✅ Found existing 'months' column")

    # 1️⃣ Add new FLOAT column
    if "months_float" not in existing_column_names:
        cursor.execute(
            "ALTER TABLE pricing_plan ADD COLUMN months_float REAL;")
        print("✅ Added new FLOAT column: months_float")

    # 2️⃣ Copy INT data → FLOAT column
    cursor.execute("UPDATE pricing_plan SET months_float = months;")
    print("✅ Copied old INT data into FLOAT column")

else:
    print("❌ No 'months' column found!")

conn.commit()
conn.close()

print("✅ INT → FLOAT migration for months completed safely!")
