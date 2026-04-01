"""
Etsy 刺绣名字生成工具 - nano_banana_2 版本
工作流程：
1. 输入名字 → PIL生成字体轨迹参考图（加粗11px，大小自适应）
2. 4张图喂给 nano_banana_2 生成效果
"""
import streamlit as st
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import base64
import re
import time
import json
from datetime import datetime

# --- 路径配置 ---
TEMPLATES_DIR = Path(__file__).parent / "templates"
SWEATER_DIR = TEMPLATES_DIR / "01毛衣颜色"
YARN_SINGLE_DIR = TEMPLATES_DIR / "04名字毛线颜色" / "单色名字"
YARN_MULTI_DIR = TEMPLATES_DIR / "04名字毛线颜色" / "彩色名字"
STYLE_REF = TEMPLATES_DIR / "03名字刺绣样式参考.jpg"
TEMP_DIR = Path(__file__).parent / "temp_output"
OUTPUT_DIR = Path(__file__).parent / "final_psd"
STATS_FILE = Path(__file__).parent / "generation_stats.json"
TEMP_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# PS模板路径
PS_TEMPLATE = Path(__file__).parent / "templates" / "05配饰合成" / "预览图配饰文件.psb"

# 自动查找 Photoshop 安装路径
def find_photoshop():
    """自动查找电脑上安装的 Photoshop"""
    import winreg
    
    # 常见安装位置
    ps_versions = [
        r"Adobe\Adobe Photoshop 2024",
        r"Adobe\Adobe Photoshop 2023",
        r"Adobe\Adobe Photoshop CC 2024",
        r"Adobe\Adobe Photoshop CC 2023",
        r"Adobe\Photoshop 2024",
        r"Adobe\Photoshop 2023",
    ]
    
    # 从注册表查找
    registry_paths = [
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\Photoshop.exe",
        r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\App Paths\Photoshop.exe",
    ]
    
    for reg_path in registry_paths:
        try:
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path)
            value, _ = winreg.QueryValueEx(key, "")
            ps_path = Path(value)
            if ps_path.exists():
                return ps_path
            winreg.CloseKey(key)
        except:
            pass
    
    # 从Program Files查找
    program_files = Path(r"C:\Program Files")
    for version in ps_versions:
        ps_path = program_files / version / "Photoshop.exe"
        if ps_path.exists():
            return ps_path
    
    program_files_x86 = Path(r"C:\Program Files (x86)")
    for version in ps_versions:
        ps_path = program_files_x86 / version / "Photoshop.exe"
        if ps_path.exists():
            return ps_path
    
    return None

# --- API配置 ---
# 每个 endpoint: (base_url, api_key, model, api_type)
# api_type: "openai" | "gemini_native"
ENDPOINTS = [
    ("https://www.moyu.info/v1beta",  "sk-beG2fn9bT0Ud1EhWHCq4hitQs7l0RIKC28bUFLvk8sbduELb", "gemini-3.1-flash-image-preview", "gemini_native"),
    ("https://api.linapi.net/v1",      "sk-lskP4c8hvfvi63ts3ZjdEXpZnGSEgScs9lUOrYquavYr5WMO", "gemini-3.1-flash-image-preview", "openai"),
    ("https://api.linapi.net/v1",      "sk-lskP4c8hvfvi63ts3ZjdEXpZnGSEgScs9lUOrYquavYr5WMO", "gemini-3-pro-image-preview",     "openai"),
    ("https://toapis.com/v1",          "sk-KxA6EKkekz8d4nKEFvxDE7x4ymufPVCWLk04iPM1YQf0bbkm", "nano_banana_2",                  "openai"),
    ("https://toapis.com/v1",          "sk-KxA6EKkekz8d4nKEFvxDE7x4ymufPVCWLk04iPM1YQf0bbkm", "nano-banana-2",                  "openai"),
    ("https://toapis.com/v1",          "sk-KxA6EKkekz8d4nKEFvxDE7x4ymufPVCWLk04iPM1YQf0bbkm", "gemini-2.5-flash-official",      "openai"),
    ("https://toapis.com/v1",          "sk-KxA6EKkekz8d4nKEFvxDE7x4ymufPVCWLk04iPM1YQf0bbkm", "gemini-3-flash-official",        "openai"),
    ("https://toapis.com/v1",          "sk-KxA6EKkekz8d4nKEFvxDE7x4ymufPVCWLk04iPM1YQf0bbkm", "gemini-2.5-pro-official",        "openai"),
]

# 字体路径
FONT_PATH = str(Path(__file__).parent / "fonts" / "PlaywriteHR-Regular.ttf")

# --- 单色提示词 ---
PROMPT_SINGLE = """我想为我的儿童毛衣（我第一张附上了我的产品图）立刻生成一张带有定制刺绣名字的的预览图。它需要按照我提供的第二张参考图的字体基础笔画走向来作为刺绣轨迹，每个定制名字的编织效果都要参考第三张参考图上的这种——立体宽松的链式针法绣制的辫子状名字刺绣的毛线编织效果。定制名字需要根据参考图图一的毛衣纹理走向来缝制，整体要求每个定制名字在产品图上的显示效果都尽量最优显示，定制名字在毛衣的两侧要留有一些空白，不要把胸前位置占满，以达到给予客户良好预览效果的最终目的。请注意，接下来是我对这个毛衣定制名字预览图核心重点强调的关键：
1、要继续保持产品图上毛衣的颜色、形态和图片背景；
2、要继续保留毛衣的垂直罗纹编织的毛衣纹理；
3、定制名字的刺绣编织走向要完全按照参考图二的字体基础笔画走向来编织，同时名字的展示角度要跟随参考图图一的毛衣纹理；
4、确保每个定制名字的刺绣技法都是图三这种立体宽松的链式针法绣制的辫子状名字刺绣的毛线编织效果。
5、确保每个刺绣名字字母的毛线颜色都是参考图四中的毛线颜色。
6、最终图片输出结果为2000*2000px像素的方形展示效果，保留原产品图在整体画面中占据的比例不变。
切记：图一是我的产品图，需要在这个产品图上生成定制名字的预览效果，图二是我以便于你理解提供的定制名字的字体走向轨迹的参考图，图三是定制名字的刺绣毛线编制效果图，图四是定制名字的毛线颜色参考图。"""

# --- 彩色提示词 ---
PROMPT_MULTI = """我想为我的儿童毛衣（我第一张附上了我的产品图）立刻生成一张带有定制刺绣名字的的预览图。它需要按照我提供的第二张参考图的字体基础笔画走向来作为刺绣轨迹，每个定制名字的编织效果都要参考第三张参考图上的这种——立体宽松的链式针法绣制的辫子状名字刺绣的毛线编织效果。定制名字需要根据参考图图一的毛衣纹理走向来缝制，整体要求每个定制名字在产品图上的显示效果都尽量最优显示，定制名字在毛衣的两侧要留有一些空白，不要把胸前位置占满，以达到给予客户良好预览效果的最终目的。请注意，接下来是我对这个毛衣定制名字预览图核心重点强调的关键：
1、要继续保持产品图上毛衣的颜色、形态和图片背景；
2、要继续保留毛衣的垂直罗纹编织的毛衣纹理；
3、定制名字的刺绣编织走向要完全按照参考图二的字体基础笔画走向来编织，同时名字的展示角度要跟随参考图图一的毛衣纹理；
4、确保每个定制名字的刺绣技法都是图三这种立体宽松的链式针法绣制的辫子状名字刺绣的毛线编织效果。
5、确保每个刺绣名字单个字母的毛线颜色都是参考图四中的毛线颜色。参考图四中有多个颜色，按照定制名字中依次的一个字母一个颜色的从前往后依次排序，如果出现名字单词字母多，则在图四颜色依次排完的情况下，从颜色的起始位置再依次排序。
6、最终图片输出结果为2000*2000px像素的方形展示效果，保留原产品图在整体画面中占据的比例不变。
切记：图一是我的产品图，需要在这个产品图上生成定制名字的预览效果，图二是我以便于你理解提供的定制名字的字体走向轨迹的参考图，图三是定制名字的刺绣毛线编制效果图，图四是定制名字的毛线颜色参考图。"""


def load_stats():
    """加载统计数据"""
    if STATS_FILE.exists():
        with open(STATS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"total": 0, "success": 0, "failed": 0, "records": []}


def save_stats(stats):
    """保存统计数据"""
    with open(STATS_FILE, 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)


def add_record(name, success, yarn_type, has_accessory=False):
    """添加生成记录"""
    stats = load_stats()
    stats["total"] += 1
    if success:
        stats["success"] += 1
    else:
        stats["failed"] += 1
    
    stats["records"].insert(0, {
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "name": name,
        "success": success,
        "yarn_type": yarn_type,
        "has_accessory": has_accessory
    })
    # 只保留最近100条记录
    stats["records"] = stats["records"][:100]
    save_stats(stats)


def get_sweater_colors():
    return [f.stem for f in SWEATER_DIR.glob("*.jpg")]


def get_yarn_colors(folder: Path):
    files = [f for f in folder.iterdir() if f.suffix.lower() in (".jpg", ".png")]
    # 按A1-A24数字顺序排序
    def sort_key(f):
        import re
        match = re.match(r'A(\d+)', f.stem)
        if match:
            return int(match.group(1))
        return 0
    return sorted(files, key=sort_key)


def generate_name_image(name: str) -> Path:
    """用PIL生成名字字体轨迹参考图（加粗11px，大小自适应）"""
    # 根据名字长度确定字体大小
    name_len = len(name)
    if name_len <= 4:
        font_size = 300
    elif name_len <= 6:
        font_size = 250
    elif name_len <= 8:
        font_size = 200
    else:
        font_size = 150
    
    # 创建2000x2000白色画布
    img = Image.new("RGB", (2000, 2000), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    
    try:
        font = ImageFont.truetype(FONT_PATH, font_size)
    except:
        font = ImageFont.load_default()
    
    # 获取文字边界
    bbox = draw.textbbox((0, 0), name, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    # 计算居中位置
    x = (2000 - text_width) // 2 - bbox[0]
    y = (2000 - text_height) // 2 - bbox[1]
    
    # 加粗效果：绘制多层文字偏移
    stroke_width = 11  # 加粗11像素
    
    # 多层叠加实现加粗效果
    for dx in range(-stroke_width, stroke_width + 1):
        for dy in range(-stroke_width, stroke_width + 1):
            if dx * dx + dy * dy <= stroke_width * stroke_width:
                draw.text((x + dx, y + dy), name, fill=(0, 0, 0), font=font)
    
    # 最后绘制一层确保中心清晰
    draw.text((x, y), name, fill=(0, 0, 0), font=font)
    
    out_path = TEMP_DIR / f"{name}_font_ref.jpg"
    img.save(str(out_path), "JPEG", quality=95)
    return out_path


# 记录上次成功的 endpoint，下次优先使用
_last_successful_endpoint = None


def generate_embroidery(sweater_path, name_image_path, yarn_path, prompt, log) -> Path | None:
    """逐个尝试模型列表，直到成功生成刺绣预览；上次成功的模型优先"""
    global _last_successful_endpoint

    def b64img(path):
        with open(path, 'rb') as f:
            return base64.b64encode(f.read()).decode('utf-8')

    log.write(f"  图1 (产品图): {sweater_path.name}")
    log.write(f"  图2 (字体参考): {name_image_path.name}")
    log.write(f"  图3 (刺绣样式): {STYLE_REF.name}")
    log.write(f"  图4 (毛线颜色): {yarn_path.name}")

    from openai import OpenAI
    import urllib.request

    content_openai = [
        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64img(sweater_path)}"}},
        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64img(name_image_path)}"}},
        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64img(STYLE_REF)}"}},
        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64img(yarn_path)}"}},
        {"type": "text", "text": prompt},
    ]

    content_gemini_native = [
        {"inline_data": {"mime_type": "image/jpeg", "data": b64img(sweater_path)}},
        {"inline_data": {"mime_type": "image/jpeg", "data": b64img(name_image_path)}},
        {"inline_data": {"mime_type": "image/jpeg", "data": b64img(STYLE_REF)}},
        {"inline_data": {"mime_type": "image/jpeg", "data": b64img(yarn_path)}},
        {"text": prompt},
    ]

    # 上次成功的排最前，其余顺序不变
    if _last_successful_endpoint and _last_successful_endpoint in ENDPOINTS:
        ordered = [_last_successful_endpoint] + [e for e in ENDPOINTS if e != _last_successful_endpoint]
        log.write(f"⭐ 优先使用上次成功: {_last_successful_endpoint[2]}")
    else:
        ordered = ENDPOINTS

    for base_url, api_key, model, api_type in ordered:
        log.write(f"\n🚀 尝试: {model} ({api_type})")
        try:
            t0 = time.time()
            raw = None

            if api_type == "gemini_native":
                import json as _json
                url = f"{base_url}/models/{model}:generateContent"
                payload = _json.dumps({"contents": [{"role": "user", "parts": content_gemini_native}]}).encode()
                req = urllib.request.Request(url, data=payload, headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}"
                })
                import socket as _socket
                _socket.setdefaulttimeout(180)
                with urllib.request.urlopen(req) as r:
                    resp_data = _json.loads(r.read().decode())
                parts = resp_data["candidates"][0]["content"]["parts"]
                for part in parts:
                    if "inlineData" in part:
                        fmt = part["inlineData"]["mimeType"].split("/")[1]
                        img_data = base64.b64decode(part["inlineData"]["data"])
                        elapsed = time.time() - t0
                        log.write(f"⏱️ 耗时: {elapsed:.1f}秒")
                        output_path = OUTPUT_DIR / f"{name_image_path.stem.replace('_font_ref', '')}_{sweater_path.stem}.{fmt}"
                        with open(output_path, 'wb') as f:
                            f.write(img_data)
                        log.write(f"✅ 图片已保存: {output_path.name}")
                        _last_successful_endpoint = (base_url, api_key, model, api_type)
                        return output_path
                elapsed = time.time() - t0
                log.write(f"⏱️ 耗时: {elapsed:.1f}秒")
                text_parts = [p.get("text", "") for p in parts if "text" in p]
                log.write(f"❌ 响应中未找到图片数据，尝试下一个")
                log.write(f"响应内容(前200字): {''.join(text_parts)[:200]}")

            else:  # openai
                client = OpenAI(base_url=base_url, api_key=api_key)
                response = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": content_openai}],
                    max_tokens=4096
                )
                elapsed = time.time() - t0
                log.write(f"⏱️ 耗时: {elapsed:.1f}秒")
                raw = response.choices[0].message.content
                match = re.search(r'data:image/(\w+);base64,([A-Za-z0-9+/=]+)', raw)
                if match:
                    fmt = match.group(1)
                    img_data = base64.b64decode(match.group(2))
                    output_path = OUTPUT_DIR / f"{name_image_path.stem.replace('_font_ref', '')}_{sweater_path.stem}.{fmt}"
                    with open(output_path, 'wb') as f:
                        f.write(img_data)
                    log.write(f"✅ 图片已保存: {output_path.name}")
                    _last_successful_endpoint = (base_url, api_key, model, api_type)
                    return output_path
                else:
                    log.write(f"❌ 响应中未找到图片数据，尝试下一个")
                    log.write(f"响应内容(前200字): {raw[:200]}")

        except Exception as e:
            log.write(f"❌ {model} 失败: {e}，尝试下一个")

    log.write("❌ 所有接口均失败")
    return None


def is_photoshop_running():
    """检测PS是否正在运行"""
    import subprocess
    try:
        result = subprocess.run(
            ['powershell', '-Command', 
             "Get-Process -Name 'Photoshop' -ErrorAction SilentlyContinue | Select-Object -First 1"],
            capture_output=True, text=True
        )
        return 'Photoshop' in result.stdout
    except:
        return False


def check_template_open():
    """检测模板文件是否已在PS中打开"""
    import subprocess
    
    jsx_check = '''
if (app.documents.length > 0) {
    var found = false;
    for (var i = 0; i < app.documents.length; i++) {
        if (app.documents[i].fullName.toString().indexOf("预览图配饰文件") != -1) {
            found = true;
            break;
        }
    }
    if (found) {
        alert("TEMPLATE_OPEN");
    } else {
        alert("TEMPLATE_CLOSED");
    }
} else {
    alert("NO_DOCUMENT");
}
'''
    
    script_path = Path(__file__).parent / "check_template.jsx"
    with open(script_path, 'w', encoding='utf-8') as f:
        f.write(jsx_check)
    
    try:
        result = subprocess.run(
            ['powershell', '-Command', 
             f"& 'C:\\Program Files\\Adobe\\Adobe Photoshop 2024\\Photoshop.exe' -s '{script_path}'"],
            capture_output=True, text=True, timeout=10
        )
        return "TEMPLATE_OPEN" in result.stdout
    except:
        return False


def click_ps_dialog(log):
    """自动点击Photoshop弹窗"""
    import subprocess
    import time
    import threading
    import os
    
    def click_loop():
        try:
            # 创建独立的PowerShell脚本来自动点击
            script_content = '''
Add-Type -AssemblyName System.Windows.Forms

# 等待并循环点击
for ($i = 0; $i -lt 40; $i++) {
    # 发送 Y 键点击"是"按钮
    [System.Windows.Forms.SendKeys]::SendWait("y")
    Start-Sleep -Milliseconds 150
    
    # 发送 Enter 点击确定
    [System.Windows.Forms.SendKeys]::SendWait("{ENTER}")
    Start-Sleep -Milliseconds 150
    
    Start-Sleep -Milliseconds 400
}
'''
            # 保存脚本到临时文件
            script_path = os.path.join(os.environ['TEMP'], 'auto_click_ps.ps1')
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(script_content)
            
            # 启动
            subprocess.Popen([
                'powershell', 
                '-ExecutionPolicy', 'Bypass', 
                '-WindowStyle', 'Hidden',
                '-File', script_path
            ], shell=True)
            
        except Exception as e:
            pass
    
    # 启动点击线程
    t = threading.Thread(target=click_loop, daemon=True)
    t.start()


def open_ps_with_image(image_path: Path, log):
    """打开PS并将图片放入配饰图层文件夹"""
    import subprocess
    import time
    import threading
    
    log.write("🔍 正在查找 Photoshop...")
    
    # 查找PS路径
    ps_path = find_photoshop()
    
    if not ps_path:
        log.write("❌ 未找到 Photoshop，请确认已安装")
        st.error("未找到 Photoshop，请确认已安装")
        return
    
    log.write(f"✅ 找到 Photoshop: {ps_path.name}")
    
    # 检测PS是否已运行
    ps_running = is_photoshop_running()
    log.write(f"📊 PS运行状态: {'已运行' if ps_running else '未运行'}")
    
    # 模板和图片路径 - 使用正斜杠和转义
    template_path_str = str(PS_TEMPLATE).replace("\\", "/")
    img_path_str = str(image_path).replace("\\", "/")
    
    # JSX脚本 - 删除旧预览图层，新图放在配饰文件夹外面
    jsx_script = f'''
// 图片和模板路径
var imgFile = new File("{img_path_str}");
var templatePath = "{template_path_str}";

// 查找模板
var targetDoc = null;
for (var i = 0; i < app.documents.length; i++) {{
    var docName = app.documents[i].name;
    if (docName.indexOf("\\u9884\\u89c8\\u56fe\\u914d\\u9970\\u6587\\u4ef6") != -1) {{
        targetDoc = app.documents[i];
        break;
    }}
}}

if (targetDoc) {{
    app.activeDocument = targetDoc;
    
    var group = null;
    for (var i = 0; i < targetDoc.layerSets.length; i++) {{
        var groupName = targetDoc.layerSets[i].name;
        if (groupName.indexOf("\\u914d\\u9970") != -1) {{
            group = targetDoc.layerSets[i];
            break;
        }}
    }}
    
    // 删除旧的"预览"图层（在文档顶层）
    for (var i = targetDoc.artLayers.length - 1; i >= 0; i--) {{
        if (targetDoc.artLayers[i].name == "\\u9884\\u89c8") {{
            targetDoc.artLayers[i].remove();
        }}
    }}
    
    // 打开并复制新图片
    var imgDoc = app.open(imgFile);
    imgDoc.activeLayer.copy();
    imgDoc.close(SaveOptions.DONOTSAVECHANGES);
    
    // 在文档顶部创建新图层（配饰文件夹外面）
    targetDoc.artLayers.add();
    targetDoc.activeLayer.name = "\\u9884\\u89c8";
    app.activeDocument.paste();
    
    // 如果有配饰文件夹，把预览图层移到配饰文件夹下面
    if (group) {{
        var groupIndex = -1;
        for (var i = 0; i < targetDoc.layers.length; i++) {{
            if (targetDoc.layers[i] == group) {{
                groupIndex = i;
                break;
            }}
        }}
        if (groupIndex > 0) {{
            // 移动到配饰文件夹下面
            activeDocument.activeLayer.move(group, ElementPlacement.PLACEAFTER);
        }}
    }}
    
    alert("OK");
}} else {{
    var doc = app.open(new File(templatePath));
    var group = null;
    for (var i = 0; i < doc.layerSets.length; i++) {{
        var groupName = doc.layerSets[i].name;
        if (groupName.indexOf("\\u914d\\u9970") != -1) {{
            group = doc.layerSets[i];
            break;
        }}
    }}
    
    // 删除旧的"预览"图层
    for (var i = doc.artLayers.length - 1; i >= 0; i--) {{
        if (doc.artLayers[i].name == "\\u9884\\u89c8") {{
            doc.artLayers[i].remove();
        }}
    }}
    
    // 打开并复制新图片
    var imgDoc = app.open(imgFile);
    imgDoc.activeLayer.copy();
    imgDoc.close(SaveOptions.DONOTSAVECHANGES);
    
    // 在文档顶部创建新图层
    doc.artLayers.add();
    doc.activeLayer.name = "\\u9884\\u89c8";
    doc.paste();
    
    // 移到配饰文件夹下面
    if (group) {{
        activeDocument.activeLayer.move(group, ElementPlacement.PLACEAFTER);
    }}
    
    alert("OK");
}}
'''
    
    # 保存JSX脚本 - 使用UTF-8 with BOM确保PS能正确识别
    script_path = Path(__file__).parent / "temp_ps_script.jsx"
    with open(script_path, 'w', encoding='utf-8-sig') as f:
        f.write(jsx_script)
    
    log.write(f"📜 脚本已保存: {script_path.name}")
    
    # 启动后台线程自动点击PS弹窗
    threading.Thread(target=click_ps_dialog, args=(log,), daemon=True).start()
    
    try:
        if ps_running:
            # PS已运行：直接执行脚本
            log.write("🎨 PS已运行，执行脚本...")
            subprocess.Popen([
                str(ps_path),
                str(script_path)
            ], shell=True)
        else:
            # PS未运行：先打开模板，等待，再执行脚本
            log.write("🎨 正在启动 Photoshop...")
            subprocess.Popen([str(ps_path), str(PS_TEMPLATE)], shell=True)
            
            log.write("⏳ 等待 Photoshop 启动...")
            time.sleep(10)
            
            log.write("📜 执行脚本...")
            subprocess.Popen([
                str(ps_path),
                str(script_path)
            ], shell=True)
        
        log.write("✅ 请查看 Photoshop 中的弹窗提示")
        
    except Exception as e:
        log.write(f"❌ 错误: {e}")
        st.error(f"错误: {e}")


# ===================== UI =====================
st.set_page_config(page_title="🧶 Etsy 刺绣预览生成器", layout="centered")
st.title("🧶 Etsy 刺绣名字预览生成器")
st.markdown("**使用 nano_banana_2 · 自动生成字体参考图**")

# 显示统计数据
stats = load_stats()
col1, col2, col3 = st.columns(3)
col1.metric("总生成", stats["total"])
col2.metric("成功", stats["success"])
col3.metric("失败", stats["failed"])

# 1. 名字输入
name = st.text_input("输入刺绣名字（如 Emma）", placeholder="Emma").strip()

# 2. 毛衣颜色
sweater_colors = get_sweater_colors()
sweater_color = st.selectbox("选择毛衣颜色", sweater_colors) if sweater_colors else None

if sweater_color:
    sweater_path = SWEATER_DIR / f"{sweater_color}.jpg"
    st.success(f"✓ 毛衣文件: {sweater_path.name}")

# 3. 毛线颜色类型
yarn_type = st.radio("毛线颜色类型", ["单色名字", "彩色名字"])

if yarn_type == "单色名字":
    yarn_folder = YARN_SINGLE_DIR
    prompt = PROMPT_SINGLE
else:
    yarn_folder = YARN_MULTI_DIR
    prompt = PROMPT_MULTI

yarn_files = get_yarn_colors(yarn_folder)
yarn_names = [f.stem for f in yarn_files]
selected_yarn_name = st.selectbox("选择毛线颜色", yarn_names) if yarn_names else None
selected_yarn_path = next((f for f in yarn_files if f.stem == selected_yarn_name), None)

if selected_yarn_path:
    st.success(f"✓ 毛线颜色: {selected_yarn_path.name}")
    with Image.open(selected_yarn_path) as im:
        st.image(im, width=100)

# 4. 是否有配件
has_accessory = st.checkbox("☑️ 是否有配件（打开PS合成）")

# 实时检测PS状态
current_ps_running = is_photoshop_running()
if "ps_was_open" not in st.session_state:
    st.session_state.ps_was_open = current_ps_running

if has_accessory:
    st.info(f"将自动打开 PS 并将生成图放入配饰图层\n模板: {PS_TEMPLATE.name}")
    
    # 显示PS状态
    if current_ps_running:
        st.success("🟢 Photoshop 正在运行")
    else:
        st.warning("⚪ Photoshop 未运行")

if has_accessory:
    st.info(f"将自动打开 PS 并将生成图放入配饰图层\n模板: {PS_TEMPLATE.name}")

# 5. 说明
st.divider()
st.markdown("""
### 📋 工作流程

1. 输入名字 → **自动生成加粗字体轨迹参考图**（11px加粗，大小自适应）
2. 4张参考图喂给 nano_banana_2
3. 模型直接生成刺绣预览效果

**注意**: 处理时间约30-60秒，请耐心等待。
""")

# 6. 生成按钮
st.divider()
if st.button("🎨 开始生成", type="primary", use_container_width=True):
    if not name:
        st.error("请输入名字")
        st.stop()
    if not sweater_color:
        st.error("请选择毛衣颜色")
        st.stop()
    if not selected_yarn_path:
        st.error("请选择毛线颜色")
        st.stop()
    
    sweater_img = SWEATER_DIR / f"{sweater_color}.jpg"
    
    progress = st.progress(0, text="准备中...")
    log = st.status("运行日志", expanded=True)
    
    # 步骤1: 生成字体参考图
    progress.progress(20, text="步骤 1/2: 生成加粗字体轨迹参考图...")
    log.write("**步骤 1/2** 生成加粗字体轨迹参考图（11px加粗，大小自适应）...")
    name_image_path = generate_name_image(name)
    log.write(f"✅ 字体参考图已生成: {name_image_path.name}")
    st.image(str(name_image_path), caption=f"{name} 字体参考", width=200)
    
    # 步骤2: 调用nano_banana_2
    progress.progress(40, text="步骤 2/2: 调用 nano_banana_2...")
    log.write(f"**步骤 2/2** 使用 {'单色' if yarn_type == '单色名字' else '彩色'} 提示词...")
    
    result = generate_embroidery(sweater_img, name_image_path, selected_yarn_path, prompt, log)
    
    if result and result.exists():
        progress.progress(80, text="保存到日期文件夹...")
        
        # 创建按日期的输出文件夹
        today = datetime.now().strftime("%Y-%m-%d")
        date_dir = OUTPUT_DIR / today
        date_dir.mkdir(exist_ok=True)
        
        # 文件名：刺绣名字 + 原文件名
        final_name = f"{name}_{result.name}"
        final_path = date_dir / final_name
        
        # 复制到日期文件夹
        import shutil
        shutil.copy2(result, final_path)
        log.write(f"✅ 已保存到日期文件夹: {final_path.relative_to(OUTPUT_DIR)}")
        
        # 如果有配件，打开PS
        if has_accessory:
            progress.progress(90, text="打开 Photoshop...")
            open_ps_with_image(final_path, log)
        
        progress.progress(100, text="完成!")
        log.update(label="✅生成完成", state="complete", expanded=False)
        
        st.success(f"图片已生成: {final_path.relative_to(OUTPUT_DIR)}")
        st.image(str(final_path), caption="刺绣预览效果", width=400)
        
        # 更新统计
        add_record(name, True, yarn_type, has_accessory)
        
        # 下载按钮
        with open(final_path, "rb") as f:
            st.download_button("📥 下载图片", f, file_name=final_name, mime="image/jpeg")
    else:
        log.update(label="❌ 生成失败", state="error", expanded=True)
        st.error("生成失败，请查看日志")
        
        # 更新统计
        add_record(name, False, yarn_type, has_accessory)

# 显示最近生成记录
st.divider()
st.markdown("### 📊 最近生成记录")
records = load_stats()["records"][:10]
if records:
    for r in records:
        status_icon = "✅" if r["success"] else "❌"
        accessory_text = " +配件" if r.get("has_accessory") else ""
        st.write(f"{status_icon} {r['time']} | {r['name']} | {r['yarn_type']}{accessory_text}")
else:
    st.info("暂无生成记录")
