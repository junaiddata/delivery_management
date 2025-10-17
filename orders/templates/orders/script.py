import zipfile
import os

# Path to the ZIP file
zip_path = "/home/junaiddo/delivery_management/orders/templates/orders/ZIP.zip"
extract_path = "/home/junaiddo/delivery_management/orders/templates/orders"

# Ensure extraction folder exists
os.makedirs(extract_path, exist_ok=True)

# Extract files
with zipfile.ZipFile(zip_path, 'r') as zip_ref:
    zip_ref.extractall(extract_path)

print("Files extracted successfully!")