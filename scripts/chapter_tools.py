#!/usr/bin/env python3
"""chapter_tools.py - 小说章节切分与 fidelity gate 验证工具

用法:
  python chapter_tools.py split <txt路径> <输出目录>
  python chapter_tools.py check <章节txt路径> <json路径>
  python chapter_tools.py batch_check <章节txt目录> <json目录>

依赖: 仅 Python 标准库
编码: UTF-8
"""

import sys
import os
import re
import json

# Windows 终端默认 GBK，强制 UTF-8 输出
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# 章节标题正则: 匹配 "第一章", "第1章", "第123回", "Chapter 1" 等
CHAPTER_PATTERN = re.compile(
    r'^\s*'
    r'(?:'
    r'第[零一二三四五六七八九十百千万\d]+[章节回卷部]'   # 中文章节
    r'|'
    r'[Cc]hapter\s*\d+'                                    # 英文章节
    r'|'
    r'【第[零一二三四五六七八九十百千万\d]+[章节回卷部]】'  # 带方括号
    r')'
    r'(?:\s.*)?'
    r'\s*$'
)

# 中文数字映射
CN_NUM = {'零': 0, '一': 1, '二': 2, '三': 3, '四': 4, '五': 5,
          '六': 6, '七': 7, '八': 8, '九': 9, '十': 10, '百': 100, '千': 1000}

# 引号正则 (中文引号 + 英文引号)
QUOTE_PATTERN = re.compile(
    r'[\u300c\u201c\u201d\u2018\u2019\u300a\u3010]'
    r'(.+?)'
    r'[\u300d\u201c\u201d\u2018\u2019\u300b\u3011]'
)


def cn_to_int(s):
    """中文数字转整数"""
    if s.isdigit():
        return int(s)
    result = 0
    current = 0
    for ch in s:
        if ch in CN_NUM:
            val = CN_NUM[ch]
            if val >= 10:
                if current == 0:
                    current = 1
                result += current * val
                current = 0
            else:
                current = val
        else:
            return 0
    return result + current


def split_chapters(txt_path, output_dir):
    """将 TXT 按章节切分，输出每章文本文件和索引 JSON"""
    with open(txt_path, 'r', encoding='utf-8') as f:
        content = f.read()

    lines = content.split('\n')

    chapters = []
    current_title = None
    current_lines = []
    current_start = 0
    file_header = ''  # 标题前的内容(如书名、简介)

    for i, line in enumerate(lines):
        stripped = line.strip()
        if CHAPTER_PATTERN.match(stripped):
            # 保存上一章
            if current_title is not None:
                ch_content = '\n'.join(current_lines).strip()
                chapters.append({
                    'index': len(chapters) + 1,
                    'title': current_title,
                    'start_line': current_start + 1,
                    'end_line': i,
                    'char_count': len(ch_content.replace(' ', '').replace('\n', '')),
                    'content': ch_content
                })
            else:
                # 标题前的内容
                file_header = '\n'.join(current_lines).strip()
            current_title = stripped
            current_lines = []
            current_start = i + 1
        else:
            current_lines.append(line)

    # 保存最后一章
    if current_title is not None:
        ch_content = '\n'.join(current_lines).strip()
        chapters.append({
            'index': len(chapters) + 1,
            'title': current_title,
            'start_line': current_start + 1,
            'end_line': len(lines),
            'char_count': len(ch_content.replace(' ', '').replace('\n', '')),
            'content': ch_content
        })

    # 如果没有检测到章节标记，整篇作为一个章节
    if not chapters:
        full_content = content.strip()
        chapters.append({
            'index': 1,
            'title': os.path.splitext(os.path.basename(txt_path))[0],
            'start_line': 1,
            'end_line': len(lines),
            'char_count': len(full_content.replace(' ', '').replace('\n', '')),
            'content': full_content
        })

    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)

    # 小说名(去扩展名)
    novel_name = os.path.splitext(os.path.basename(txt_path))[0]

    # 保存每章文本
    for ch in chapters:
        # 文件名: 小说名_001_章节标题.txt (去除文件名非法字符)
        safe_title = re.sub(r'[<>:"/\\|?*]', '_', ch['title'])
        ch_filename = f'{novel_name}_{ch["index"]:03d}_{safe_title}.txt'
        ch_filepath = os.path.join(output_dir, ch_filename)
        with open(ch_filepath, 'w', encoding='utf-8') as f:
            f.write(ch['content'])
        ch['file'] = ch_filepath

    # 保存索引 (移除 content 字段，太大)
    index_data = []
    for ch in chapters:
        index_data.append({
            'index': ch['index'],
            'title': ch['title'],
            'start_line': ch['start_line'],
            'end_line': ch['end_line'],
            'char_count': ch['char_count'],
            'file': ch['file']
        })

    index_file = os.path.join(output_dir, 'chapters.json')
    with open(index_file, 'w', encoding='utf-8') as f:
        json.dump({
            'novel_name': novel_name,
            'source_file': txt_path,
            'total_chapters': len(chapters),
            'header': file_header[:200] if file_header else '',
            'chapters': index_data
        }, f, ensure_ascii=False, indent=2)

    # 输出摘要
    print(f'切分完成: {novel_name} - 共 {len(chapters)} 章')
    print(f'索引文件: {index_file}')
    print(f'输出目录: {output_dir}')
    print('-' * 60)
    for ch in index_data:
        print(f'  第{ch["index"]:3d}章 {ch["title"][:20]:20s} {ch["char_count"]:6d}字  [{ch["start_line"]}-{ch["end_line"]}]')

    return chapters


def extract_last_meaningful_text(text):
    """提取文本中最后一个有意义的文本片段(台词或旁白末句)"""
    lines = [l.strip() for l in text.strip().split('\n') if l.strip()]
    if not lines:
        return ''

    last_line = lines[-1]

    # 如果最后一行是章节标题，取倒数第二行
    if CHAPTER_PATTERN.match(last_line) and len(lines) > 1:
        last_line = lines[-2]

    return last_line.strip()


def fidelity_check(txt_path, json_path):
    """fidelity gate: 比对 TXT 末句与 JSON 末句，检测台词遗漏"""
    with open(txt_path, 'r', encoding='utf-8') as f:
        txt_content = f.read()
    with open(json_path, 'r', encoding='utf-8') as f:
        json_data = json.load(f)

    # --- 提取 TXT 末句 ---
    txt_last = extract_last_meaningful_text(txt_content)

    # --- 提取 JSON 末句 ---
    script = json_data.get('script', [])
    if not script:
        return {
            'pass': False,
            'reason': 'JSON script 数组为空',
            'txt_last': txt_last[-50:],
            'json_last': '(空)',
            'txt_quote_count': 0,
            'json_dialogue_count': 0,
            'quote_diff': 0,
            'overlap_ratio': '0%',
            'issues': ['JSON script 数组为空']
        }

    json_last = script[-1].get('content', '')
    # 去除语气标签 [低声] 等
    json_last_clean = re.sub(r'^\[[^\]]+\]', '', json_last).strip()

    # --- 统计 TXT 台词数 (引号内内容) ---
    txt_quotes = QUOTE_PATTERN.findall(txt_content)
    txt_quote_count = len(txt_quotes)

    # --- 统计 JSON 非旁白 speaker 数 ---
    json_dialogue_count = sum(1 for s in script if s.get('speaker') != '旁白')

    # --- 语义比对: 关键词重叠率 ---
    json_keywords = set(re.findall(r'[\u4e00-\u9fff]', json_last_clean))
    txt_keywords = set(re.findall(r'[\u4e00-\u9fff]', txt_last))

    if json_keywords and txt_keywords:
        overlap = json_keywords & txt_keywords
        overlap_ratio = len(overlap) / max(len(json_keywords), len(txt_keywords))
    else:
        overlap_ratio = 0.0

    # 台词数量偏差
    quote_diff = abs(txt_quote_count - json_dialogue_count)

    # --- 判断: 分离硬失败与警告 ---
    hard_issues = []  # 导致 FAIL
    soft_issues = []  # 警告，不阻断

    # 硬失败：末句不匹配（最关键的检查）
    if overlap_ratio < 0.3 and txt_last and json_last_clean:
        hard_issues.append(
            f'末句关键词重叠率低 ({overlap_ratio:.0%}): '
            f'TXT="...{txt_last[-30:]}" vs JSON="...{json_last_clean[-30:]}"'
        )
        # 末句不匹配时才检查台词偏差
        if quote_diff > 2:
            hard_issues.append(
                f'台词数量偏差大: TXT={txt_quote_count}句 vs JSON={json_dialogue_count}句 '
                f'(偏差{quote_diff})'
            )
    elif quote_diff > 2:
        # 末句匹配但台词偏差大 → 通常是长篇独白嵌套引号，仅警告
        soft_issues.append(
            f'台词数量有偏差(偏差{quote_diff})，但末句匹配，可能因角色长篇叙述嵌套引号导致'
        )

    # 检查 JSON 字段完整性
    field_issues = []
    required_fields = {'speaker', 'content', 'emo_vector', 'delay'}
    for i, s in enumerate(script):
        missing = required_fields - set(s.keys())
        if missing:
            field_issues.append(f'script[{i}] 缺少字段: {missing}')
        extra = set(s.keys()) - required_fields
        if extra:
            field_issues.append(f'script[{i}] 多余字段: {extra}')

    if field_issues:
        hard_issues.extend(field_issues[:5])  # 只报前5个

    # 检查 content 长度
    long_contents = []
    for i, s in enumerate(script):
        content = re.sub(r'^\[[^\]]+\]', '', s.get('content', ''))
        cn_chars = len(re.findall(r'[\u4e00-\u9fff]', content))
        if cn_chars > 120:
            long_contents.append(f'script[{i}] content 超过120汉字 ({cn_chars}字)')

    if long_contents:
        hard_issues.extend(long_contents[:5])

    return {
        'pass': len(hard_issues) == 0,
        'txt_last': txt_last[-50:] if txt_last else '(空)',
        'json_last': json_last_clean[-50:] if json_last_clean else '(空)',
        'txt_quote_count': txt_quote_count,
        'json_dialogue_count': json_dialogue_count,
        'quote_diff': quote_diff,
        'overlap_ratio': f'{overlap_ratio:.0%}',
        'hard_issues': hard_issues,
        'soft_issues': soft_issues,
        'issues': hard_issues + soft_issues  # 向后兼容
    }


def batch_check(txt_dir, json_dir):
    """批量检查: 对比 txt 目录和 json 目录下的所有章节"""
    txt_files = sorted([f for f in os.listdir(txt_dir) if f.endswith('.txt') and f != 'chapters.json'])
    json_files = sorted([f for f in os.listdir(json_dir) if f.endswith('.json') and f != 'chapters.json'])

    results = []
    pass_count = 0
    fail_count = 0

    for txt_file in txt_files:
        # 匹配对应的 JSON 文件: 优先同名，其次按章节序号匹配
        base_name = os.path.splitext(txt_file)[0]
        matched_json = None

        # 策略1: 完全同名 (xxx.txt -> xxx.json)
        for jf in json_files:
            jf_base = os.path.splitext(jf)[0]
            if base_name == jf_base:
                matched_json = jf
                break

        # 策略2: 按章节序号匹配 (提取 _001_ 中的 001)
        if not matched_json:
            num_match = re.search(r'_(\d{3})_', txt_file)
            if num_match:
                ch_num = num_match.group(1)
                for jf in json_files:
                    if f'_{ch_num}_' in jf or f'_{ch_num}.' in jf:
                        matched_json = jf
                        break

        # 策略3: 模糊匹配
        if not matched_json:
            for jf in json_files:
                jf_base = os.path.splitext(jf)[0]
                if base_name in jf_base or jf_base in base_name:
                    matched_json = jf
                    break

        if not matched_json:
            results.append({
                'chapter': txt_file,
                'status': 'MISSING_JSON',
                'detail': '未找到对应的 JSON 文件'
            })
            fail_count += 1
            continue

        txt_path = os.path.join(txt_dir, txt_file)
        json_path = os.path.join(json_dir, matched_json)
        result = fidelity_check(txt_path, json_path)

        if result['pass']:
            results.append({
                'chapter': txt_file,
                'status': 'PASS',
                'detail': f'末句重叠{result["overlap_ratio"]}, 台词偏差{result["quote_diff"]}'
            })
            pass_count += 1
        else:
            results.append({
                'chapter': txt_file,
                'status': 'FAIL',
                'detail': '; '.join(result['issues'])
            })
            fail_count += 1

    # 输出报告
    print('=' * 70)
    print('FIDELITY GATE 批量检查报告')
    print('=' * 70)
    print(f'总计: {len(results)} 章 | 通过: {pass_count} | 未通过: {fail_count}')
    print('-' * 70)
    print(f'{"章节":<40s} {"状态":<12s} {"详情"}')
    print('-' * 70)
    for r in results:
        status_icon = {'PASS': '✓通过', 'FAIL': '✗未通过', 'MISSING_JSON': '⚠缺JSON'}[r['status']]
        print(f'{r["chapter"][:38]:<40s} {status_icon:<12s} {r["detail"]}')
    print('=' * 70)

    return results


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1]

    if command == 'split':
        if len(sys.argv) < 4:
            print('用法: python chapter_tools.py split <txt路径> <输出目录>')
            sys.exit(1)
        txt_path = sys.argv[2]
        output_dir = sys.argv[3]
        if not os.path.exists(txt_path):
            print(f'错误: 文件不存在: {txt_path}')
            sys.exit(1)
        split_chapters(txt_path, output_dir)

    elif command == 'check':
        if len(sys.argv) < 4:
            print('用法: python chapter_tools.py check <章节txt路径> <json路径>')
            sys.exit(1)
        txt_path = sys.argv[2]
        json_path = sys.argv[3]
        if not os.path.exists(txt_path):
            print(f'错误: TXT文件不存在: {txt_path}')
            sys.exit(1)
        if not os.path.exists(json_path):
            print(f'错误: JSON文件不存在: {json_path}')
            sys.exit(1)

        result = fidelity_check(txt_path, json_path)

        print('=' * 60)
        print('FIDELITY GATE 检查结果')
        print('=' * 60)
        print(f'状态: {"✓ 通过" if result["pass"] else "✗ 未通过"}')
        print(f'TXT 末句:  ...{result["txt_last"]}')
        print(f'JSON 末句: ...{result["json_last"]}')
        print(f'TXT 台词数:  {result["txt_quote_count"]}')
        print(f'JSON 台词数: {result["json_dialogue_count"]} (偏差 {result["quote_diff"]})')
        print(f'末句重叠率: {result["overlap_ratio"]}')
        if result.get('hard_issues'):
            print('\n硬失败（需重试）:')
            for issue in result['hard_issues']:
                print(f'  - {issue}')
        if result.get('soft_issues'):
            print('\n警告（不阻断）:')
            for issue in result['soft_issues']:
                print(f'  - {issue}')
        print('=' * 60)

        if not result['pass']:
            sys.exit(1)

    elif command == 'progress':
        if len(sys.argv) < 4:
            print('用法: python chapter_tools.py progress save <输出目录> <章节序号> <标题>')
            print('      python chapter_tools.py progress load <输出目录>')
            sys.exit(1)
        sub_cmd = sys.argv[2]
        output_dir = sys.argv[3]
        if sub_cmd == 'save':
            if len(sys.argv) < 6:
                print('用法: python chapter_tools.py progress save <输出目录> <章节序号> <标题>')
                sys.exit(1)
            ch_idx = int(sys.argv[4])
            ch_title = sys.argv[5]
            progress_save(output_dir, ch_idx, ch_title)
        elif sub_cmd == 'load':
            progress_load(output_dir)
        else:
            print(f'未知子命令: {sub_cmd} (可用: save, load)')

    elif command == 'list':
        txt_dir = sys.argv[2] if len(sys.argv) > 2 else '.'
        json_dir = sys.argv[3] if len(sys.argv) > 3 else os.path.join(txt_dir, 'output')
        list_chapters(txt_dir, json_dir)

    else:
        print(f'未知命令: {command}')
        print('可用命令: split, check, batch_check, progress, list')
        sys.exit(1)


def _chapter_sort_key(filename):
    """提取文件名中的章节序号用于排序，支持 '第X章' 中文数字"""
    import re as _re
    # 提取 "第X章" 中的数字
    m = _re.search(r'第([零一二三四五六七八九十百千万\d]+)[章节回卷部]', filename)
    if m:
        return (0, cn_to_int(m.group(1)))
    # 提取任何数字
    m = _re.search(r'(\d+)', filename)
    if m:
        return (1, int(m.group(1)))
    return (2, filename)


def progress_save(output_dir, chapter_index, chapter_title):
    """保存进度到 progress.json"""
    import datetime
    progress_path = os.path.join(output_dir, 'progress.json')
    progress = {
        'last_completed': chapter_index,
        'last_chapter': chapter_title,
        'completed_at': datetime.datetime.now().isoformat()
    }
    with open(progress_path, 'w', encoding='utf-8') as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)
    print(f'进度已保存: 第{chapter_index}章 {chapter_title}')


def progress_load(output_dir):
    """加载进度，返回 (chapter_index, chapter_title) 或 (0, None)"""
    progress_path = os.path.join(output_dir, 'progress.json')
    if not os.path.exists(progress_path):
        print('未找到进度文件，从头开始。')
        return 0, None
    with open(progress_path, 'r', encoding='utf-8') as f:
        progress = json.load(f)
    idx = progress.get('last_completed', 0)
    title = progress.get('last_chapter', '')
    print(f'上次完成: 第{idx}章 {title}')
    print(f'下次从第{idx + 1}章开始。')
    return idx, title


def list_chapters(txt_dir, output_dir=None):
    """列出章节及转换状态"""
    output_dir = output_dir or os.path.join(txt_dir, 'output')
    txt_files = sorted(
        [f for f in os.listdir(txt_dir) if f.endswith('.txt')],
        key=lambda x: _chapter_sort_key(x)
    )

    if not txt_files:
        print('未找到 .txt 文件')
        return []

    # 查找已有的 JSON 文件
    json_files = set()
    if os.path.isdir(output_dir):
        for f in os.listdir(output_dir):
            if f.endswith('.json') and f != 'chapters.json':
                json_files.add(f)

    results = []
    for i, txt_file in enumerate(txt_files, 1):
        base = os.path.splitext(txt_file)[0]
        converted = any(base in jf for jf in json_files)
        results.append({
            'index': i,
            'file': txt_file,
            'title': base,
            'converted': converted
        })

    # 输出
    print(f'章节文件 ({len(txt_files)} 个)')
    print('-' * 60)
    for r in results:
        status = '✓已转换' if r['converted'] else '○待转换'
        print(f'  [{r["index"]:3d}] {status}  {r["file"][:45]}')
    print('-' * 60)
    print(f'已转换: {sum(1 for r in results if r["converted"])}/{len(results)}')

    return results


if __name__ == '__main__':
    main()
