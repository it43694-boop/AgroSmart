"""Script utilitaire pour convertir en masse des images en WebP.

Usage:
    python scripts/convert_images_to_webp.py /path/to/images --quality 90
"""
import sys
import argparse
from services.image_service import batch_convert_folder


def main():
    p = argparse.ArgumentParser()
    p.add_argument('folder', help='Dossier contenant les images à convertir')
    p.add_argument('--quality', type=int, default=90, help='Qualité WebP (0-100)')
    p.add_argument('--lossless', action='store_true', help='Utiliser WebP lossless')
    args = p.parse_args()

    n = batch_convert_folder(args.folder, quality=args.quality, lossless=args.lossless)
    print(f'Converted {n} files to WebP in {args.folder}')


if __name__ == '__main__':
    main()
