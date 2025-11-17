def html_table_to_markdown(table):
    """
    将bs4的<table>节点转为Markdown表格字符串
    """
    rows = table.find_all('tr')
    if not rows:
        return ''
    md_lines = []
    # 处理表头
    headers = [cell.get_text(strip=True) for cell in rows[0].find_all(['th', 'td'])]
    md_lines.append('| ' + ' | '.join(headers) + ' |')
    md_lines.append('|' + '|'.join([' --- ' for _ in headers]) + '|')
    # 处理表体
    for row in rows[1:]:
        cells = [cell.get_text(strip=True) for cell in row.find_all(['td', 'th'])]
        md_lines.append('| ' + ' | '.join(cells) + ' |')
    return '\n'.join(md_lines)
"""
site: pkulaw.com
    description: 自动检测北大法宝导出的HTML类型（论文/法规/案例），并转换为PKB规范的Markdown文件
"""
import os
import re
from bs4 import BeautifulSoup, NavigableString

# --- 配置区 ---
INPUT_HTML_FILE = 'E:/CODE/Test/Files/pkulaw.html'  # 你要处理的HTML文件
OUTPUT_DIR = 'E:/CODE/Test/Targets/'

# --- 论文处理逻辑 ---
def process_paper(soup):
    metadata = {}
    metadata['title'] = soup.find('h2', class_='title').text.strip()
    safe_title = re.sub(r'[\\/*?:"<>|\n\r\t]', "", metadata['title'])
    safe_title = re.sub(r'\s+', ' ', safe_title).strip()
    output_file = os.path.join(OUTPUT_DIR, f"{safe_title}.md")
    fields_map = {
        '作者：': 'author',
        '期刊名称：': 'journal',
        '期刊年份：': 'year',
        '期号：': 'issue',
        '关键词：': 'keywords'
    }
    for li in soup.select('.fields li'):
        key_strong = li.find('strong')
        if key_strong:
            key_text = key_strong.text.strip()
            if key_text in fields_map:
                field_name = fields_map[key_text]
                if field_name == 'keywords':
                    metadata[field_name] = [a.text.strip() for a in li.find_all('a')]
                elif field_name == 'journal':
                    box_text = li.find('div', class_='box').decode_contents()
                    match = re.search(r'《[^《》]+》', box_text)
                    if match:
                        value = match.group(0)
                        metadata[field_name] = value
                elif field_name == 'author':
                    value = li.find('div', class_='box').text.replace(key_text, '').strip()
                    authors = re.split(r'[；;\s]+', value)
                    authors = [a for a in authors if a]
                    if len(authors) > 1:
                        metadata[field_name] = authors
                    else:
                        metadata[field_name] = value
                else:
                    value = li.find('div', class_='box').text.replace(key_text, '').strip()
                    metadata[field_name] = value
    abstract = ""
    strong_abstract = soup.select_one('strong:contains("摘要：")')
    if strong_abstract:
        abstract_p = strong_abstract.find_next('p')
        if abstract_p:
            abstract = abstract_p.text.strip()
    full_text_div = soup.find('div', id='divFullText')
    footnotes = {}
    footnote_spans = full_text_div.find_all('span', class_='footnote')
    for span in footnote_spans:
        note_id = re.search(r'\[(\d+)\]', span.text)
        if note_id:
            fn_id = note_id.group(1)
            fn_content = span['content'].strip()
            footnotes[fn_id] = fn_content
            span.replace_with(f'[^{fn_id}]')
    main_body_md = []
    heading_patterns = [
        {"pattern": "^[一二三四五六七八九十]、", "level": "####"},
        {"pattern": "^（[一二三四五六七八九十]+）", "level": "#####"},
        {"pattern": "^\\d+\\.", "level": "######"}
    ]
    content_elements = full_text_div.find_all('p', recursive=False)
    for p in content_elements:
        p_text = p.text.strip()
        if not p_text or "【注释】" in p_text or "作者单位：" in p_text:
            continue
        is_heading = False
        for heading in heading_patterns:
            if re.match(heading['pattern'], p_text):
                clean_title = re.sub(heading['pattern'], '', p_text).strip()
                main_body_md.append(f"{heading['level']} {clean_title}\n")
                is_heading = True
                break
        if not is_heading:
            main_body_md.append(p_text + '\n')
    main_body_str = "\n".join(main_body_md)
    yaml_lines = ['---']
    yaml_lines.append(f"title: \"{metadata.get('title', '')}\"")
    if isinstance(metadata.get('author'), list):
        yaml_lines.append("author:")
        for a in metadata['author']:
            yaml_lines.append(f"  - {a}")
    else:
        yaml_lines.append(f"author: {metadata.get('author', '')}")
    yaml_lines.append(f"journal: {metadata.get('journal', '')}")
    yaml_lines.append(f"year: {metadata.get('year', '')}")
    yaml_lines.append(f"issue: {metadata.get('issue', '')}")
    if metadata.get('keywords'):
        yaml_lines.append("keywords:")
        for kw in metadata['keywords']:
            yaml_lines.append(f"  - {kw}")
    yaml_lines.append("tags:\n  - 文献/期刊文章")
    yaml_lines.append("Finished: false")
    yaml_lines.append('---')
    yaml_str = "\n".join(yaml_lines)
    if abstract != "":
        abstract_str = f"> [!abstract]- 摘要\n> {abstract}"
    else:
        abstract_str = ""
    footnote_lines = ['---', '### 脚注\n']
    for fn_id, fn_content in sorted(footnotes.items(), key=lambda item: int(item[0])):
        footnote_lines.append(f"[^{fn_id}]: {fn_content}\n")
    footnote_str = "\n".join(footnote_lines)
    # 查找所有表格
    tables = full_text_div.find_all('table') if full_text_div else []
    table_md = []
    for table in tables:
        md = html_table_to_markdown(table)
        if md:
            table_md.append(md)
    if table_md:
        tables_section = '\n\n---\n\n### 附表\n' + '\n\n'.join(table_md)
    else:
        tables_section = ''
    final_md_content = f"{yaml_str}\n\n{abstract_str}\n\n---\n\n#### 前言\n\n{main_body_str}\n{footnote_str}{tables_section}"
    return final_md_content, output_file

# --- 法规处理逻辑 ---
def process_regulation(soup):
    # 直接复用 regulation_process.py 里的逻辑
    # ...existing code...
    # 1. 提取元数据
    metadata = {}
    title_tag = soup.find('h2', class_='title')
    if title_tag:
        raw_title = ''.join([t for t in title_tag.contents if isinstance(t, NavigableString)]).strip()
        # 只去除文件名中最后一个括号及其内容（包括中文全角括号和英文半角括号），保留其他括号内容
        def remove_last_bracket_content(s):
            import re
            # 匹配所有全角括号
            cn = list(re.finditer(r'（([^（）]*?)）', s))
            # 匹配所有半角括号
            en = list(re.finditer(r'\(([^()]*)\)', s))
            all_brackets = cn + en
            if not all_brackets:
                return s
            # 找到最后一个括号对
            last = max(all_brackets, key=lambda m: m.start())
            content = last.group(1)
            # 判断内容是否为单个大写中文数字（如一二三四五六七八九十）
            if len(content) == 1 and content in '一二三四五六七八九十':
                return s  # 保留该括号
            return s[:last.start()] + s[last.end():]
        pure_title = remove_last_bracket_content(raw_title).strip()
    else:
        raw_title = pure_title = "未知法规"
    metadata['title'] = raw_title
    def get_field_text_by_label(label_text):
        strong_tag = soup.find('strong', string=lambda text: text and label_text in text)
        if strong_tag:
            parent_box = strong_tag.find_parent(class_='box')
            if parent_box:
                return parent_box.get_text(strip=True).replace(label_text, '').replace('：', '').strip()
        return None
    tag_map = [
        (['法律', '全国人大', '常委会'], '\n  - 规范/法律'),
        (['行政法规', '国务院'], '\n  - 规范/行政法规'),
        (['司法解释'], '\n  - 规范/司法解释'),
        (['司法解释性质文件'], '\n  - 规范/司法解释/司法解释性质文件'),
        (['两高工作文件'], '\n  - 规范/司法解释/两高工作文件'),
        (['部门规章', '部委'], '\n  - 规范/部门规章'),
        (['部门规范性文件'],'\n  - 规范/部门规章/部门规范性文件'),
        (['部门工作文件'],'\n  - 规范/部门规章/部门工作文件'),
        (['国际条约'], '#规范/国际条约'),
    ]
    drafting_body_list = []
    strong_tag = soup.find('strong', string=lambda text: text and '制定机关' in text)
    if strong_tag:
        parent_box = strong_tag.find_parent(class_='box')
        if parent_box:
            for span in parent_box.find_all('span', title=True):
                title = span.get('title', '').strip()
                if title:
                    drafting_body_list.append(f"  - {title}")
    if drafting_body_list:
        metadata['制定机关'] = '\n' + '\n'.join(drafting_body_list)
    else:
        metadata['制定机关'] = None
    metadata['发文字号'] = soup.find('li', class_='row', title=True).get('title') if soup.find('li', class_='row', title=True) else get_field_text_by_label('发文字号')
    metadata['公布日期'] = get_field_text_by_label('公布日期')
    metadata['施行日期'] = get_field_text_by_label('施行日期')
    metadata['时效性'] = get_field_text_by_label('时效性')
    eff_level = get_field_text_by_label('效力位阶')
    if eff_level:
        for keywords, tag in tag_map:
            if any(k in eff_level for k in keywords):
                metadata['tags'] = tag
                break
    pub_date = metadata.get('公布日期', '')
    date_str = ''
    if pub_date:
        m = re.search(r'(\d{4})[.\-年](\d{2})[.\-月](\d{2})', pub_date)
        if m:
            date_str = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    eff_level = metadata.get('tags', '')
    is_judicial_interpretation = False
    if eff_level and '司法解释' in eff_level:
        is_judicial_interpretation = True
    m = re.search(r'(.*?[院部会委局厅署])?关于(.*)', pure_title)
    if m:
        short_title = f"关于{m.group(2).strip()}"
        if date_str:
            final_title = f"{date_str} - {short_title}"
        else:
            final_title = short_title
    else:
        if pure_title.startswith("中华人民共和国"):
            pure_title = pure_title.replace("中华人民共和国", "").strip()
        if date_str:
            final_title = f"{date_str} - {pure_title}"
        else:
            final_title = pure_title
    metadata['title'] = final_title
    yaml_lines = ["---"]
    for key, value in metadata.items():
        if value and key != 'title':
            yaml_lines.append(f"{key}: {value}")
    yaml_lines.append("---")
    yaml_header = "\n".join(yaml_lines)
    full_text_div = soup.find('div', id='divFullText')
    if full_text_div:
        for a_tag in full_text_div.find_all('a'):
            a_tag.unwrap()
        for fb_dropdown in full_text_div.find_all(class_=['TiaoYinV2', 'c-icon']):
            fb_dropdown.decompose()
        content_parts = []
        has_tiao_wrap = any(
            hasattr(element, 'get') and element.get('class') and 'tiao-wrap' in element.get('class', [])
            for element in full_text_div.children if hasattr(element, 'get')
        )
        if has_tiao_wrap:
            for element in full_text_div.children:
                if isinstance(element, NavigableString):
                    continue
                if not hasattr(element, 'name'):
                    continue
                class_list = element.get('class', []) if element.has_attr('class') else []
                if 'navbian' in class_list:
                    content_parts.append(f"## {element.get_text(strip=True)}\n")
                elif 'navzhang' in class_list:
                    content_parts.append(f"### {element.get_text(strip=True)}\n")
                elif 'navjie' in class_list:
                    content_parts.append(f"#### {element.get_text(strip=True)}\n")
                elif 'tiao-wrap' in class_list:
                    tiao_span = element.find('span', class_='navtiao')
                    if tiao_span:
                        tiao_text = re.sub(r'\s+', ' ', tiao_span.get_text(strip=True)).strip()
                        content_parts.append(f"###### {tiao_text}")
                    for kuan_wrap in element.find_all('div', class_='kuan-wrap'):
                        kuan_texts = []
                        contents = kuan_wrap.find_all(class_=['kuan-content', 'xiang-content'])
                        for content in contents:
                            if content.find('span', class_='navtiao'):
                                content.find('span', class_='navtiao').decompose()
                            cleaned_text = content.get_text().replace('　', '  ').strip()
                            if cleaned_text:
                                kuan_texts.append(cleaned_text)
                        full_kuan_text = "\n".join(kuan_texts)
                        content_parts.append(full_kuan_text)
                    content_parts.append('')
                elif element.name == 'div' and element.get('align') == 'center':
                    content_parts.append(element.get_text(separator='\n', strip=True))
                    content_parts.append('')
                elif element.name == 'p' and element.get_text(strip=True):
                    content_parts.append(element.get_text(strip=True))
                    content_parts.append('')
        else:
            # 没有 tiao-wrap，直接查找所有 navtiao span，按条标题和正文分组
            navtiao_spans = full_text_div.find_all('span', class_='navtiao')
            for navtiao in navtiao_spans:
                tiao_text = re.sub(r'\s+', ' ', navtiao.get_text(strip=True)).strip()
                content_parts.append(f"###### {tiao_text}")
                # 收集该 span 后面紧跟的所有兄弟节点，直到下一个 navtiao 或结束
                tiao_content = []
                for sib in navtiao.next_siblings:
                    if getattr(sib, 'name', None) == 'span' and 'navtiao' in sib.get('class', []):
                        break
                    if isinstance(sib, NavigableString):
                        text = sib.strip()
                        if text:
                            tiao_content.append(text)
                    elif hasattr(sib, 'get_text'):
                        text = sib.get_text(strip=True)
                        if text:
                            tiao_content.append(text)
                if tiao_content:
                    content_parts.append("\n".join(tiao_content))
                content_parts.append('')
        main_content = "\n".join(content_parts)
        # 查找所有表格
        tables = full_text_div.find_all('table')
        table_md = []
        for table in tables:
            md = html_table_to_markdown(table)
            if md:
                table_md.append(md)
        if table_md:
            tables_section = '\n\n---\n\n### 附表\n' + '\n\n'.join(table_md)
        else:
            tables_section = ''
        main_content = main_content + tables_section
    else:
        main_content = "未能找到正文内容。"
    main_content = re.sub(r'。\n(?=.)', '。\n\n', main_content)
    final_markdown = f"{yaml_header}\n\n{main_content}"
    safe_title = re.sub(r'[\\/*?:"<>|\n\r\t]', "", final_title)
    safe_title = re.sub(r'\s+', ' ', safe_title).strip()
    output_file = os.path.join(OUTPUT_DIR, f"{safe_title}.md")
    split1 = final_markdown.find('---', final_markdown.find('---')+3)
    if split1 != -1:
        hash_pos = final_markdown.find('#', split1)
        if hash_pos != -1:
            final_markdown = final_markdown[:split1+3] + '\n' + final_markdown[hash_pos:]
    return final_markdown, output_file

# --- 案例处理逻辑 ---
def process_case(soup):
    metadata = {}
    def get_field_text(soup_obj, label_text):
        strong_tag = soup_obj.find('strong', string=lambda text: text and label_text in text)
        if strong_tag:
            parent_box = strong_tag.find_parent(class_='box')
            if parent_box:
                links = parent_box.find_all('a')
                if links:
                    return [a.get_text(strip=True) for a in links]
                else:
                    return [strong_tag.parent.get_text(strip=True).replace(label_text, '').replace('：', '').strip()]
        return []
    case_no_li = soup.find('li', title=lambda x: x and '号' in x)
    if case_no_li:
        metadata['案号'] = case_no_li.get('title', '未知案号').strip()
    else:
        case_no_span = soup.find('span', class_='case-flag self')
        metadata['案号'] = case_no_span.get_text(strip=True) if case_no_span else '未知案号'
    metadata['审理法院'] = get_field_text(soup, '审理法院')
    metadata['审结日期'] = get_field_text(soup, '审结日期')
    metadata['文书类型'] = get_field_text(soup, '文书类型')
    metadata['审理程序'] = get_field_text(soup, '审理程序')
    metadata['keywords'] = get_field_text(soup, '权责关键词')
    metadata['案件要素'] = get_field_text(soup, '案件要素')
    anyou_links = soup.find('strong', string='案由：').parent.find_all('a', class_=None)
    anyou_parts = [a.get_text(strip=True) for a in anyou_links]
    if anyou_parts:
        metadata['案由_tag'] = f"民事案由/{'/'.join(anyou_parts[1:])}"
    else:
        metadata['案由_tag'] = ""
    yaml_lines = ["---"]
    for key, values in metadata.items():
        if not values: continue
        if key.endswith('_tag'):
            yaml_lines.append("tags:")
            yaml_lines.append(f"  - {values}")
        elif isinstance(values, list):
            yaml_lines.append(f"{key}:")
            for value in values:
                yaml_lines.append(f"  - {value}")
        else:
            yaml_lines.append(f"{key}: {values}")
    yaml_lines.append("---")
    yaml_header = "\n".join(yaml_lines)
    full_text_div = soup.find('div', id='divFullText')
    if full_text_div:
        a_tags_to_merge = full_text_div.find_all('a')
        for a_tag in a_tags_to_merge:
            prev_sibling = a_tag.previous_sibling
            next_sibling = a_tag.next_sibling
            a_text = a_tag.get_text()
            if prev_sibling and isinstance(prev_sibling, NavigableString):
                combined_text = prev_sibling.string.rstrip() + a_text
                if next_sibling and isinstance(next_sibling, NavigableString):
                    combined_text += next_sibling.string.lstrip()
                    next_sibling.extract()
                prev_sibling.string.replace_with(combined_text)
                a_tag.extract()
            else:
                a_tag.replace_with(a_text)
        spans_to_merge = full_text_div.find_all('span', class_=lambda c: c and 'case-flag' in c)
        for span in spans_to_merge:
            prev_sibling = span.previous_sibling
            next_sibling = span.next_sibling
            span_text = span.get_text()
            if prev_sibling and isinstance(prev_sibling, NavigableString):
                combined_text = prev_sibling.string.rstrip() + span_text
                if next_sibling and isinstance(next_sibling, NavigableString):
                    combined_text += next_sibling.string.lstrip()
                    next_sibling.extract()
                prev_sibling.string.replace_with(combined_text)
                span.extract()
            else:
                span.replace_with(span_text)
        for span_tag in full_text_div.find_all('span', class_='anchor-case'):
            title_text = span_tag.get_text(strip=True)
            if title_text:
                span_tag.insert_before(f"\n\n##### {title_text}\n")
            span_tag.decompose()
        main_content = full_text_div.get_text(separator='\n\n', strip=True)
        main_content = main_content.replace('[', r'\[').replace(']', r'\]')
        # 查找所有表格
        tables = full_text_div.find_all('table')
        table_md = []
        for table in tables:
            md = html_table_to_markdown(table)
            if md:
                table_md.append(md)
        if table_md:
            tables_section = '\n\n---\n\n### 附表\n' + '\n\n'.join(table_md)
        else:
            tables_section = ''
        main_content = main_content + tables_section
    else:
        main_content = "未能找到正文内容。"
    final_markdown = f"{yaml_header}\n\n{main_content}"
    safe_case_title = re.sub(r'[\\/*?:"<>|\n\r\t]', "", metadata.get('案号', '未命名案例'))
    safe_case_title = re.sub(r'\s+', ' ', safe_case_title).strip()
    output_file = os.path.join(OUTPUT_DIR, f"{safe_case_title}.md")
    return final_markdown, output_file

import re
# --- 类型自动检测与主流程 ---
def detect_type_and_process(html_filepath):
    with open(html_filepath, 'r', encoding='utf-8') as f:
        html_content = f.read()
    soup = BeautifulSoup(html_content, 'lxml')
    # 优先通过法宝引证码判断类型
    citation_code = None
    # 常见引证码格式：CLI.1.153700、CLI.11.518085、CLI.WR.3553、CLI.C.375295等
    code_match = re.search(r'(CLI\.[A-Z0-9]+\.[A-Z0-9]+|CLI\.[A-Z]+\.[A-Z0-9]+|CLI\.[A-Z]+\.[A-Z0-9]+|CLI\.[A-Z]+)', html_content)
    if code_match:
        citation_code = code_match.group(0)
        # 法律法规（中央/地方法规/中外条约/外国/港澳台/年鉴/英文译本等）
        if re.match(r'CLI\.(1|2|3|11|T|FL|HK|MAC|TW|WR|N|ALE)\.', citation_code) or citation_code.startswith('CLI.WR.'):
            print(f'检测到类型：法规（引证码 {citation_code}）')
            return process_regulation(soup)
        # 案例/判决/仲裁/案例报道/检察文书/行政执法/合同范本/法律文书
        elif re.match(r'CLI\.(C|CR|AA|P|LD|ALE|CS)\.', citation_code):
            print(f'检测到类型：案例（引证码 {citation_code}）')
            return process_case(soup)
        # 期刊/文献/专家解读/律所实务/法学期刊/法学文献
        elif re.match(r'CLI\.(A|J|L|A)\.', citation_code):
            print(f'检测到类型：论文/文献（引证码 {citation_code}）')
            return process_paper(soup)
    # 如果引证码未命中，回退HTML结构判断
    # 检测论文
    if soup.find('h2', class_='title') and soup.find('div', class_='fields'):
        print('检测到类型：论文')
        return process_paper(soup)
    # 检测法规
    if soup.find('h2', class_='title') and soup.find('div', id='divFullText') and soup.find('strong', string=lambda t: t and '制定机关' in t):
        print('检测到类型：法规')
        return process_regulation(soup)
    # 检测案例
    if soup.find('h2', class_='title') and soup.find('div', id='divFullText') and soup.find('strong', string=lambda t: t and '审理法院' in t):
        print('检测到类型：案例')
        return process_case(soup)
    print('未能识别HTML类型，未处理。')
    return None, None

if __name__ == "__main__":
    if not os.path.exists(INPUT_HTML_FILE):
        print(f"错误：输入文件 '{INPUT_HTML_FILE}' 不存在。请确保该文件和脚本在同一目录下。")
    else:
        markdown_output, output_filename = detect_type_and_process(INPUT_HTML_FILE)
        if markdown_output and output_filename:
            with open(output_filename, 'w', encoding='utf-8') as f:
                f.write(markdown_output)
            print(f"🎉 成功！已将内容解析并保存为: {output_filename}")
        else:
            print("未生成任何输出。")
