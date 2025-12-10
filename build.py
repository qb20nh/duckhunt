import argparse
import os
import shutil
import sys

import PyInstaller.__main__

def build():
    parser = argparse.ArgumentParser(description="Build DuckHunt executable")
    parser.add_argument("--no-clean", action="store_true", help="Do not clean before building")
    parser.add_argument("--name", help="Name of the executable", default="duckhunt-win")
    
    args = parser.parse_args()

    if os.name != 'nt':
        print("Error: This build script is designed for Windows only.")
        sys.exit(1)

    # Clean only if not disabled
    if not args.no_clean:
         print("Cleaning previous builds...")
         if os.path.exists('dist'):
             shutil.rmtree('dist')
         if os.path.exists('build'):
             shutil.rmtree('build')
    
    print(f"Building {args.name} for Windows...")
    
    pyinstaller_args = [
        'duckhunt_win/__main__.py',
        f'--name={args.name}',
        '--noconsole',
        '--onefile',
        '--icon=duckhunt_win/resources/favicon.ico',
        f'--add-data=duckhunt_win/resources;duckhunt_win/resources',
        '--noconfirm',
    ]

    if not args.no_clean:
        pyinstaller_args.append('--clean')
    
    PyInstaller.__main__.run(pyinstaller_args)
    print("Build complete.")

if __name__ == '__main__':
    build()
