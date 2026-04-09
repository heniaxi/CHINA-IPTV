import requests
import re
import os

def get_base_dir():
    """获取脚本所在的目录（TV目录）"""
    return os.path.dirname(os.path.abspath(__file__))

def load_source_urls():
    """从文件加载源地址列表"""
    base_dir = get_base_dir()
    source_path = os.path.join(base_dir, "sources.txt")
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

    base_dir = get_base_dir()
    template_path = os.path.join(base_dir, "moban.txt")

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

def fetch_content(url, mapping):
    """从URL获取内容并转换为TXT格式的频道列表"""
    try:
        m3u_url_match = re.search(r"https?://[^\s]+", url)
        if not m3u_url_match:
            print(f"无效的URL格式: {url}")
            return [], 0

        m3u_url = m3u_url_match.group(0)
        print(f"正在获取: {m3u_url}")

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(m3u_url, timeout=15, headers=headers)
        response.raise_for_status()

        return parse_content(response.text, mapping)
    except requests.exceptions.RequestException as e:
        print(f"请求失败: {e}")
        return [], 0
    except Exception as e:
        print(f"处理内容时出错: {e}")
        return [], 0

def load_channel_mapping():
    """加载频道名称映射表"""
    mapping = {}
    base_dir = get_base_dir()
    mapping_path = os.path.join(base_dir, "channel_mapping.txt")

    if not os.path.exists(mapping_path):
        print(f"警告：未找到映射表文件 {mapping_path}")
        return mapping

    try:
        with open(mapping_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or "," not in line:
                    continue
                old_name, new_name = line.split(",", 1)
                mapping[old_name.strip()] = new_name.strip()
        print(f"加载映射表成功，共 {len(mapping)} 条映射")
    except Exception as e:
        print(f"加载映射表失败: {e}")
    return mapping

def parse_content(content, mapping):
    """解析内容，返回 (频道列表, 数量)"""
    lines = content.split('\n')
    channels = []  # 存储 (原始名称, 标准名称, URL)

    for i in range(len(lines)):
        line = lines[i].strip()

        # 处理M3U格式
        if line.startswith('#EXTINF:'):
            # 提取频道名
            name_match = re.search(r'tvg-name="([^"]*)"', line)
            if name_match:
                name = name_match.group(1)
            else:
                name = line.split(',')[-1].strip()

            name = re.sub(r'\s+', ' ', name).strip()

            # 获取URL
            if i + 1 < len(lines):
                url = lines[i + 1].strip()
                if url and not url.startswith('#'):
                    # 应用映射表
                    standard_name = mapping.get(name, name)
                    channels.append((name, standard_name, url))

        # 处理TXT格式（频道名,URL）
        elif ',' in line and not line.startswith('#'):
            parts = line.split(',', 1)
            if len(parts) == 2 and parts[1].startswith('http'):
                name = parts[0].strip()
                url = parts[1].strip()
                standard_name = mapping.get(name, name)
                channels.append((name, standard_name, url))

    return channels, len(channels)

def main():
    base_dir = get_base_dir()
    print(f"脚本所在目录: {base_dir}")

    print("当前目录文件列表:")
    for f in os.listdir(base_dir):
        print(f"  - {f}")

    # 1. 加载映射表
    mapping = load_channel_mapping()

    # 2. 加载源地址
    source_urls = load_source_urls()
    print(f"共加载 {len(source_urls)} 个源地址")

    # 3. 获取所有源的内容
    all_channels = []  # 每个元素: (原始名, 标准名, URL)
    for idx, url in enumerate(source_urls, 1):
        print(f"\n--- 处理第 {idx}/{len(source_urls)} 个源 ---")
        channels, count = fetch_content(url, mapping)
        all_channels.extend(channels)
        print(f"✅ 源 {idx} 获取成功，频道数: {count}")

    print(f"\n📊 总计获取频道数: {len(all_channels)}")

    # 4. 加载分类模板
    categories = load_categories_from_template()
    if not categories:
        print("分类数据为空，请检查模板文件格式")
        return

    print(f"\n加载分类: {list(categories.keys())}")

    # 构建标准名称到分类的映射
    name_to_category = {}
    for category, channel_list in categories.items():
        for channel_name in channel_list:
            name_to_category[channel_name] = category

    print(f"模板中的标准频道数: {len(name_to_category)}")

    # 5. 按分类整理频道
    categorized = {cat: [] for cat in categories.keys()}
    categorized['其它'] = []

    # 用于去重（同一个标准名只保留第一个URL）
    seen_names = set()

    for original_name, standard_name, url in all_channels:
        # 根据标准名称确定分类
        category = name_to_category.get(standard_name, '其它')

        # 去重：同一个标准名只保留一个
        if standard_name not in seen_names:
            seen_names.add(standard_name)
            categorized[category].append(f"{standard_name},{url}")
        # 可选：如果想保留多个源，注释掉上面的去重逻辑

    # 6. 构建输出
    sorted_content = []
    for category in ['央视', '卫视', '地方']:
        if categorized.get(category):
            sorted_content.append(f"{category},#genre#")
            sorted_content.extend(categorized[category])
            sorted_content.append("")

    # 添加其它分类
    if categorized['其它']:
        sorted_content.append("其它,#genre#")
        sorted_content.extend(categorized['其它'])
        sorted_content.append("")

    # 7. 保存结果
    output_path = os.path.join(base_dir, "live.txt")
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(sorted_content))

        total = sum(len(v) for v in categorized.values())
        matched = total - len(categorized['其它'])

        print(f"\n✅ 完成，已保存为 {output_path}")
        print(f"📊 统计: {matched}个匹配频道, {len(categorized['其它'])}个未分类频道")
        print(f"📊 总计频道数: {total}")

        if categorized['其它']:
            print(f"\n⚠️ 未匹配的频道标准名（前10个）:")
            for line in categorized['其它'][:10]:
                print(f"   - {line.split(',')[0]}")
    except Exception as e:
        print(f"保存文件时出错: {e}")

if __name__ == "__main__":
    main()