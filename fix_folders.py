import os
import re
import shutil

base_path = "output/migrated_open_liberty/src/main/java"
flat_dir = os.path.join(base_path, "com/company/customer")
java_files = [f for f in os.listdir(flat_dir) if f.endswith(".java")]

for filename in java_files:
    filepath = os.path.join(flat_dir, filename)
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Extract package
    match = re.search(r'package\s+([\w.]+);', content)
    if match:
        package = match.group(1)
        new_dir = os.path.join(base_path, package.replace('.', '/'))
        os.makedirs(new_dir, exist_ok=True)
        new_path = os.path.join(new_dir, filename)
        
        print(f"Moving {filename} to {new_dir}")
        shutil.move(filepath, new_path)
    else:
        print(f"No package found in {filename}")

# Clean up empty com/company/customer if needed
try:
    os.removedirs(flat_dir)
except OSError:
    pass
