import argparse
import os
import shutil
import sys



def build():
    parser = argparse.ArgumentParser(description="Build DuckHunt executable")
    parser.add_argument("--ci", action="store_true", help="CI Mode: Clean output but keep build cache")
    parser.add_argument("--no-clean", action="store_true", help="Do not clean build artifacts")
    parser.add_argument("--name", default="duckhunt", help="Name of the output executable")
    
    args = parser.parse_args()

    if os.name != 'nt':
        print("Skipping Windows-only build script on non-Windows platform.")
        sys.exit(0)

    # Cleaning Logic
    should_clean_dist = True
    should_clean_build = True

    if args.no_clean:
        should_clean_dist = False
        should_clean_build = False
    elif args.ci:
        should_clean_dist = True
        should_clean_build = False
    
    if should_clean_dist:
         print("Cleaning dist (output)...")
         if os.path.exists('dist'):
             shutil.rmtree('dist')
    
    if should_clean_build:
         print("Cleaning build (cache)...")
         if os.path.exists('build'):
             shutil.rmtree('build')
    
    # extract version from source
    # We add the current directory to sys.path to ensure we can import the local module
    # even if it's not installed.
    sys.path.insert(0, os.path.abspath(os.getcwd()))
    try:
        from duckhunt_win._version import __version__
        version = __version__

        print(f"Generating version info for version {version}...")
        # Cleaning version string for Windows usage
        # We only want the numeric part for the tuple (e.g. 1.0.0)
        # Assuming format is something like 1.0.0-rc.1 or 1.0.0
        base_version = version.split('-')[0] 
        v_parts = [int(p) for p in base_version.split('.')]
        while len(v_parts) < 4:
            v_parts.append(0)
        v_tuple = tuple(v_parts[:4])
    except Exception as e:
        raise ImportError(f"Failed to determine version: {e}")

    output_name = f"{args.name}_v{version}"

    # Generate version_info.txt
    template_path = "version_info.template"
    if not os.path.exists(template_path):
         print(f"Error: Template not found at {template_path}")
         sys.exit(1)

    with open(template_path, "r", encoding="utf-8") as f:
        template_content = f.read()
        version_info_content = template_content.format(
            file_version_tuple=v_tuple,
            file_version_str=version
        )

    version_file_path = "version_info.txt"
    with open(version_file_path, "w", encoding="utf-8") as f:
        f.write(version_info_content)
    
    print(f"Building {output_name} for Windows...")
    
    pyinstaller_args = [
        'duckhunt_win/__main__.py',
        f'--name={output_name}',
        '--noconsole',
        '--onefile',
        '--icon=duckhunt_win/resources/favicon.ico',
        f'--add-data=duckhunt_win/resources;duckhunt_win/resources',
        '--version-file=version_info.txt',
        '--noconfirm',
    ]

    if should_clean_build:
        pyinstaller_args.append('--clean')
    
    try:
        import PyInstaller.__main__
        PyInstaller.__main__.run(pyinstaller_args)
    finally:
        # Cleanup generated version info file
        if os.path.exists(version_file_path):
            os.remove(version_file_path)

    print("Build complete.")

if __name__ == '__main__':
    build()
