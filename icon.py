import glob
import os
from PIL import Image

def generate_icon():
    # Source pattern
    pattern = "duckhunt.*.png"
    files = glob.glob(pattern)
    
    if not files:
        print(f"No files found matching {pattern}")
        return

    print(f"Found source images: {files}")
    
    images = []
    for f in files:
        try:
            img = Image.open(f)
            images.append(img)
            print(f"Loaded {f} ({img.size})")
        except Exception as e:
            print(f"Failed to load {f}: {e}")

    if not images:
        print("No valid images to create icon.")
        return

    # Sort images by size (largest first usually preferred for high quality, but ICO dict handles it)
    # Actually for .save(append_images=...), the first image is the primary one, others are appended.
    # Usually largest first is best practice for the main view.
    images.sort(key=lambda i: i.size[0], reverse=True)
    
    output_path = "duckhunt_win/resources/favicon.ico"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    print(f"Saving icon to {output_path}...")
    try:
        # Save the first image as ICO, appending the rest
        images[0].save(
            output_path, 
            format='ICO', 
            sizes=[(img.width, img.height) for img in images],
            append_images=images[1:]
        )
        print("Icon generation successful.")
    except Exception as e:
        print(f"Failed to save icon: {e}")

if __name__ == "__main__":
    generate_icon()
