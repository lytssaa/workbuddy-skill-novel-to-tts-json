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


def _pre_fix_bare_quotes_inline(raw_text):
    """
    内联预修复：在 json.load 之前修复 content 内裸 ASCII 双引号。
    使用 ", "delay"/",/"] 等作为 content 值结束的可靠标记，按行处理。
    兼容压缩单行 JSON 和格式化多行 JSON。
    """
    lines = raw_text.split('\n')
    fixed_lines = []
    fixed_count = 0
    for line in lines:
        # 兼容 "content": " 和 "content":" 两种格式
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
                    body = rest[:end_idx]
                    suffix = rest[end_idx:]
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
        print(f"     🔧 预修复 content 内裸引号: {fixed_count} 处")
    return '\n'.join(fixed_lines)


def fidelity_check(txt_path, json_path):
    """fidelity gate: 比对 TXT 末句与 JSON 末句，检测台词遗漏"""
    # ═══════ Step 0: JSON 合法性预检 ═══════
    print("  🔍 [预检] 校验 JSON 语法...")
    with open(txt_path, 'r', encoding='utf-8') as f:
        txt_content = f.read()
    with open(json_path, 'r', encoding='utf-8') as f:
        raw_json = f.read()

    json_data = None
    try:
        json_data = json.loads(raw_json)
        print("     ✅ JSON 语法合法")
    except json.JSONDecodeError as e:
        print(f"     ❌ JSON 语法错误: {e}")
        print("     💡 建议: 先运行 python scripts/fix_all.py 尝试自动修复")
        # 内联预修复逻辑，不依赖模块导入路径
        try:
            print("     🔧 尝试文本级预修复...")
            fixed = _pre_fix_bare_quotes_inline(raw_json)
            json_data = json.loads(fixed)
            with open(json_path, 'w', encoding='utf-8') as f:
                f.write(fixed)
            print("     ✅ 预修复成功，已写回文件")
        except Exception as e2:
            print(f"     ❌ 预修复也失败: {e2}")
            return {
                'pass': False,
                'reason': 'JSON 解析失败且预修复无效',
                'txt_last': '(预检失败)',
                'json_last': '(预检失败)',
                'txt_quote_count': 0,
                'json_dialogue_count': 0,
                'quote_diff': 0,
                'overlap_ratio': '0%',
                'issues': ['JSON 语法错误']
            }

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
    # 必须是完整5字段（speaker/content/delay + fix_all后补的emo_vector/ref_emotion）
    # check 是在 fix_all 之后运行的，所以必须5字段齐全
    required_fields = {'speaker', 'content', 'delay', 'emo_vector', 'ref_emotion'}
    for i, s in enumerate(script):
        missing = required_fields - set(s.keys())
        if missing:
            field_issues.append(f'script[{i}] 缺少字段: {missing}')

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

    # --- 字数覆盖率检查 ---
    txt_cn_count = len(re.findall(r'[\u4e00-\u9fff]', txt_content))
    json_cn_count = 0
    for s in script:
        content = re.sub(r'^\[[^\]]+\]', '', s.get('content', ''))
        json_cn_count += len(re.findall(r'[\u4e00-\u9fff]', content))

    if txt_cn_count > 0:
        coverage_ratio = json_cn_count / txt_cn_count
    else:
        coverage_ratio = 1.0

    if coverage_ratio < 0.92:
        hard_issues.append(
            f'字数覆盖率低 ({coverage_ratio:.0%}): '
            f'TXT={txt_cn_count}字 vs JSON={json_cn_count}字，'
            f'可能有 {txt_cn_count - json_cn_count}字内容遗漏'
        )
    elif coverage_ratio < 0.96:
        soft_issues.append(
            f'字数覆盖率偏低 ({coverage_ratio:.0%})，可能有少量内容压缩'
        )

    # --- 段落采样检查 ---
    # 把 TXT 按换行分段，从中均匀采样若干段，检查关键词是否在 JSON 中出现
    json_full_text = ''
    for s in script:
        c = re.sub(r'^\[[^\]]+\]', '', s.get('content', ''))
        json_full_text += c

    paragraphs = [p.strip() for p in txt_content.split('\n') if p.strip() and len(p.strip()) > 30]
    if paragraphs:
        # 均匀采样：取 1/4, 2/4, 3/4 位置的段落（不取头尾，头尾已被末句检查覆盖）
        sample_indices = []
        if len(paragraphs) >= 4:
            for frac in [0.25, 0.5, 0.75]:
                idx = int(len(paragraphs) * frac)
                sample_indices.append(idx)
        elif len(paragraphs) >= 2:
            sample_indices.append(len(paragraphs) // 2)

        missing_paragraphs = []
        for idx in sample_indices:
            para = paragraphs[idx]
            # 去掉引号和说话者标识（"XXX道："、"XXX叫道："等），这些在转换时会被移到 speaker 字段
            para_clean = re.sub(r'[\u201c\u201d\u300c\u300d\u300e\u300f]', '', para)  # 去引号
            para_clean = re.sub(r'[\u4e00-\u9fff]{2,6}(?:道|叫道|大怒道|嚷道|大喝道|骂道|说|笑道|问道|答道|喊道)[：:]', '', para_clean)
            # 取前 15 个汉字作为搜索关键词
            cn_chars = re.findall(r'[\u4e00-\u9fff]', para_clean)
            if len(cn_chars) < 8:
                continue
            search_key = ''.join(cn_chars[:15])
            # 在 JSON 全文（去标点）中搜索
            json_nopunc = re.sub(r'[，。！？、；：""''\u201c\u201d\u300c\u300d]', '', json_full_text)
            if search_key not in json_nopunc:
                missing_paragraphs.append(f'段落"{para[:40]}..."的关键词未在JSON中找到')

        # 段落采样作为软警告（对话密集章节容易因拆分方式不同而误报）
        if missing_paragraphs:
            soft_issues.append(
                f'段落采样检查发现 {len(missing_paragraphs)} 处内容可能遗漏: '
                + '; '.join(missing_paragraphs[:3])
            )

    # --- 语气标签检查（角色台词应加标签，旁白不加） ---
    dialogue_total = 0
    dialogue_tagged = 0
    untagged_dialogue = []

    for i, s in enumerate(script):
        if s.get('speaker') == '旁白':
            continue
        dialogue_total += 1
        content = s.get('content', '')
        has_tag = bool(re.match(r'^\[[^\]]+\]', content))
        if has_tag:
            dialogue_tagged += 1
        else:
            untagged_dialogue.append(f'script[{i}] {s["speaker"]}: {content[:40]}...')

    # 角色台词无标签≥5条硬失败，1-4条软警告
    if len(untagged_dialogue) >= 5:
        hard_issues.append(
            f'角色台词缺少语气标签: {len(untagged_dialogue)}条台词未加标签(共{dialogue_total}条)。'
            f'角色台词应加语气标签如[低声][愤怒][悲伤]等。'
            f'如: {"; ".join(untagged_dialogue[:3])}'
        )
    elif len(untagged_dialogue) >= 1:
        soft_issues.append(
            f'有{len(untagged_dialogue)}条角色台词未加语气标签: '
            + '; '.join(untagged_dialogue[:3])
        )

    # --- 收集报告数据 ---
    char_count = len(json_data.get('character_map', {}))
    delay_dist = {}
    tag_dist = {}
    for s in script:
        d = s.get('delay', 0)
        delay_dist[d] = delay_dist.get(d, 0) + 1
        content = s.get('content', '')
        tag_match = re.match(r'^\[([^\]]+)\]', content)
        if tag_match:
            t = tag_match.group(1)
            tag_dist[t] = tag_dist.get(t, 0) + 1

    return {
        'pass': len(hard_issues) == 0,
        'txt_last': txt_last[-50:] if txt_last else '(空)',
        'json_last': json_last_clean[-50:] if json_last_clean else '(空)',
        'txt_quote_count': txt_quote_count,
        'json_dialogue_count': json_dialogue_count,
        'quote_diff': quote_diff,
        'overlap_ratio': f'{overlap_ratio:.0%}',
        'coverage_ratio': f'{coverage_ratio:.0%}',
        'txt_cn_count': txt_cn_count,
        'json_cn_count': json_cn_count,
        'tag_ratio': f'{dialogue_tagged}/{dialogue_total}',
        'char_count': char_count,
        'delay_dist': delay_dist,
        'tag_dist': tag_dist,
        'hard_issues': hard_issues,
        'soft_issues': soft_issues,
        'issues': hard_issues + soft_issues  # 向后兼容
    }


def print_report(result, json_path=None):
    """输出章节质量报告表格"""
    status = '✅ 通过' if result['pass'] else '❌ 未通过'

    # 收集表格行
    lines = []
    lines.append('')
    lines.append('=' * 60)
    lines.append('📊 章节转换质量报告')
    lines.append('=' * 60)
    lines.append(f'  {"状态":<12} {status}')

    if json_path:
        lines.append(f'  {"文件":<12} {os.path.basename(json_path)}')

    lines.append(f'  {"字数覆盖率":<12} {result["coverage_ratio"]} ({result.get("json_cn_count","?")}/{result.get("txt_cn_count","?")}字)')
    lines.append(f'  {"script条数":<12} {result["json_dialogue_count"]} 条')
    lines.append(f'  {"角色数量":<12} {result.get("char_count", "?")} 个')

    # 语气标签
    tag_ratio = result.get('tag_ratio', '?/???')
    parts = tag_ratio.split('/')
    if len(parts) == 2:
        try:
            tagged, total = int(parts[0]), int(parts[1])
            tag_pct = f'{tagged}/{total} ({tagged/total*100:.0f}%)' if total > 0 else '0/0'
        except:
            tag_pct = tag_ratio
    else:
        tag_pct = tag_ratio
    lines.append(f'  {"台词标签":<12} {tag_pct}')

    # 标签分布
    tag_dist = result.get('tag_dist', {})
    if tag_dist:
        top_tags = sorted(tag_dist.items(), key=lambda x: -x[1])[:5]
        tag_str = ', '.join(f'[{t}]{c}' for t, c in top_tags)
        lines.append(f'  {"标签TOP5":<12} {tag_str}')

    # delay 分布
    delay_dist = result.get('delay_dist', {})
    if delay_dist:
        delay_parts = []
        for d in [800, 500, 1500, 2000]:
            if d in delay_dist:
                label = {800: '旁白', 500: '对话', 1500: '转折', 2000: '场景'}.get(d, str(d))
                delay_parts.append(f'{label}={delay_dist[d]}条')
        if delay_parts:
            lines.append(f'  {"delay分布":<12} {", ".join(delay_parts)}')

    # 问题摘要
    if result.get('hard_issues'):
        lines.append(f'  {"硬失败":<12} {len(result["hard_issues"])} 项')
        for issue in result['hard_issues'][:2]:
            lines.append(f'    ⚠ {issue[:60]}')
    if result.get('soft_issues'):
        lines.append(f'  {"警告":<12} {len(result["soft_issues"])} 项')
        for issue in result['soft_issues'][:2]:
            lines.append(f'    ⓘ {issue[:60]}')

    lines.append('=' * 60)
    print('\n'.join(lines))


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
            # 解析标签率
            tag_ratio = result.get('tag_ratio', '?/?')
            results.append({
                'chapter': txt_file,
                'status': 'PASS',
                'coverage': result['coverage_ratio'],
                'script_count': result['json_dialogue_count'],
                'char_count': result.get('char_count', 0),
                'tag_ratio': tag_ratio,
                'detail': f'台词偏差{result["quote_diff"]}'
            })
            pass_count += 1
        else:
            results.append({
                'chapter': txt_file,
                'status': 'FAIL',
                'coverage': result.get('coverage_ratio', '?'),
                'script_count': result['json_dialogue_count'],
                'char_count': result.get('char_count', 0),
                'tag_ratio': result.get('tag_ratio', '?/?'),
                'detail': '; '.join(result['issues'][:2])
            })
            fail_count += 1

    # 输出报告
    print()
    print('━' * 66)
    print('  FIDELITY GATE 批量检查报告')
    print('━' * 66)
    print(f'  总计: {len(results)} 章 | 通过: {pass_count} | 未通过: {fail_count}')
    print()
    for r in results:
        status_icon = '✅' if r['status'] == 'PASS' else ('❌' if r['status'] == 'FAIL' else '⚠️')
        # 缩写章节名（取第2个__之后的和上中下）
        ch = r['chapter'].replace('.txt', '')
        parts = ch.split('__')
        if len(parts) >= 2:
            short = parts[-1]  # 最后的"xxx_上"部分
            ch_short = f'{parts[0]} {short}'
        else:
            ch_short = ch
        # 标签率
        tag = r.get('tag_ratio', '?/?')
        coverage = r.get('coverage', '??%')
        detail = r.get('detail', '')
        print(f'  {status_icon} {ch_short:<28s} 覆盖率{coverage:<5s} 脚本{r["script_count"]:<4d}条 角色{r.get("char_count",0):<2d}个 标签{tag:<8s} {detail[:40]}')
    print('━' * 66)

    # 汇总统计
    if pass_count > 0:
        coverages = []
        tag_ratios = []
        for r in results:
            if r['status'] == 'PASS' and r.get('coverage', '').endswith('%'):
                try:
                    coverages.append(int(r['coverage'].replace('%', '')))
                except:
                    pass
        avg_cov = sum(coverages) / len(coverages) if coverages else 0
        print(f'  通过率 {pass_count}/{len(results)} | 平均覆盖率 {avg_cov:.0f}%')
    print('━' * 66)
    print()

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
        print(f'字数覆盖率: {result["coverage_ratio"]} (TXT {result.get("txt_cn_count","?")}字 / JSON {result.get("json_cn_count","?")}字)')
        if result.get('hard_issues'):
            print('\n硬失败（需重试）:')
            for issue in result['hard_issues']:
                print(f'  - {issue}')
        if result.get('soft_issues'):
            print('\n警告（不阻断）:')
            for issue in result['soft_issues']:
                print(f'  - {issue}')
        print('=' * 60)

        # 输出质量报告表格
        print_report(result, json_path)

        if not result['pass']:
            sys.exit(1)

    elif command == 'batch_check':
        if len(sys.argv) < 4:
            print('用法: python chapter_tools.py batch_check <章节txt目录> <json目录>')
            sys.exit(1)
        txt_dir = sys.argv[2]
        json_dir = sys.argv[3]
        batch_check(txt_dir, json_dir)

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
