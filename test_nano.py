import openai, base64, re
from pathlib import Path
from PIL import Image, ImageDraw

client = openai.OpenAI(base_url='https://toapis.com/v1', api_key='sk-KxA6EKkekz8d4nKEFvxDE7x4ymufPVCWLk04iPM1YQf0bbkm')

sweater = next(f for f in Path('templates/01毛衣颜色').iterdir() if f.suffix=='.jpg' and f.stem != 'Thumbs')
yarn = next(f for f in Path('templates/04名字毛线颜色/单色名字').iterdir() if f.suffix=='.jpg' and f.stem != 'Thumbs')
style = Path('templates/03名字刺绣样式参考.jpg')

img = Image.new('RGB', (600, 200), (255, 255, 255))
ImageDraw.Draw(img).text((50, 40), 'Emma', fill=(0, 0, 0))
img.save('temp_output/test_font.jpg')

def b64(p):
    with open(p, 'rb') as f:
        return base64.b64encode(f.read()).decode()

print(f'毛衣: {sweater.name}, 毛线: {yarn.name}')
print('发送请求 (nano_banana_2)...')

resp = client.chat.completions.create(
    model='nano_banana_2',
    messages=[{'role': 'user', 'content': [
        {'type': 'image_url', 'image_url': {'url': f'data:image/jpeg;base64,{b64(sweater)}'}},
        {'type': 'image_url', 'image_url': {'url': f'data:image/jpeg;base64,{b64("temp_output/test_font.jpg")}'}},
        {'type': 'image_url', 'image_url': {'url': f'data:image/jpeg;base64,{b64(style)}'}},
        {'type': 'image_url', 'image_url': {'url': f'data:image/jpeg;base64,{b64(yarn)}'}},
        {'type': 'text', 'text': '在毛衣上添加刺绣名字Emma'},
    ]}],
    max_tokens=4096
)

raw = resp.choices[0].message.content
print(f'响应长度: {len(raw)}')
print(f'前200字: {raw[:200]}')
match = re.search(r'data:image/(\w+);base64,([A-Za-z0-9+/=]+)', raw)
if match:
    img_data = base64.b64decode(match.group(2))
    with open('temp_output/test_result.jpg', 'wb') as f:
        f.write(img_data)
    print('图片已保存到 temp_output/test_result.jpg')
else:
    print('未找到图片数据')
