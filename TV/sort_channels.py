import requests
import re
import os
import sys

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

def fetch_m3u_content(url, mapping):
    """从URL获取M3U内容并转换为TXT格式"""
    try:
        m3u_url_match = re.search(r"https?://[^\s]+", url)
        if not m3u_url_match:
            print(f"无效的URL格式: {url}")
            return "", 0

        m3u_url = m3u_url_match.group(0)
        print(f"正在获取: {m3u_url}")

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(m3u_url, timeout=15, headers=headers)
        response.raise_for_status()

        # 判断内容类型并调用相应的解析函数
        content_type = response.headers.get('content-type', '').lower()
        if 'm3u' in content_type or m3u_url.endswith('.m3u'):
            return parse_m3u_to_txt(response.text, mapping)
        else:
            # 假设是TXT格式，直接处理
            return parse_txt_to_txt(response.text, mapping)
    except requests.exceptions.RequestException as e:
        print(f"请求失败: {e}")
        return "", 0
    except Exception as e:
        print(f"处理内容时出错: {e}")
        return "", 0

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

def parse_m3u_to_txt(m3u_content, mapping):
    """解析M3U格式内容，返回(txt内容, 频道数量)"""
    lines = m3u_content.split('\n')
    channels = {}
    current_group = '未分组'
    channel_count = 0

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
                    channel_count += 1
                    current_group = group

    txt_content = ""
    for group, channel_list in channels.items():
        txt_content += f"{group},#genre#\n"
        txt_content += "\n".join(channel_list) + "\n\n"
    return txt_content.strip(), channel_count

def parse_txt_to_txt(txt_content, mapping):
    """解析TXT格式内容（频道名,URL格式），返回(txt内容, 频道数量)"""
    lines = txt_content.split('\n')
    channels = {}
    current_group = '未分组'
    channel_count = 0

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # 处理分类行
        if ",#genre#" in line:
            current_group = line.split(",")[0].strip()
            continue

        # 处理频道行
        if ',' in line:
            parts = line.split(',', 1)
            if len(parts) == 2 and parts[1].startswith('http'):
                name = parts[0].strip()
                url = parts[1].strip()
                # 应用映射
                name = mapping.get(name, name)

                if current_group not in channels:
                    channels[current_group] = []
                channels[current_group].append(f"{name},{url}")
                channel_count += 1

    txt_content = ""
    for group, channel_list in channels.items():
        txt_content += f"{group},#genre#\n"
        txt_content += "\n".join(channel_list) + "\n\n"
    return txt_content.strip(), channel_count

def normalize_channel_name(name, mapping, reverse_mapping):
    """标准化频道名称，用于匹配"""
    # 先尝试直接映射
    if name in mapping:
        return mapping[name]

    # 尝试反向映射（将别名映射回标准名）
    for alias, standard in mapping.items():
        if name == standard or name.startswith(standard):
            return standard

    # 尝试去除常见后缀
    name_clean = re.sub(r'[-\s_].*$', '', name)
    if name_clean in mapping:
        return mapping[name_clean]

    return name

def count_channels_in_content(content):
    """统计内容中的频道数量（不包含分类行）"""
    if not content:
        return 0
    lines = content.splitlines()
    count = 0
    for line in lines:
        line = line.strip()
        if line and "#genre#" not in line and "," in line:
            parts = line.split(',', 1)
            if len(parts) == 2 and parts[1].startswith('http'):
                count += 1
    return count

def main():
    base_dir = get_base_dir()
    print(f"脚本所在目录: {base_dir}")

    # 列出当前目录下的文件（调试用）
    print("当前目录文件列表:")
    for f in os.listdir(base_dir):
        print(f"  - {f}")

    # 1. 加载映射表（只加载一次）
    mapping = load_channel_mapping()

    # 2. 加载源地址
    source_urls = load_source_urls()
    print(f"共加载 {len(source_urls)} 个源地址")

    # 3. 获取并合并所有源的内容
    all_content = ""
    total_channels = 0

    for idx, url in enumerate(source_urls, 1):
        print(f"\n--- 处理第 {idx}/{len(source_urls)} 个源 ---")
        content, channel_count = fetch_m3u_content(url, mapping)
        if content:
            all_content += content + "\n\n"
            total_channels += channel_count
            print(f"✅ 源 {idx} 获取成功，频道数: {channel_count}")
        else:
            print(f"❌ 源 {idx} 获取失败或内容为空")

    if not all_content:
        print("错误：未能获取任何有效内容")
        return

    print(f"\n📊 总计从所有源获取频道数: {total_channels}")

    # 4. 加载分类模板
    categories = load_categories_from_template()
    if not categories:
        print("分类数据为空，请检查模板文件格式")
        return

    print(f"\n加载分类: {list(categories.keys())}")
    for cat, chs in categories.items():
        print(f"  {cat}: {len(chs)}个频道")

    # 5. 解析所有频道行
    lines = all_content.splitlines()
    all_channel_lines = []

    for line in lines:
        line = line.strip()
        if line and "#genre#" not in line and "," in line:
            parts = line.split(',', 1)
            if len(parts) == 2 and parts[1].startswith('http'):
                all_channel_lines.append(line)

    print(f"\n📋 总共解析到 {len(all_channel_lines)} 个频道行")

    # 6. 按模板分类整理频道
    sorted_content = []
    matched_lines = set()

    # 创建标准频道名集合，用于快速匹配
    standard_channels = {}
    for category, channels in categories.items():
        for channel in channels:
            standard_channels[channel] = category

    # 匹配逻辑：将每个频道行中的频道名标准化后与模板对比
    for line in all_channel_lines:
        if line in matched_lines:
            continue

        # 提取频道名（逗号之前的部分）
        channel_name = line.split(',', 1)[0].strip()

        # 尝试匹配模板中的频道
        matched = False
        for standard_name, category in standard_channels.items():
            # 完全匹配
            if channel_name == standard_name:
                matched = True
                break
            # 标准化后匹配
            if standard_name in channel_name or channel_name in standard_name:
                matched = True
                break

        if matched:
            matched_lines.add(line)

    # 按分类输出
    for category, channels in categories.items():
        sorted_content.append(f"{category},#genre#")
        category_lines = []
        for channel in channels:
            # 查找匹配该频道的行
            for line in all_channel_lines:
                if line in matched_lines:
                    line_name = line.split(',', 1)[0].strip()
                    if line_name == channel or channel in line_name:
                        if line not in category_lines:
                            category_lines.append(line)
                            break
        # 去重并排序
        unique_lines = []
        seen = set()
        for line in category_lines:
            if line not in seen:
                seen.add(line)
                unique_lines.append(line)
        sorted_content.extend(unique_lines)
        sorted_content.append("")

    # 7. 处理未匹配的频道
    other_lines = [line for line in all_channel_lines if line not in matched_lines]
    if other_lines:
        sorted_content.append("其它,#genre#")
        sorted_content.extend(other_lines)
        sorted_content.append("")

    # 8. 保存结果
    output_path = os.path.join(base_dir, "live.txt")
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(sorted_content))

        # 统计最终文件中的频道数
        final_channel_count = count_channels_in_content("\n".join(sorted_content))

        print(f"\n✅ 多源合并完成，已保存为 {output_path}")
        print(f"📊 统计: {len(matched_lines)}个匹配频道, {len(other_lines)}个未分类频道")
        print(f"📊 总计频道数: {final_channel_count}")

        # 显示未匹配的频道示例
        if other_lines:
            print(f"\n⚠️ 未匹配频道示例（前10个）:")
            for line in other_lines[:10]:
                print(f"   - {line.split(',')[0]}")
    except Exception as e:
        print(f"保存文件时出错: {e}")

if __name__ == "__main__":
    main()