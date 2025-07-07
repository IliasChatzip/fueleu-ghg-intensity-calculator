# Replaces all tab characters with 4 spaces in app.py

INPUT_FILE = "app.py"
TAB_REPLACEMENT = "    "  # 4 spaces

with open(INPUT_FILE, "r", encoding="utf-8") as f:
    lines = f.readlines()

fixed_lines = [line.replace("\t", TAB_REPLACEMENT) for line in lines]

with open(INPUT_FILE, "w", encoding="utf-8") as f:
    f.writelines(fixed_lines)

print(f"✔ All tabs in {INPUT_FILE} have been replaced with spaces.")
