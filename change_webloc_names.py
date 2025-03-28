import os
import re
import argparse
import plistlib
import requests
from bs4 import BeautifulSoup
from typing import List

PLATFORM_RULES = {
    "BILIBILI": {
        "prefix": "       Bilibili - ",
        "detect": lambda p: re.search(r'(b23\.tv|bilibili\.com)', str(p), re.I),
        "suffix_cleaner": lambda n: n.split("_哔哩哔哩bilibili")[0].split("_哔哩哔哩_bilibili")[0]
    },
    "YOUTUBE": {
        "prefix": "       YouTube - ",
        "detect": lambda p: re.search(r'(youtu\.be|youtube\.com)', str(p), re.I),
        "suffix_cleaner": lambda n: 
            n[:-8].split("• • 收看次數")[0].replace(" - YouTube", "")
    },
    "BAIKE": {
        "prefix": "       百度百科 - ",
        "detect": lambda p: re.search(r'baike\.baidu\.com', str(p), re.I),
        "suffix_cleaner": lambda n: n.replace("_百度百科", "")
    },
    "WIKIPEDIA": {
        "prefix": "       Wikipedia - ",
        "detect": lambda p: re.search(r'wikipedia\.org', str(p), re.I),
        "suffix_cleaner": lambda n: n.replace(" - 維基百科, 自由的百科全書", "").replace(" 維基百科，自由的百科全書", "")
    },
    "GEEKSFORGEEKS": {
        "prefix": "       GeeksforGeeks - ",
        "detect": lambda p: re.search(r'geeksforgeeks\.org', str(p), re.I),
        "suffix_cleaner": lambda n: n.replace(" | GeeksforGeeks", "")
    },
    "STACKOVERFLOW": {
        "prefix": "       StackOverflow - ",
        "detect": lambda p: re.search(r'stackoverflow\.com', str(p), re.I),
        "suffix_cleaner": lambda n: n.replace(" - Stack Overflow", "")
    },
    "LATEX STACK EXCHANGE": {
        "prefix": "       Latex StackExchange - ",
        "detect": lambda p: re.search(r'tex\.stackexchange\.com', str(p), re.I),
        "suffix_cleaner": lambda n: n.replace(" - TeX - LaTeX Stack Exchange", "")
    },
    "ZHIHU": {
        "prefix": "       Zhihu - ",
        "detect": lambda p: re.search(r'zhihu\.com', str(p), re.I),
        "suffix_cleaner": lambda n: n.replace(" - 知乎", "")
    },
    "CSDN": {
        "prefix": "       CSDN - ",
        "detect": lambda p: re.search(r'blog\.csdn\.net', str(p), re.I),
        "suffix_cleaner": lambda n: n.replace("-CSDN博客", "")
    },
    "HUGGINGFACE": {
        "prefix": "       HuggingFace - ",
        "detect": lambda p: re.search(r'huggingface\.co', str(p), re.I),
        "suffix_cleaner": lambda n: n
    },
    "BBC": {
        "prefix": "       BBC - ",
        "detect": lambda p: re.search(r'bbc\.com', str(p), re.I),
        "suffix_cleaner": lambda n: n.replace(" - BBC News 中文", "").replace(" - BBC News", "")
    },
    "PYTHON": {
        "prefix": "       Python - ",
        "detect": lambda p: re.search(r'python\.org', str(p), re.I),
        "suffix_cleaner": lambda n: n
    },
    "GITHUB": {
        "prefix": "       Github - ",
        "detect": lambda p: re.search(r'github\.com', str(p), re.I),
        "suffix_cleaner": lambda n: n.split(' · ')[0]
    }
}

EMOJI_PATTERN = re.compile(
    "["
    "\U0001F600-\U0001F64F"  # 表情符号
    "\U0001F300-\U0001F5FF"  # 符号和象形文字
    "\U0001F680-\U0001F6FF"  # 交通和地图符号
    "\U0001F700-\U0001F77F"  # 炼金术符号
    "\U0001F780-\U0001F7FF"  # 几何形状
    "\U0001F800-\U0001F8FF"  # 补充箭头-C
    "\U0001F900-\U0001F9FF"  # 补充符号和象形文字
    "\U0001FA00-\U0001FA6F"  # 国际象棋符号
    "\U0001FA70-\U0001FAFF"  # 符号和图形扩展-A
    "\U00002702-\U000027B0"  # 装饰符号
    "\U000024C2-\U0000257F"  # 封闭字符
    "\U00002600-\U000026FF"  # 杂项符号
    "\U00002700-\U000027BF"  # 装饰符号
    "\U0000FE00-\U0000FE0F"  # 变体选择器
    "\U0001F1E6-\U0001F1FF"  # 国旗符号
    "]+", 
    flags=re.UNICODE
)

def find_webloc_files(directory: str = ".") -> List[str]:
    """Recursively find all .webloc files in the given directory."""
    webloc_files = []
    for root, _, files in os.walk(directory):
        for file in files: 
            full_path = os.path.join(root, file)
            if (parse_webloc(full_path)): 
                webloc_files.append(full_path)
    return webloc_files

def get_webpage_title(url):
    """
    给定url, 获取网页标题
    """
    if not url: return None
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        title = soup.title.string if soup.title else None
        return title.strip() if title else None
    except Exception as e:
        print (f"获取 {url} 网页标题失败, 错误: {e}")
        return None

def parse_webloc(filepath):
    """
    Check if a file is a webloc file and return its URL if it is.
    Returns None if not a webloc file or if there's an error.
    """
    try: 
        with open(filepath, 'rb') as f:
            plist = plistlib.load(f)
            return plist.get('URL', None)
    except Exception as e: 
        return None

def main(): 
    '''
    Process webloc files in the given directory, removing duplicates.
    '''
    parser = argparse.ArgumentParser(description="Simplify filenames using OpenRouter API")
    parser.add_argument("--directory", "-d", default=".", help="Directory to search for files")
    args = parser.parse_args()
    directory = args.directory

    total_count = 0
    url_map = {}

    # Find all .webloc files
    print(f"Searching for .webloc files in {args.directory}")
    valid_webloc_files = find_webloc_files(args.directory)
    if not valid_webloc_files:
        print("No valid .webloc files found.")
        return
    
    file_length = len(valid_webloc_files)
    print(f"Found {file_length} valid .webloc files.")

    failed_instances = []
    for id, filepath in enumerate(valid_webloc_files): 
        print (f"\n{id+1}/{file_length}: '{filepath}'")
        url = parse_webloc(filepath)
        if url:  # Only process if we got a valid URL
            total_count += 1 

            try: 
                # Step 1: Clean up duplicate URLs
                if (url.startswith("https://www.youtube.com/watch?")):
                    url = url.split('&pp')[0]
                if (url.startswith("https://www.bilibili.com/video/")):
                    url = url.split('&vd_source=')[0].split('?vd_source=')[0].split('?spm_id_from=')[0]
                print (f"[Step 1] 处理文件: {filepath}\n         有效URL: {url}")
                if url in url_map:
                    print(f"=> 删除 (与文件 '{os.path.basename(url_map[url])}' 的url: {url} 重复)")
                    os.remove(filepath)
                    continue
                else: url_map[url] = filepath

                # Step 2: Rename files based on webpage title
                title = get_webpage_title(url)
                if not title: 
                    step_2_filename = os.path.basename(filepath)
                    step_2_filepath = filepath
                    print(f"[Step 2] 无法获取标题, 跳过重命名步骤: {filepath}")
                else: 
                    title = title.replace('/', '_').replace(':', '：').replace(' - ', ' ').replace(' | ', ' ').replace('｜', ' ').replace('?', '').replace('!', '').replace('- ', ' ').replace(' -', ' ')
                    print(f"[Step 2] 获取到标题: '{title}'")
                    step_2_filename = title
                    max_length = 255 - len(".webloc") - len(os.path.dirname(filepath))
                    if (len(step_2_filename) > max_length):
                        step_2_filename = step_2_filename[:max_length]
                        print (f"         文件名过长, 截断为: '{step_2_filename}'")
                    step_2_filepath = os.path.join(os.path.dirname(filepath), step_2_filename)
                    try:
                        os.rename(filepath, step_2_filepath)
                        print(f"         标题重命名: {step_2_filename}")
                    except Exception as e:
                        print(f"         重命名失败, 错误: {e}")
                
                # Step 3: Hard-configured processing
                step_3_filename = step_2_filename
                step_3_filename = step_3_filename.replace("?", "").replace("!", "").replace("/", "").replace("　", " ")
                step_3_filename = EMOJI_PATTERN.sub('', step_3_filename)
                print(f"[Step 3] 基本重命名: {step_3_filename}")
                for web, rule in PLATFORM_RULES.items():
                    if rule["detect"](url): 
                        print (f"         匹配网站: {web}")
                        if not step_2_filename.startswith(rule["prefix"]):
                            step_3_filename = rule["prefix"] + step_3_filename.split(' - ')[-1]
                        if rule["suffix_cleaner"]:
                            step_3_filename = rule["suffix_cleaner"](step_3_filename)
                        print (f"         网站重命名: '{step_3_filename}'")
                        break
                else: 
                    step_3_filename = "       Link - " + step_2_filename.split(' - ')[-1]
                    print (f"         其它网页链接, 前面增加Link标记。")
                max_length = 255 - len(".webloc") - len(os.path.dirname(step_2_filepath))
                if (len(step_3_filename) > max_length):
                    step_3_filename = step_3_filename[:max_length]
                    print (f"         文件名过长, 截断为: '{step_3_filename}'")
                step_3_filepath = os.path.join(os.path.dirname(step_2_filepath), step_3_filename)
                if (not step_3_filepath.endswith(".webloc")):
                    step_3_filepath += ".webloc"
                step_3_filename = os.path.basename(step_3_filepath)
                print (f"         最终重命名: '{step_3_filename}'")
                os.rename(step_2_filepath, step_3_filepath)
            except Exception as e:
                print(f"         处理失败: {filepath}, 错误: {e}")
                failed_instances.append(filepath)
    
    print(f"\n处理完成！共处理 {total_count} 个webloc文件。")
    if failed_instances:
        display_text = '\n'.join(failed_instances)
        print(f"处理失败的文件: \n{display_text}")

if __name__ == "__main__":
    main()
