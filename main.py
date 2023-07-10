import yaml
import aiofiles
import aiohttp
import shelve
from PIL import Image
import asyncio
import os

BUCKET_NAME = "xtol.dev"
BASE_URL = f"https://{BUCKET_NAME}.s3.wasabisys.com"
IMAGE_SIZES = [(200, "small"), (500, "medium"), (800, "large")]

async def upload_file_to_wasabi(filepath, key):
    async with aiofiles.open(filepath, mode='rb') as f:
        file_content = await f.read()
    async with aiohttp.ClientSession() as session:
        async with session.put(f"{BASE_URL}/{key}", data=file_content) as resp:
            return resp.status

async def resize_image(filepath, sizes):
    basename = os.path.basename(filepath)
    name, ext = os.path.splitext(basename)
    try:
        with Image.open(filepath) as img:
            entries = []
            new_filename = f"{name}_orig{ext}"
            new_filepath = os.path.join(os.path.dirname(filepath), new_filename)
            url = await upload_file_to_wasabi(new_filepath, f"images/{new_filename}")
            entry = {"size": "orig", "filename": new_filename, "url": url, "width": img.width, "height": img.height}
            entries.append(entry)
            for size, label in sizes:
                new_filename = f"{name}_{label}{ext}"
                new_filepath = os.path.join(os.path.dirname(filepath), new_filename)
                img.thumbnail((size, size))
                img.save(new_filepath, "JPEG")
                url = await upload_file_to_wasabi(new_filepath, f"images/{new_filename}")
                entry = {"size": label, "filename": new_filename, "url": url, "width": img.width, "height": img.height}
                entries.append(entry)
            return entries
    except Exception as e:
        return [{"error": str(e)}]

async def process_media(directory):
    db = shelve.open('media.db')
    for root, dirs, files in os.walk(directory):
        for name in files:
            filepath = os.path.join(root, name)
            if name.lower().endswith(('.png', '.jpg', '.jpeg')):
                entries = await resize_image(filepath, IMAGE_SIZES)
                db[name] = entries
    with open("media.yaml", "w") as f:
        yaml.dump(dict(db), f)

    db.close()

if __name__ == "__main__":
    asyncio.run(process_media("./media"))

