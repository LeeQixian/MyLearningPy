import os
from pathlib import Path

# --- 配置区 ---
ROOT_DIR = '.'
OUTPUT_FILE = './structure_report.md'
IGNORE_LIST = {
    '.obsidian', '.git', '.trash', '__pycache__', 'analyze_structure.py', 
    'structure_report.md', '.DS_Store', 'desktop.ini',
    'site-packages', 'Scripts', 'Include', 'Lib', 'pyvenv.cfg', # 排除Python虚拟环境
}

# --- 脚本主代码 ---

def generate_tree_recursive(directory, prefix=''):
    """递归生成目录树的函数"""
    contents = list(Path(directory).iterdir())
    # 筛选掉需要忽略的文件/文件夹
    pointers = [
        item for item in contents if item.name not in IGNORE_LIST
    ]
    # 排序以保证输出一致性
    pointers.sort(key=lambda x: (x.is_file(), x.name.lower()))

    lines = []
    for i, path in enumerate(pointers):
        # 判断是否是最后一个元素，以决定用 '└──'还是 '├──'
        connector = '└── ' if i == len(pointers) - 1 else '├── '
        lines.append(f"{prefix}{connector}{path.name}{'/' if path.is_dir() else ''}")

        if path.is_dir():
            # 为下一层生成新的前缀
            extension = '    ' if i == len(pointers) - 1 else '│   '
            lines.extend(generate_tree_recursive(path, prefix=prefix + extension))
    return lines

def run_analysis():
    """主执行函数"""
    print("🚀 开始分析您的文件结构...")
    try:
        root_path = Path(ROOT_DIR)
        header = (
            f"# 我的知识库结构报告\n\n"
            f"根目录: `{root_path.resolve()}`\n\n"
            "```\n"
            f"{root_path.name}/\n"
        )
        
        tree_lines = generate_tree_recursive(root_path)
        
        report_content = header + "\n".join(tree_lines) + "\n```"
        
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        print(f"✅ 成功！结构报告已保存到: {OUTPUT_FILE}")

    except Exception as e:
        print(f"❌ 失败！发生错误: {e}")

if __name__ == '__main__':
    run_analysis()