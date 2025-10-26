from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from rembg import remove
from PIL import Image
import io, zipfile, os, uvicorn

app = FastAPI()

# ✅ Allow frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update with your frontend URL if needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def remove_bg_hd(image_bytes: bytes) -> bytes:
    """Remove background and upscale image for HD output"""
    img = Image.open(io.BytesIO(image_bytes))
    width, height = img.size
    img = img.resize((width * 2, height * 2), Image.LANCZOS)  # 2x upscale for HD
    output = remove(img)
    buf = io.BytesIO()
    output.save(buf, format="PNG")
    return buf.getvalue()

@app.post("/remove-bg")
async def remove_background(
    images: list[UploadFile] = File(...),
    enhance: bool = Form(False)  # Optional frontend toggle
):
    if not images:
        return {"error": "No images uploaded"}

    results = []

    for image in images:
        try:
            input_bytes = await image.read()
            output_bytes = remove_bg_hd(input_bytes)

            # Optional AI enhancement (placeholder)
            # if enhance:
            #     output_bytes = enhance_image(output_bytes)

            results.append((image.filename, output_bytes))
        except Exception as e:
            print(f"Error processing {image.filename}: {e}")

    # ✅ Single image → return PNG
    if len(results) == 1:
        filename, data = results[0]
        return Response(
            content=data,
            media_type="image/png",
            headers={"Content-Disposition": f'attachment; filename="{filename.rsplit(".",1)[0]}-no-bg.png"'}
        )

    # ✅ Multiple images → return ZIP
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zipf:
        for name, data in results:
            clean_name = name.rsplit(".", 1)[0] + "-no-bg.png"
            zipf.writestr(clean_name, data)
    zip_buffer.seek(0)

    return Response(
        content=zip_buffer.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="processed_images.zip"'}
    )

# ✅ Render-friendly startup
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
