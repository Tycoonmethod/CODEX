from PIL import Image, ImageDraw, ImageFont
import os

# Create a new image with a white background
width = 300
height = 100
background_color = (255, 255, 255)
img = Image.new('RGB', (width, height), background_color)

# Get a drawing context
draw = ImageDraw.Draw(img)

# Draw a simple placeholder logo
# Rectangle border
draw.rectangle([10, 10, width-10, height-10], outline=(0, 0, 0), width=2)

# Text
text = "COMPANY\nLOGO"
text_bbox = draw.textbbox((0, 0), text, font=None)
text_width = text_bbox[2] - text_bbox[0]
text_height = text_bbox[3] - text_bbox[1]

# Center the text
x = (width - text_width) // 2
y = (height - text_height) // 2
draw.text((x, y), text, fill=(0, 0, 0))

# Save the image
img.save('assets/logo.png') 