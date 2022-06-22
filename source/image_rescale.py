from PIL import Image
import pathlib, sys

def _rescale(image, percentage):
    with Image.open(image) as im:
        width, height = im.size
        resized_dimensions = (int(width * percentage), int(height * percentage))
        resized = im.resize(resized_dimensions)
        resized.save(image)

def rescale(image, percentage, batch=0):
    """Rescale images in batch"""
    if batch:
        for path in pathlib.Path(image).rglob('*.jpg'):
            _rescale(path, percentage)
    else: _rescale(image, percentage)

if '__main__' == __name__:
    x = 0

    if len(sys.argv) == 4:
        if '-b' in sys.argv: x = 1
        rescale(sys.argv[1+x], float(sys.argv[2+x])/100, batch=x)

    else: print("Usage: python3 [-b] input.jpg 75 (Percentage)")

