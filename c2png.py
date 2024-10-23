import sys
import os
from PIL import Image

def convert_image_to_png(image_path, output_path):
    try:
        with Image.open(image_path) as img:
            # Remove the extension from the original filename
            base = os.path.splitext(os.path.basename(image_path))[0]
            # Create the full output path
            output_file = os.path.join(output_path, base + ".png")
            img.save(output_file, "PNG")
            print(f"Converted {image_path} to {output_file}")
    except Exception as e:
        print(f"Failed to convert {image_path}: {e}")

def main():
    args = sys.argv[1:]
    if not args:
        print("Usage: scriptname.py [image_file] | -all [directory_path]")
        sys.exit(1)
    if args[0] == "-all":
        if len(args) == 1:
            dir_path = os.getcwd()
        else:
            dir_path = args[1]
        if not os.path.isdir(dir_path):
            print(f"Error: {dir_path} is not a directory")
            sys.exit(1)
        # Process all image files in dir_path
        for filename in os.listdir(dir_path):
            if not filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp')):
                continue
            file_path = os.path.join(dir_path, filename)
            convert_image_to_png(file_path, dir_path)
    else:
        image_file = args[0]
        if not os.path.isfile(image_file):
            print(f"Error: {image_file} is not a file")
            sys.exit(1)
        dir_path = os.path.dirname(image_file)
        convert_image_to_png(image_file, dir_path)

if __name__ == "__main__":
    main()
