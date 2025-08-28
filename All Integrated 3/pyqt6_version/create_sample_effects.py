#!/usr/bin/env python3
"""
Create sample PNG files for testing effects functionality
"""

import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

def create_sample_png(folder_path, filename, text, color):
    """Create a sample PNG file with text"""
    # Create a 160x90 image (same size as effect frames)
    img = Image.new('RGB', (160, 90), color=color)
    draw = ImageDraw.Draw(img)
    
    # Try to use a default font, fallback to basic if not available
    try:
        font = ImageFont.truetype("arial.ttf", 16)
    except:
        font = ImageFont.load_default()
    
    # Calculate text position to center it
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = (160 - text_width) // 2
    y = (90 - text_height) // 2
    
    # Draw text
    draw.text((x, y), text, fill='white', font=font)
    
    # Save the image
    img.save(folder_path / filename)
    print(f"Created: {folder_path / filename}")

def main():
    # Base effects folder
    effects_base = Path(__file__).parent / "effects"
    
    # Sample effects for each tab
    tab_effects = {
        "Web01": [
            ("effect1.png", "Web Effect 1", (50, 100, 150)),
            ("effect2.png", "Web Effect 2", (100, 50, 150)),
            ("effect3.png", "Web Effect 3", (150, 100, 50))
        ],
        "Web02": [
            ("transition1.png", "Transition 1", (200, 50, 50)),
            ("transition2.png", "Transition 2", (50, 200, 50)),
            ("transition3.png", "Transition 3", (50, 50, 200))
        ],
        "Web03": [
            ("overlay1.png", "Overlay 1", (150, 150, 50)),
            ("overlay2.png", "Overlay 2", (150, 50, 150)),
            ("overlay3.png", "Overlay 3", (50, 150, 150))
        ],
        "God01": [
            ("divine1.png", "Divine 1", (255, 215, 0)),
            ("divine2.png", "Divine 2", (255, 165, 0)),
            ("divine3.png", "Divine 3", (255, 140, 0))
        ],
        "Muslim": [
            ("islamic1.png", "Islamic 1", (0, 128, 0)),
            ("islamic2.png", "Islamic 2", (0, 100, 0)),
            ("islamic3.png", "Islamic 3", (0, 150, 0))
        ],
        "Stage": [
            ("stage1.png", "Stage 1", (128, 0, 128)),
            ("stage2.png", "Stage 2", (100, 0, 100)),
            ("stage3.png", "Stage 3", (150, 0, 150))
        ],
        "Telugu": [
            ("telugu1.png", "Telugu 1", (255, 69, 0)),
            ("telugu2.png", "Telugu 2", (255, 99, 71)),
            ("telugu3.png", "Telugu 3", (255, 140, 105))
        ]
    }
    
    # Create sample effects for each tab
    for tab_name, effects in tab_effects.items():
        tab_folder = effects_base / tab_name
        if tab_folder.exists():
            for filename, text, color in effects:
                create_sample_png(tab_folder, filename, text, color)
        else:
            print(f"Warning: Folder {tab_folder} does not exist")
    
    print("\nSample PNG files created successfully!")
    print("You can now run the application and see the effects in each tab.")

if __name__ == "__main__":
    main()