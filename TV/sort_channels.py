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
                if not line or line.startswith('#'):
                    continue
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

                if ",#genre#" in line:
                    current_category = line.split(",")[0].strip()
                    categories[current_category] = []
                elif current_category:
                    channel = line.strip()
                    if channel:
                        categories[current_category].append(channel)
    except Exception as e:
        print(f"读取模板文件出错: {e}")

    return categories

def fetch_m3u_content(url):
    """从URL获取M3U内容并转换为TXT格式"""
    try:
        m3u_url_match = re.search(r"https?://[^\s]+", url)
        if not m3u_url_match:
            print(f"无效的URL格式: {url}")
            return ""

        m3u_url = m3u_url_match.group(0)
        print(f"正在获取: {m3u_url}")

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(m3u_url, timeout=15, headers=headers)
        response.raise_for_status()

        return parse_m3u_to_txt(response.text)
    except requests.exceptions.RequestException as e:
        print(f"请求失败: {e}")
        return ""
    except Exception as e:
        print(f"处理内容时出错: {e}")
        return ""

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
    mapping = load_channel_mapping()
    lines = m3u_content.split('\n')
    channels = {}
    current_group = '未分组'

    for i in range(len(lines)):
        line = lines[i].strip()
        if line.startswith('#EXTINF:'):
            group_match = re.search(r'group-title="([^"]*)"', line)
            group = group_match.group(1) if group_match else current_group

            name_match = re.search(r'tvg-name="([^"]*)"', line)
            name = name_match.group(1) if name_match else line.split(',')[-1].strip()

            name = re.sub(r'\s+', ' ', name).strip()
            name = mapping.get(name, name)

            if i + 1 < len(lines):
                url = lines[i + 1].strip()
                if url and not url.startswith('#'):
                    if group not in channels:
                        channels[group] = []
                    channels[group].append(f"{name},{url}")
                    current_group = group

    txt_content = ""
    for group, channel_list in channels.items():
        txt_content += f"{group},#genre#\n"
        txt_content += "\n".join(channel_list) + "\n\n"
    return txt_content.strip()

def main():
    # 确保TV目录存在
    if not os.path.exists("TV"):
        os.makedirs("TV")

    source_urls = load_source_urls()
    print(f"共加载 {len(source_urls)} 个源地址")

    all_content = ""
    for url in source_urls:
        content = fetch_m3u_content(url)
        if content:
            all_content += content + "\n\n"

    if not all_content:
        print("错误：未能获取任何有效内容")
        return

    categories = load_categories_from_template()
    if not categories:
        print("分类数据为空，请检查模板文件格式")
        return

    lines = all_content.splitlines()
    sorted_content = []
    all_lines = [line.strip() for line in lines if line.strip() and "#genre#" not in line]

    matched_lines = set()

    for category, channels in categories.items():
        sorted_content.append(f"{category},#genre#")
        for channel in channels:
            channel_pattern = re.escape(channel)
            for line in all_lines:
                if re.match(rf"^\s*{channel_pattern}\s*,", line, re.IGNORECASE):
                    if line not in matched_lines:
                        sorted_content.append(line)
                        matched_lines.add(line)
                        break
        sorted_content.append("")

    other_lines = [line for line in all_lines if line not in matched_lines]
    if other_lines:
        sorted_content.append("其它,#genre#")
        sorted_content.extend(other_lines)
        sorted_content.append("")

    output_path = "TV/live.txt"
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(sorted_content))
        print(f"✅ 多源合并完成，已保存为 {output_path}")
        print(f"统计: {len(matched_lines)}个匹配频道, {len(other_lines)}个未分类频道")
    except Exception as e:
        print(f"保存文件时出错: {e}")

if __name__ == "__main__":
    main()