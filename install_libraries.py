import sys
import subprocess
import platform

libraries = ["requests", "dotenv", "pathlib", "argparse"]

print("Installing required libraries...")
print()

for library in libraries:
    try:
        print("Installing", library, "...")
        subprocess.check_call([sys.executable, "-m", 'pip', 'install', library])
    except subprocess.CalledProcessError:
        print(f"Warning: Failed to install {library} with pip. Continuing anyway...")