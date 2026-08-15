from io import BytesIO
from PIL import Image
import os


def convert_bytes_to_webp(image_bytes: bytes, quality: int = 85, lossless: bool = False) -> bytes:
    """Convertit des octets d'image en WebP optimisé.

    - Force la conversion en sRGB basique via .convert('RGB'/'RGBA').
    - Utilise un quality élevé (85+) et method=6 pour meilleur rendu.
    """
    with Image.open(BytesIO(image_bytes)) as im:
        # Normalize mode: keep alpha if present otherwise RGB
        if im.mode in ("RGBA", "LA") or (im.mode == "P" and im.info.get("transparency") is not None):
            im = im.convert("RGBA")
        else:
            im = im.convert("RGB")

        out = BytesIO()
        save_kwargs = {
            "format": "WEBP",
            "quality": int(quality),
            "method": 6,
            "lossless": bool(lossless),
        }
        im.save(out, **save_kwargs)
        return out.getvalue()


def convert_file_to_webp(src_path: str, dst_path: str = None, quality: int = 85, lossless: bool = False) -> str:
    """Convertit un fichier image en WebP et retourne le chemin du fichier créé."""
    if dst_path is None:
        base, _ = os.path.splitext(src_path)
        dst_path = base + ".webp"

    with open(src_path, "rb") as f:
        data = convert_bytes_to_webp(f.read(), quality=quality, lossless=lossless)

    # Ensure destination dir exists
    os.makedirs(os.path.dirname(dst_path) or ".", exist_ok=True)
    with open(dst_path, "wb") as f:
        f.write(data)

    return dst_path


def batch_convert_folder(folder: str, extensions=None, quality: int = 85, lossless: bool = False) -> int:
    """Convertit en masse les images d'un dossier en WebP. Retourne le nombre de fichiers convertis."""
    if extensions is None:
        extensions = {'.jpg', '.jpeg', '.png', '.tif', '.tiff', '.bmp'}
    count = 0
    for root, _, files in os.walk(folder):
        for fn in files:
            if os.path.splitext(fn)[1].lower() in extensions:
                src = os.path.join(root, fn)
                dst = os.path.splitext(src)[0] + '.webp'
                try:
                    convert_file_to_webp(src, dst_path=dst, quality=quality, lossless=lossless)
                    count += 1
                except Exception:
                    # ignore individual failures
                    continue
    return count
