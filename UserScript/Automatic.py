from bs4 import BeautifulSoup, NavigableString
import re
from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import os


options = Options()
options.binary_location = r'D:\Firefox Developer Edition\firefox.exe'  # 修改为你的实际路径

service = Service(executable_path='E:\\CODE\\geckodriver.exe')
driver = webdriver.Firefox(service=service, options=options)
import re
driver.get('https://www.pkulaw.com/chl/3b70bb09d2971662bdfb.html?way=listView')  # 替换为你的目标页面

# 2. 注入并执行 history.js
time.sleep(3)  # 等待页面加载

# --------- history.js核心逻辑（Python实现） ---------
# 1. 寻找“本法变迁”区域
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException

version_ids = []
try:
    title_div = driver.find_element(By.CSS_SELECTOR, 'div.change-title')
    if title_div.text.strip() == '本法变迁':
        target_box = title_div.find_element(By.XPATH, 'following-sibling::div[@class="box"]')
        compare_links = target_box.find_elements(By.CSS_SELECTOR, 'ul li div.theme a.lawChange.contrast')
        regex_compare_id = re.compile(r'/compare/.*-(.*)\.html')
        for link in compare_links:
            href = link.get_attribute('href')
            if href:
                match = regex_compare_id.search(href)
                if match:
                    version_ids.append(match.group(1))
except NoSuchElementException:
    print('未找到“本法变迁”模块或内容区域，脚本终止。')
    driver.quit()
    exit()

# 2. 获取当前页面ID，去重并排除当前ID
current_id = None
regex_current_id = re.compile(r'chl/(.*?)\.html')
current_url_match = regex_current_id.search(driver.current_url)
if current_url_match:
    current_id = current_url_match.group(1)
unique_ids = list(set(version_ids))
final_ids_to_open = [id for id in unique_ids if id != current_id]

print(f'将打开 {len(final_ids_to_open)} 个历史版本页面...')

# 3. 批量打开所有历史版本页面（新标签页）
for id in final_ids_to_open:
    url = f'https://www.pkulaw.com/chl/{id}.html?way=listView'
    driver.execute_script(f"window.open('{url}', '_blank');")
    time.sleep(0.5)  # 可调整批量打开速度

time.sleep(5)  # 等待所有标签页加载
def parse_regulation_to_markdown(html_filepath):

    print(f"开始处理文件: {html_filepath}")

    try:
        with open(html_filepath, 'r', encoding='utf-8') as f:
            html_content = f.read()
    except FileNotFoundError:
        return f"错误：找不到文件 {html_filepath}。", "error.md"

    soup = BeautifulSoup(html_content, 'lxml')

    # --- 1. & 2. YAML元数据部分 (无改动) ---
    metadata = {}
    title_tag = soup.find('h2', class_='title')
    if title_tag:
        # 只取h2本身的直接文本，不包含a等子标签内容
        raw_title = ''.join([t for t in title_tag.contents if isinstance(t, NavigableString)]).strip()
        # 去掉括号及括号内内容
        pure_title = re.sub(r'（.*?）|\(.*?\)', '', raw_title).strip()
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

    # 效力位阶与标签映射表
    tag_map = [
        (['法律', '全国人大', '常委会'], '\n  - 规范/法律'),
        (['行政法规', '国务院'], '\n  - 规范/行政法规'),
        (['司法解释', '最高法', '最高检'], '\n  - 规范/司法解释'),
        (['部门规章', '部委'], '\n  - 规范/部门规章'),
        (['地方性法规', '地方人大'], '\n  - 规范/地方性法规'),
        (['地方政府规章'], '\n  - 规范/地方政府规章'),
        (['国际条约'], '#规范/国际条约'),
    ]

    drafting_body = get_field_text_by_label('制定机关')
    if drafting_body:
        # 将制定机关以顿号分隔，并格式化为列表项
        drafting_body_list = [f"\n  - {item.strip()}" for item in drafting_body.split('、') if item.strip()]
        metadata['制定机关'] = "\n".join(drafting_body_list)
    else:
        metadata['制定机关'] = None
    metadata['发文字号'] = soup.find('li', class_='row', title=True).get('title') if soup.find('li', class_='row', title=True) else get_field_text_by_label('发文字号')
    metadata['公布日期'] = get_field_text_by_label('公布日期')
    metadata['施行日期'] = get_field_text_by_label('施行日期')
    metadata['时效性'] = get_field_text_by_label('时效性')


    # 获取效力位阶并匹配标签
    eff_level = get_field_text_by_label('效力位阶')
    if eff_level:
        for keywords, tag in tag_map:
            if any(k in eff_level for k in keywords):
                metadata['tags'] = tag
                break

    # 公布日期处理，生成 [YYYY-MM-DD] 格式
    pub_date = metadata.get('公布日期', '')
    date_str = ''
    if pub_date:
        m = re.search(r'(\d{4})[.\-年](\d{2})[.\-月](\d{2})', pub_date)
        if m:
            date_str = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"

    # 生成最终title，命名逻辑：有公布日期则为 [YYYY-MM-DD] 法规名，否则为法规名
    if date_str:
        final_title = f"[{date_str}] {pure_title}"
    else:
        final_title = pure_title

    metadata['title'] = final_title
    
    yaml_lines = ["---"]
    for key, value in metadata.items():
        if value and key != 'title':
            yaml_lines.append(f"{key}: {value}")
    yaml_lines.append("---")
    yaml_header = "\n".join(yaml_lines)

    # --- 3. 处理正文内容 ---
    full_text_div = soup.find('div', id='divFullText')
    
    if full_text_div:
        # 预处理部分 (无改动)
        for a_tag in full_text_div.find_all('a'):
            a_tag.unwrap()
        for fb_dropdown in full_text_div.find_all(class_=['TiaoYinV2', 'c-icon']):
            fb_dropdown.decompose()
        
        content_parts = []

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
                
                # 遍历条文下的每一个“款”(<div class="kuan-wrap">)
                for kuan_wrap in element.find_all('div', class_='kuan-wrap'):
                    kuan_texts = []
                    # 找到“款”内部所有的内容块 (款自身内容 + 所有项的内容)
                    contents = kuan_wrap.find_all(class_=['kuan-content', 'xiang-content'])
                    for content in contents:
                        # 清理每个块内部的文本
                        if content.find('span', class_='navtiao'):
                            content.find('span', class_='navtiao').decompose()
                        
                        cleaned_text = content.get_text().replace('　', '  ').strip()
                        if cleaned_text:
                            kuan_texts.append(cleaned_text)
                    
                    # 将一款内的所有内容用换行符连接成一个整体
                    full_kuan_text = "\n".join(kuan_texts)
                    content_parts.append(full_kuan_text)
                
                content_parts.append('') # 每个法条结束后加一个空行

            elif element.name == 'div' and element.get('align') == 'center':
                 content_parts.append(element.get_text(separator='\n', strip=True))
                 content_parts.append('')
            elif element.name == 'p' and element.get_text(strip=True):
                 content_parts.append(element.get_text(strip=True))
                 content_parts.append('')

        main_content = "\n".join(content_parts)

    else:
        main_content = "未能找到正文内容。"
        
    # --- 4. 组合并返回最终结果 (无改动) ---
    # 处理完后，正则将。\n.替换为。\n\n.，实现分段
    main_content = re.sub(r'。\n(?=.)', '。\n\n', main_content)
    final_markdown = f"{yaml_header}\n\n{main_content}"

    safe_title = re.sub(r'[\\/*?:"<>|]', "", final_title)
    output_filename = f"./Processor/{safe_title}.md"
    
    # 替换第二个'---'后到第一个'#'之间的内容为\n
    split1 = final_markdown.find('---', final_markdown.find('---')+3)
    if split1 != -1:
        hash_pos = final_markdown.find('#', split1)
        if hash_pos != -1:
            final_markdown = final_markdown[:split1+3] + '\n' + final_markdown[hash_pos:]
    return final_markdown, output_filename

# 4. 遍历所有标签页，抓取 HTML 并解析

def wait_for_page_loaded(driver, timeout=15):
    try:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.ID, 'divFullText'))
        )
        return True
    except Exception:
        return False

print('等待所有标签页加载完毕...')
for handle in driver.window_handles:
    driver.switch_to.window(handle)
    loaded = wait_for_page_loaded(driver, timeout=20)
    if not loaded:
        print(f"标签页 {driver.current_url} 加载超时，跳过。")
        continue
    html = driver.page_source
    temp_html_path = 'temp_regulation.html'
    with open(temp_html_path, 'w', encoding='utf-8') as f:
        f.write(html)

    markdown, output_filename = parse_regulation_to_markdown(temp_html_path)
    with open(output_filename, 'w', encoding='utf-8') as f:
        f.write(markdown)
    print(f"已保存: {output_filename}")

driver.quit()