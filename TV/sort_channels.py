import requests
import re
import os

def load_source_urls():
    """从文件加载源地址列表"""
    source_path = "TV/sources.txt"
    urls = []

    if not os.path.exists(source_path):
        print(f"警告：未找到源地址文件 {source_path}，使用默认源")
        return ["https://live.fanmingming.com/tv/m3u/ipv6.m3u"]

    try:
        with open(source_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                # 跳过空行和注释
                if not line or line.startswith('#'):
                    continue
                # 只添加有效的URL
                if line.startswith('http'):
                    urls.append(line)
                    print(f"加载源地址: {line}")
    except Exception as e:
        print(f"读取源地址文件失败: {e}")
        return ["https://live.fanmingming.com/tv/m3u/ipv6.m3u"]

    if not urls:
        print("警告：源地址文件为空，使用默认源")
        return ["https://live.fanmingming.com/tv/m3u/ipv6.m3u"]

    return urls

def load_categories_from_template():
    """从模板文件加载分类和频道信息"""
    categories = {}
    current_category = None

    template_path = "TV/moban.txt"
    if not os.path.exists(template_path):
        print(f"错误：未找到模板文件 {template_path}")
        return categories

    try:
        with open(template_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                # 处理分类行
                if ",#genre#" in line:
                    current_category = line.split(",")[0].strip()
                    categories[current_category] = []
                # 处理频道行
                elif current_category:
                    channel = line.strip()
                    if channel:
                        categories[current_category].append(channel)
    except Exception as e:
        print(f"读取模板文件出错: {e}")

    return categories

def load_channel_mapping():
    """加载频道名称映射表"""
    mapping = {}
    mapping_path = "TV/channel_mapping.txt"
    if not os.path.exists(mapping_path):
        return mapping

    try:
        with open(mapping_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or "," not in line:
                    continue
                old_name, new_name = line.split(",", 1)
                mapping[old_name.strip()] = new_name.strip()
    except Exception as e:
        print(f"加载映射表失败: {e}")
    return mapping

def parse_m3u_to_txt(m3u_content):
    """解析M3U内容，返回(内容, 频道数)"""
    mapping = load_channel_mapping()
    lines = m3u_content.split('\\n')
    channels = {}
    current_group = '未分组'
    channel_count = 0

    for i in range(len(lines)):
        line = lines[i].strip()
        if line.startswith('#EXTINF:-1'):
            group_match = re.search(r'group-title="([^"]*)"', line)
            group = group_match.group(1) if group_match else current_group

            name_match = re.search(r'tvg-name="([^"]*)"', line)
            name = name_match.group(1) if name_match else line.split(',')[-1].strip()

            # 使用映射表标准化名称
            name = mapping.get(name, name)

            if i + 1 < len(lines):
                url = lines[i + 1].strip()
                if url and not url.startswith('#'):
                    if group not in channels:
                        channels[group] = []
                    channels[group].append(f"{name},{url}")
                    channel_count += 1
                    current_group = group

    txt_content = ""
    for group, channel_list in channels.items():
        txt_content += f"{group},#genre#\\n"
        txt_content += "\\n".join(channel_list) + "\\n\\n"
    return txt_content.strip(), channel_count

def parse_txt_content(txt_content):
    """解析TXT格式内容，返回(内容, 频道数)"""
    mapping = load_channel_mapping()
    lines = txt_content.split('\\n')
    channels = {}
    current_group = '未分组'
    channel_count = 0

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # 检测分类行
        if ",#genre#" in line:
            current_group = line.split(",")[0].strip()
            if current_group not in channels:
                channels[current_group] = []
        # 检测频道行 (格式: 频道名,URL)
        elif ',' in line and not line.startswith('#'):
            parts = line.split(',', 1)
            if len(parts) == 2:
                name = parts[0].strip()
                url = parts[1].strip()
                # 验证URL格式
                if url.startswith('http'):
                    # 使用映射表标准化名称
                    name = mapping.get(name, name)
                    if current_group not in channels:
                        channels[current_group] = []
                    channels[current_group].append(f"{name},{url}")
                    channel_count += 1

    # 转换为统一格式
    txt_content = ""
    for group, channel_list in channels.items():
        txt_content += f"{group},#genre#\\n"
        txt_content += "\\n".join(channel_list) + "\\n\\n"
    return txt_content.strip(), channel_count

def fetch_content(url):
    """从URL获取内容，自动识别格式并转换，返回(内容, 频道数)"""
    try:
        print(f"正在获取: {url}")

        # 设置请求头模拟浏览器
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        response = requests.get(url, timeout=15, headers=headers)
        response.raise_for_status()

        content = response.text

        # 自动检测内容格式
        if '#EXTM3U' in content or '#EXTINF' in content:
            print("  检测到M3U格式，正在解析...")
            return parse_m3u_to_txt(content)
        else:
            print("  检测到TXT格式，正在解析...")
            return parse_txt_content(content)

    except requests.exceptions.RequestException as e:
        print(f"  请求失败: {e}")
        return "", 0
    except Exception as e:
        print(f"  处理内容时出错: {e}")
        return "", 0

def main():
    # 确保TV目录存在
    if not os.path.exists("TV"):
        os.makedirs("TV")

    # 从文件加载源地址
    source_urls = load_source_urls()
    print(f"\\n共加载 {len(source_urls)} 个源地址")

    # 获取并合并内容
    all_content = ""
    total_channels = 0
    success_count = 0

    for idx, url in enumerate(source_urls, 1):
        print(f"\\n--- 处理第 {idx}/{len(source_urls)} 个源 ---")
        content, channel_count = fetch_content(url)
        if content:
            all_content += content + "\\n\\n"
            total_channels += channel_count
            success_count += 1
            print(f"✅ 源 {idx} 获取成功，频道数: {channel_count}")
        else:
            print(f"❌ 源 {idx} 获取失败或内容为空")

    print(f"\\n📊 成功获取 {success_count}/{len(source_urls)} 个源")
    print(f"📊 总计频道数: {total_channels}")

    if not all_content:
        print("错误：未能获取任何有效内容")
        return

    # 加载模板分类
    categories = load_categories_from_template()
    if not categories:
        print("分类数据为空，请检查模板文件格式")
        return

    # 处理内容
    lines = all_content.splitlines()
    sorted_content = []
    all_lines = [line.strip() for line in lines if line.strip() and "#genre#" not in line]

    # 记录已匹配行
    matched_lines = set()

    # 按模板分类整理频道
    for category, channels in categories.items():
        sorted_content.append(f"{category},#genre#")
        for channel in channels:
            # 尝试匹配频道名称
            channel_pattern = re.escape(channel)
            for line in all_lines:
                # 检查频道名称是否在行首
                if re.match(rf"^\\s*{channel_pattern}\\s*,", line, re.IGNORECASE):
                    if line not in matched_lines:
                        sorted_content.append(line)
                        matched_lines.add(line)
                    break  # 每个标准频道只取第一个
        sorted_content.append("")

    # 剩余未匹配的归入"其它"
    other_lines = [line for line in all_lines if line not in matched_lines]
    if other_lines:
        sorted_content.append("其它,#genre#")
        sorted_content.extend(other_lines)
        sorted_content.append("")

    # 保存结果
    output_path = "TV/live.txt"
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\\n".join(sorted_content))
        print(f"\\n✅ 多源合并完成，已保存为 {output_path}")
        print(f"📊 统计: {len(matched_lines)}个匹配频道, {len(other_lines)}个未分类频道")
        print(f"📊 总计写入频道数: {len(matched_lines) + len(other_lines)}")
    except Exception as e:
        print(f"保存文件时出错: {e}")

if __name__ == "__main__":
    main()