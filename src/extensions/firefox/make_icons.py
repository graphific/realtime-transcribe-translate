#!/usr/bin/env python3
"""
Create icon files for the Firefox extension
Run this script in the firefox-extension directory
"""

from PIL import Image, ImageDraw
import os

def create_microphone_icon(size):
    """Create a simple microphone icon"""
    # Create image with transparent background
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Colors
    mic_color = (33, 150, 243)  # Blue
    stand_color = (100, 100, 100)  # Gray
    
    # Scale factors based on size
    if size == 16:
        # Microphone body (simplified for small size)
        draw.ellipse([4, 2, 12, 10], fill=mic_color)
        # Stand
        draw.rectangle([7, 10, 9, 14], fill=stand_color)
        # Base
        draw.rectangle([5, 13, 11, 15], fill=stand_color)
    
    elif size == 48:
        # Microphone body
        draw.ellipse([16, 8, 32, 28], fill=mic_color)
        # Grille lines
        for y in range(12, 25, 3):
            draw.line([18, y, 30, y], fill=(255, 255, 255), width=1)
        # Stand
        draw.rectangle([22, 28, 26, 38], fill=stand_color)
        # Base
        draw.ellipse([18, 36, 30, 42], fill=stand_color)
        # Sound waves
        for i in range(3):
            x = 34 + i * 3
            draw.arc([x, 14 + i * 2, x + 4, 22 - i * 2], 270, 90, fill=mic_color, width=2)
    
    elif size == 128:
        # Microphone body
        draw.ellipse([45, 20, 83, 75], fill=mic_color)
        # Grille lines
        for y in range(30, 65, 4):
            draw.line([50, y, 78, y], fill=(255, 255, 255), width=2)
        # Stand
        draw.rectangle([60, 75, 68, 100], fill=stand_color)
        # Base
        draw.ellipse([50, 95, 78, 108], fill=stand_color)
        # Sound waves
        for i in range(4):
            x = 90 + i * 6
            draw.arc([x, 35 + i * 4, x + 8, 60 - i * 4], 270, 90, fill=mic_color, width=3)
        # Connection status indicator (small dot)
        draw.ellipse([108, 20, 118, 30], fill=(76, 175, 80))  # Green dot
    
    return img

def main():
    """Create all required icon files"""
    sizes = [16, 48, 128]
    
    print("Creating extension icons...")
    
    for size in sizes:
        print(f"Creating {size}x{size} icon...")
        icon = create_microphone_icon(size)
        filename = f"icon-{size}.png"
        icon.save(filename, "PNG")
        print(f"✅ Saved {filename}")
    
    print("\n🎉 All icons created successfully!")
    print("\nTo use these icons:")
    print("1. Copy the icon-*.png files to your firefox-extension directory")
    print("2. Update manifest.json to reference local files instead of data URLs")
    print("3. Reload the extension")

if __name__ == "__main__":
    try:
        main()
    except ImportError:
        print("❌ PIL (Pillow) is required to create icons")
        print("Install with: pip install Pillow")
    except Exception as e:
        print(f"❌ Error creating icons: {e}")
