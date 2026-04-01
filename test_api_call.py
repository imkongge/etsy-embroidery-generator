"""Quick API test - sends 4 images to nano-banana-2 and prints raw response"""
import base64, time, sys
from pathlib import Path
from openai import OpenAI
from PIL import Image, ImageDraw, ImageFont

API_BASE_URL = "https://toapis.com/v1"
API_KEY = "sk-KxA6EKkekz8d4nKEFvxDE7x4ymufPVCWLk04iPM1YQf0bbkm"
MODEL = "nano_banana_2"

TEMPLATES_DIR = Path(__file__).parent / "templates"
SWEATER_DIR = TEMPLATES_DIR / "01毛衣颜色"
YARN_SINGLE_DIR = TEMPLATES_DIR / "04名字毛线颜色" / "单色名字"
STYLE_REF = TEMPLATES_DIR / "03名字刺绣样式参考.jpg"
TEMP_DIR = Path(__file__).parent / "temp_output"
TEMP_DIR.mkdir(exist_ok=True)

# Pick first available sweater and yarn images
sweater_path = next(f for f in SWEATER_DIR.iterdir() if f.suffix.lower() in ('.jpg','.jpeg','.png') and f.stem != 'Thumbs')
yarn_path = next(f for f in YARN_SINGLE_DIR.iterdir() if f.suffix.lower() in ('.jpg','.jpeg','.png') and f.stem != 'Thumbs')
print(f"Sweater: {sweater_path.name}")
print(f"Yarn:    {yarn_path.name}")
print(f"Style:   {STYLE_REF.name}")

# Generate font reference image for name "Emma"
name = "Emma"
FONT_PATH = "C:/Users/Administrator/AppData/Local/Microsoft/Windows/Fonts/PlaywriteHR-Regular.ttf"
try:
    font = ImageFont.truetype(FONT_PATH, 120)
except:
    font = ImageFont.load_default()

img = Image.new('RGB', (600, 200), color=(255, 255, 255))
draw = ImageDraw.Draw(img)
draw.text((50, 40), name, fill=(0, 0, 0), font=font)
font_ref_path = TEMP_DIR / "Emma_font_ref.jpg"
img.save(str(font_ref_path), "JPEG", quality=95)
print(f"Font ref: {font_ref_path.name}")

PROMPT = """我想为我的儿童毛衣（我第一张附上了我的产品图）立刻生成一张带有定制刺绣名字的的预览图。它需要按照我提供的第二张参考图的字体基础笔画走向来作为刺绣轨迹，每个定制名字的编织效果都要参考第三张参考图上的这种——立体宽松的链式针法绣制的辫子状名字刺绣的毛线编织效果。定制名字需要根据参考图图一的毛衣纹理走向来缝制，整体要求每个定制名字在产品图上的显示效果都尽量最优显示，定制名字在毛衣的两侧要留有一些空白，不要把胸前位置占满，以达到给予客户良好预览效果的最终目的。请注意，接下来是我对这个毛衣定制名字预览图核心重点强调的关键：
1、要继续保持产品图上毛衣的颜色、形态和图片背景；
2、要继续保留毛衣的垂直罗纹编织的毛衣纹理；
3、定制名字的刺绣编织走向要完全按照参考图二的字体基础笔画走向来编织，同时名字的展示角度要跟随参考图图一的毛衣纹理；
4、确保每个定制名字的刺绣技法都是图三这种立体宽松的链式针法绣制的辫子状名字刺绣的毛线编织效果。
5、确保每个刺绣名字字母的毛线颜色都是参考图四中的毛线颜色。
6、最终图片输出结果为2000*2000px像素的方形展示效果，保留原产品图在整体画面中占据的比例不变。
切记：图一是我的产品图，需要在这个产品图上生成定制名字的预览效果，图二是我以便于你理解提供的定制名字的字体走向轨迹的参考图，图三是定制名字的刺绣毛线编制效果图，图四是定制名字的毛线颜色参考图。"""

def img_to_b64(path):
    with open(path, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')

content = [
    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_to_b64(sweater_path)}"}},
    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_to_b64(font_ref_path)}"}},
    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_to_b64(STYLE_REF)}"}},
    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_to_b64(yarn_path)}"}},
    {"type": "text", "text": PROMPT},
]

client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)
print("\nSending request...")
t0 = time.time()
try:
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": content}],
        max_tokens=4096
    )
    elapsed = time.time() - t0
    print(f"Response time: {elapsed:.1f}s")
    raw = response.choices[0].message.content
    print(f"\n--- RAW RESPONSE (first 2000 chars) ---")
    print(raw[:2000])
    print(f"\n--- Total length: {len(raw)} chars ---")

    # Check for image data
    if '![image](data:' in raw:
        print("\n✅ Image found in response!")
        import re
        match = re.search(r'data:image/(\w+);base64,([A-Za-z0-9+/=]+)', raw)
        if match:
            fmt = match.group(1)
            b64_data = match.group(2)
            img_data = base64.b64decode(b64_data)
            out = TEMP_DIR / f"test_output_{name}.{fmt}"
            with open(out, 'wb') as f:
                f.write(img_data)
            print(f"✅ Saved to: {out}")
    elif 'data:image' in raw:
        print("\n⚠️  Found data:image but not in expected markdown format")
        print("Searching for base64...")
        import re
        match = re.search(r'data:image/(\w+);base64,([A-Za-z0-9+/=]+)', raw)
        if match:
            fmt = match.group(1)
            b64_data = match.group(2)
            img_data = base64.b64decode(b64_data)
            out = TEMP_DIR / f"test_output_{name}.{fmt}"
            with open(out, 'wb') as f:
                f.write(img_data)
            print(f"✅ Saved to: {out}")
    else:
        print("\n❌ No image data detected in response")
        print("Full response:")
        print(raw)
except Exception as e:
    elapsed = time.time() - t0
    print(f"Error after {elapsed:.1f}s: {e}")
    import traceback
    traceback.print_exc()
