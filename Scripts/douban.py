"""
site: douban.com
    description: 将从豆瓣读书导出的HTML格式论文转换为符合PKB规范的Markdown文件
"""


import re
from bs4 import BeautifulSoup

def parse_douban_html(html_content):
    """
    解析豆瓣读书页面的HTML，提取书籍信息并生成Markdown格式的笔记。
    """
    soup = BeautifulSoup(html_content, 'lxml')
    
    # --- 1. 提取书籍元数据 ---
    info_div = soup.find('div', id='info')
    if not info_div:
        print("错误：未找到书籍信息区域 (div#info)。")
        return None

    # 辅助函数，用于安全地提取信息
    def get_info_text(label):
        tag = info_div.find('span', string=re.compile(label))
        if tag:
            # 优先查找a标签
            a_tag = tag.find_next('a')
            if a_tag and a_tag.parent == tag.parent:
                return a_tag.get_text(strip=True)
            # .next_sibling 可能会是换行符或空格，需要循环查找下一个有效节点
            next_s = tag.next_sibling
            while next_s and isinstance(next_s, str) and not next_s.strip():
                next_s = next_s.next_sibling
            if next_s:
                return next_s.get_text(strip=True) if getattr(next_s, 'name', None) == 'a' else next_s.strip()
        return None
        
    def get_all_info_texts(label):
        tags = info_div.find_all('span', string=re.compile(label))
        if tags:
            # 找到最后一个匹配的标签（通常是作者/译者）
            tag = tags[-1]
            # 查找该标签后的所有 a 标签兄弟节点
            translators = [a.get_text(strip=True) for a in tag.find_next_siblings('a')]
            return translators
        return []

    title = soup.find('span', property='v:itemreviewed').get_text(strip=True)
    author = get_info_text('作者')
    publisher = get_info_text('出版社')
    subtitle = get_info_text('副标题')
    producer = get_info_text('出品方') # 有些书有出品方
    series = get_info_text('丛书')
    original_title = get_info_text('原作名')
    translators = get_all_info_texts('译者')
    publish_date = get_info_text('出版年')
    isbn = get_info_text('ISBN')
    
    # 封面图片链接（取img的src）
    cover_tag = soup.find('a', class_='nbg')
    cover_url = ''
    if cover_tag:
        img_tag = cover_tag.find('img')
        if img_tag and img_tag.has_attr('src'):
            cover_url = img_tag['src']

    # --- 2. 提取目录 ---
    # 目录的div id是动态的，但通常以'dir_'开头，以'_full'结尾
    toc_div = soup.find('div', id=lambda x: x and x.startswith('dir_') and x.endswith('_full'))
    toc_markdown = ""
    if toc_div:
        # 使用get_text并指定分隔符，将<br>替换为换行
        toc_text = toc_div.get_text(separator='\n', strip=True)
        toc_lines = toc_text.splitlines()
        # 转换成Markdown任务列表格式
        toc_markdown_list = [f"- [ ] {line.strip()}" for line in toc_lines if line.strip()]
        toc_markdown = '\n'.join(toc_markdown_list)
    else:
        toc_markdown = "# 目录\n\n(未在该页面找到目录信息)"


    # --- 3. 组合成最终的Markdown文件内容 ---
    
    # 构建YAML Frontmatter
    yaml_header = "---\n"
    yaml_header += f"title: {title}\n"
    if author:
        # 正则表达式去除作者国籍信息如 "[美] "
        cleaned_author = re.sub(r'^\[.*?\]\s*', '', author)
        yaml_header += f"author: {cleaned_author}\n"
    if subtitle:
        yaml_header += f"subtitle: {subtitle}\n"
    if publisher:
        yaml_header += f"publisher: {publisher}\n"
    if producer:
        yaml_header += f"producer: {producer}\n"
    if original_title:
        yaml_header += f'原作名: "{original_title}"\n' # 引号防止特殊字符问题
    if series:
        yaml_header += f"series: {series}\n"
    if publish_date:
        yaml_header += f"publishDate: {publish_date}\n"
    if isbn:
        yaml_header += f'ISBN: "{isbn}"\n'
    if translators:
        yaml_header += "译者:\n"
        for translator in translators:
            yaml_header += f"  - {translator}\n"
    
    yaml_header += "tags:\n  - 阅读\n"
    yaml_header += f"cover: {cover_url}\n"
    yaml_header += "Finished: false\n"
    yaml_header += "---\n\n"

    # 组合最终内容
    final_content = yaml_header + toc_markdown
    
    return title, final_content


if __name__ == "__main__":
    # 定义输入和输出文件名
    input_html_file = 'E:/CODE/Test/Files/douban.html'
    
    try:
        with open(input_html_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
            
        title, markdown_content = parse_douban_html(html_content)
        
        if title and markdown_content:
            # 清理文件名中的非法字符
            safe_title = re.sub(r'[\\/*?:"<>|]', "", title)
            output_md_file = f"E:/CODE/Test/Targets/{safe_title}.md"
            
            with open(output_md_file, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
                
            print(f"🎉 成功！已为你生成知识卡片：'{output_md_file}'")

    except FileNotFoundError:
        print(f"错误：找不到文件 '{input_html_file}'。请确保它和脚本在同一个文件夹里。")
    except Exception as e:
        print(f"发生了一个错误：{e}")