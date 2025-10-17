import os
import shutil

# Define source and destination folders
source_folder = "/home/junaiddo/delivery_management/orders/templates/orders/ZIP"
destination_folder = "/home/junaiddo/delivery_management/orders/templates/orders"

# Ensure destination folder exists
os.makedirs(destination_folder, exist_ok=True)

# Move all files from source to destination
for filename in os.listdir(source_folder):
    source_path = os.path.join(source_folder, filename)
    destination_path = os.path.join(destination_folder, filename)

    if os.path.isfile(source_path):  # Ensure it's a file, not a folder
        shutil.move(source_path, destination_path)
        print(f"Moved: {filename}")

print("All files moved successfully!")