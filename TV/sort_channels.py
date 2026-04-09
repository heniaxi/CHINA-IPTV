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
        # 失败时返回默认源
        return ["https://live.fanmingming.com/tv/m3u/ipv6.m3u"]

    if not urls:
        print("警告：源地址文件为空，使用默认源")
        return ["https://live.fanmingming.com/tv/m3u/ipv6.m3u"]

    return urls

def load_categories_from_template():
    """从模板文件加载分类和频道信息"""
    categories = {}
    current_category = None

    # 确保模板文件存在
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

def fetch_m3u_content(url):
    """从URL获取M3U内容并转换为TXT格式，返回(内容, 频道数)"""
    try:
        # 从URL中提取实际的M3U URL
        m3u_url_match = re.search(r"https?://[^\s]+", url)
        if not m3u_url_match:
            print(f"无效的URL格式: {url}")
            return "", 0

        m3u_url = m3u_url_match.group(0)
        print(f"正在获取: {m3u_url}")

        response = requests.get(m3u_url, timeout=10)
        response.raise_for_status()

        # 解析M3U内容为TXT格式，返回(内容, 频道数)
        return parse_m3u_to_txt(response.text)
    except requests.exceptions.RequestException as e:
        print(f"请求失败: {e}")
        return "", 0
    except Exception as e:
        print(f"处理内容时出错: {e}")
        return "", 0

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
    lines = m3u_content.split('\n')
    channels = {}
    current_group = '未分组'
    channel_count = 0  # 新增：统计频道数

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
                    channel_count += 1  # 每添加一个频道，计数+1
                    current_group = group

    txt_content = ""
    for group, channel_list in channels.items():
        txt_content += f"{group},#genre#\n"
        txt_content += "\n".join(channel_list) + "\n\n"
    return txt_content.strip(), channel_count

def main():
    # 创建TV目录（如果不存在）
    # 确保TV目录存在
    if not os.path.exists("TV"):
        os.makedirs("TV")

    # 从文件加载源地址
    source_urls = load_source_urls()
    print(f"共加载 {len(source_urls)} 个源地址")

    # 获取并合并内容
    all_content = ""
    total_channels = 0  # 新增：累计频道总数

    for idx, url in enumerate(source_urls, 1):
        print(f"\n--- 处理第 {idx}/{len(source_urls)} 个源 ---")
        content, channel_count = fetch_m3u_content(url)
        if content:
            all_content += content + "\n\n"
            total_channels += channel_count
            print(f"✅ 源 {idx} 获取成功，频道数: {channel_count}")
        else:
            print(f"❌ 源 {idx} 获取失败或内容为空")

    print(f"\n📊 总计从所有源获取频道数: {total_channels}")

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
                if re.match(rf"^\s*{channel_pattern}\s*,", line, re.IGNORECASE):
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
            f.write("\n".join(sorted_content))
        print(f"\n✅ 多源合并完成，已保存为 {output_path}")
        print(f"📊 统计: {len(matched_lines)}个匹配频道, {len(other_lines)}个未分类频道")
        print(f"📊 总计频道数: {len(matched_lines) + len(other_lines)}")
    except Exception as e:
        print(f"保存文件时出错: {e}")

if __name__ == "__main__":
    main()