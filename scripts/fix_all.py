"""
一键修复 + 补字段脚本
用法:
  python fix_all.py <json路径>             单文件修复
  python fix_all.py <json目录>             批量修复目录下所有 JSON

功能:
  1. 修复 content 值中的未转义中文双引号（替换为书名号）
  2. 补 emo_vector（固定全0 8元素数组）
  3. 补 ref_emotion（固定"中性"）
"""
import re, json, os, sys


def pre_fix_bare_quotes(raw_text):
    """
    文本级预修复：在 json.load 之前，修复 content 值中裸 ASCII 双引号。
    兼容 "content": " 和 "content":" 两种格式。
    """
    lines = raw_text.split('\n')
    fixed_lines = []
    fixed_count = 0
    for line in lines:
        for marker in ['"content": "', '"content":"']:
            idx = line.find(marker)
            if idx >= 0:
                prefix = line[:idx + len(marker)]
                rest = line[idx + len(marker):]
                # content 结束标记优先级
                end_markers = ['", "delay"', '","delay"', '",', '"}', '"]']
                end_idx = -1
                for em in end_markers:
                    end_idx = rest.find(em)
                    if end_idx >= 0:
                        break
                if end_idx >= 0:
                    body = rest[:end_idx]       # content body（可能含裸引号）
                    suffix = rest[end_idx:]     # 从关闭 " 开始
                    if '"' in body:
                        parts = body.split('"')
                        fixed_parts = []
                        for i, part in enumerate(parts):
                            if i % 2 == 0:
                                fixed_parts.append(part)
                            else:
                                fixed_parts.append('\u300c' + part + '\u300d')
                        line = prefix + ''.join(fixed_parts) + suffix
                        fixed_count += 1
                break  # 匹配到一个 marker 就跳过其他的
        fixed_lines.append(line)
    if fixed_count > 0:
        print(f"  🔧 预修复 content 内裸引号: {fixed_count} 处")
    return '\n'.join(fixed_lines)


def fix_single_file(filepath):
    """修复单个 JSON 文件"""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # 0. 文本级预修复：在 json.parse 前修复 content 内的裸 ASCII 双引号
    content = pre_fix_bare_quotes(content)

    # 1. 修复 content 值中的未转义双引号
    lines = content.split('\n')
    fixed_lines = []
    for line in lines:
        if '"content"' in line:
            match = re.search(r'"content":\s*"(.*?)",\s*"delay"', line, re.DOTALL)
            if match:
                val = match.group(1)
                if '"' in val:
                    val_fixed = val.replace('\u201c', '\u300e').replace('\u201d', '\u300f')
                    line = line[:match.start(1)] + val_fixed + line[match.end(1):]
        fixed_lines.append(line)

    fixed_content = '\n'.join(fixed_lines)

    # 2. 解析 JSON
    try:
        data = json.loads(fixed_content)
    except json.JSONDecodeError as e:
        # 如果整行模式匹配失败，尝试在原始文本中全局替换中文引号
        raw_content = content
        raw_content = raw_content.replace('\u201c', '\u300e').replace('\u201d', '\u300f')
        try:
            data = json.loads(raw_content)
        except json.JSONDecodeError as e2:
            print(f"  ✗ JSON 仍然无法解析: {e2}")
            return False

    # 3. 补 emo_vector 和 ref_emotion
    script = data.get("script", [])
    added_count = 0
    for item in script:
        if "emo_vector" not in item:
            item["emo_vector"] = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
            added_count += 1
        if "ref_emotion" not in item:
            item["ref_emotion"] = "中性"
            added_count += 1

    # 4. 保存
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"  ✓ {os.path.basename(filepath)}: {len(script)}条脚本, 补了{added_count}个字段")
    return True


def main():
    if len(sys.argv) < 2:
        print("用法: python fix_all.py <json路径或目录>")
        sys.exit(1)

    target = sys.argv[1]

    if os.path.isfile(target):
        success = fix_single_file(target)
        if success:
            print(f"完成: {target}")
        else:
            sys.exit(1)
    elif os.path.isdir(target):
        json_files = sorted([f for f in os.listdir(target) if f.endswith('.json') and f != 'progress.json'])
        if not json_files:
            print(f"目录中未找到 JSON 文件: {target}")
            return
        print(f"批量修复 {len(json_files)} 个文件...")
        ok = 0
        fail = 0
        for fname in json_files:
            filepath = os.path.join(target, fname)
            if fix_single_file(filepath):
                ok += 1
            else:
                fail += 1
        print(f"完成: {ok} 成功, {fail} 失败")
    else:
        print(f"路径不存在: {target}")
        sys.exit(1)


if __name__ == "__main__":
    main()
