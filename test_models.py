"""测试哪些模型支持图片生成输出"""
import openai, base64, re
from pathlib import Path
from PIL import Image, ImageDraw

client = openai.OpenAI(base_url='https://toapis.com/v1', api_key='sk-KxA6EKkekz8d4nKEFvxDE7x4ymufPVCWLk04iPM1YQf0bbkm')

# 简单测试图
img = Image.new('RGB', (200, 100), (255, 255, 255))
ImageDraw.Draw(img).text((10, 30), 'Emma', fill=(0, 0, 0))
img.save('temp_output/model_test.jpg')

def b64(p):
    with open(p, 'rb') as f:
        return base64.b64encode(f.read()).decode()

models_to_test = [
    'gemini-2.5-flash-official',
    'gemini-2.5-pro-official',
    'gemini-3-flash-official',
    'gemini-3.1-flash-lite-preview-official',
    'gemini-3.1-pro',
]

for model in models_to_test:
    print(f'\n测试 {model}...')
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[{'role': 'user', 'content': [
                {'type': 'image_url', 'image_url': {'url': f'data:image/jpeg;base64,{b64("temp_output/model_test.jpg")}'}},
                {'type': 'text', 'text': '请在这张图片上的文字旁边画一个红色圆圈，并返回修改后的图片'},
            ]}],
            max_tokens=2000
        )
        raw = resp.choices[0].message.content
        has_img = bool(re.search(r'data:image/\w+;base64,', raw))
        print(f'  响应长度: {len(raw)}, 含图片: {has_img}')
        print(f'  前100字: {raw[:100]}')
    except Exception as e:
        print(f'  错误: {e}')
