"""
site: icourse163.org
	description: 下载网易云课堂视频，支持多线程和断点续传，自动转码为mp4格式。
"""
import requests
from tqdm import tqdm
import re
import ast
import json
import time
import hashlib
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
# 首先准备好cookie和请求头.

with open(r"e:\\CODE\\Test\\Files\\Cookies.json", "r", encoding="utf-8") as f:
    Cookies = json.load(f)

headers = {
	"Referer": "https://www.icourse163.org/learn/XHUN-1466082193?tid=1473254527",
	"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:146.0) Gecko/20100101 Firefox/146.0"
}

def get_csrfkey(cookies):
	csrfkey = ""
	for key, value in cookies.items():
		if key == "NTESSTUDYSI":
			csrfkey = value
			break
	return csrfkey

# 此时已经获得tid和csrfkey
tid = 1473254527
csrfkey = get_csrfkey(Cookies)

# 考虑到可能出岔子,先获取整个学期的课程分布
def term_avail(csrfkey,tid):
	data = {"termId": f"{tid}"}
	response = requests.post(f"https://www.icourse163.org/web/j/courseBean.getLastLearnedMocTermDto.rpc?csrfKey={csrfkey}",headers=headers, data=data,cookies=Cookies)
	response.close()
	response = response.text
	return response

term_data = term_avail(csrfkey,tid)

def get_chapters(term_data):
	term_json = json.loads(term_data)
	chapter = str(term_json["result"]["mocTermDto"]["chapters"])
	return chapter

chapter = get_chapters(term_data)
data = ast.literal_eval(chapter)
data = json.loads(json.dumps(data, indent=2, ensure_ascii=False))

def get_video_content_ids(data):
	"""
	Traverse the chapters/lessons/units structure and return a list of all contentId bizid, names.
	"""
	content_ids = []
	bizids = []
	names = []
	seq_pattern = re.compile(r'^(第?([一二三四五六七八九十百千万0-9]+)[讲节章课单元回])|^([0-9]+(\.[0-9]+)*|[一二三四五六七八九十百千万]+)[、.．\s-]*|[?？\\\/:*"<>\|]')
	unit_num = 1
	for chapter in data:
		lessons = chapter.get("lessons")
		if not lessons:
			continue
		lessen_num = 1
		for lesson in lessons:
			for unit in lesson.get("units", []):
				if unit.get("contentType") == 1 and unit.get("contentId") is not None:
					content_ids.append(unit["contentId"])
					bizids.append(unit["id"])
					raw_name = unit['name']
					name = seq_pattern.sub('', raw_name).strip()
					names.append(f"{unit_num}.{lessen_num} {name}")
			lessen_num += 1
		unit_num += 1
	return content_ids, bizids, names

videoids, bizids, names = get_video_content_ids(data)

def get_signature(bizid,csrfkey):
	string = f"{bizid}1{int(time.time() * 1000)}881mooc1543989727"
	sign = hashlib.md5(string.encode('utf-8')).hexdigest()
	timestamp = int(time.time() * 1000)
	params2 = {
		"bizId": bizid,
		"bizType": "1",
		"contentType": "1",
		"sign": sign,
		"timestamp": timestamp
	}
	url = f"https://www.icourse163.org/web/j/resourceRpcBean.getResourceTokenV2.rpc?csrfKey={csrfkey}"
	resp=requests.post(url,headers=headers,data=params2,cookies=Cookies)
	resp.close()
	resp_json=resp.json()
	if resp_json['code'] == 0:
		signature = resp_json['result']['videoSignDto']['signature']
		return signature
	else:
		return None

def get_video_link(videoid,signature):
	baseurl = "https://vod.study.163.com/eds/api/v1/vod/video"
	params = {"videoId": videoid,
			  "signature": signature,
			  "clientType": 1}
	videoreq = requests.get(baseurl,params = params, cookies= Cookies, headers=headers)
	if videoreq.json()['code'] == 0:
		return videoreq.json()['result']['videos'][0]['videoUrl']
	else:
		print("链接获取失败!")

def m3u8_2_mp4(m3u8_link, filename):
	import subprocess
	target_dir = "E:\\CODE\\Test\\Targets"
	os.makedirs(target_dir, exist_ok=True)
	filepath = os.path.join(target_dir, filename)
	ts_path = filepath + ".ts"
	m3u8_baseurl = m3u8_link.rsplit('/', 1)[0] + '/'
	m3u8_req = requests.get(m3u8_link, headers=headers, cookies=Cookies)
	# 只保留以.ts结尾的行，忽略其它内容
	ts_names = [line.strip() for line in m3u8_req.text.splitlines() if line.strip() and not line.startswith('#') and line.strip().endswith('.ts')]
	ts_links = [m3u8_baseurl + name for name in ts_names]
	with open(ts_path, 'wb') as outf:
		for link in tqdm(ts_links,desc=filename.rsplit('\\', 1)[-1], leave=False):
			r = requests.get(link, headers=headers, cookies=Cookies, stream=True)
			outf.write(r.content)
	print(f"{ts_path} 下载完成，开始转码为mp4...")
	# ffmpeg转码
	try:
		cmd = [
			"ffmpeg", "-y", "-i", ts_path,
			"-c", "copy", "-bsf:a", "aac_adtstoasc", filepath
		]
		subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
		print(f"{filepath} 转码完成！")
		os.remove(ts_path)
	except Exception as e:
		print(f"ffmpeg转码失败: {e}")

def check_downloaded():
	"""
	Check the Target directory for downloaded .mp4 files and return their filenames in a set (不含扩展名)。
	"""
	target_dir = r"E:\\CODE\\Test\\Targets"
	if not os.path.exists(target_dir):
		return set()
	downloaded_files = {file.rsplit('.mp4', 1)[0] for file in os.listdir(target_dir) if file.endswith('.mp4')}
	return downloaded_files

def download_one(videoid, name, max_retry=3):
	target_dir = r"E:\\CODE\\Test\\Targets"
	for attempt in range(max_retry):
		try:
			downloaded = check_downloaded()
			if name in downloaded:
				return 'exists'  # 不打印，交由外部统计
			signature = get_signature(bizids[videoids.index(videoid)], csrfkey)
			m3u8_link = get_video_link(videoid, signature)
			if m3u8_link:
				print(f"正在下载: {name}.mp4")
				m3u8_2_mp4(m3u8_link, f"{target_dir}\\{name}.mp4")
				return 'success'
			else:
				time.sleep(2)
		except Exception as e:
			print(f"{name} 下载出错: {e}，重试({attempt+1}/{max_retry})")
			time.sleep(2)
	# 删除失败的文件（如果存在）
	filepath = os.path.join(target_dir, f"{name}.mp4")
	if os.path.exists(filepath):
		os.remove(filepath)
	return 'fail'

def batch_download_with_retry(videoids, names, max_workers=5, max_retry=3):
	to_download = list(zip(videoids, names))
	all_exists = set()
	all_success = set()
	for round_num in range(max_retry):
		print(f"第{round_num+1}轮下载，待下载数量：{len(to_download)}")
		failed = []
		with ThreadPoolExecutor(max_workers=max_workers) as executor:
			futures = {executor.submit(download_one, vid, name, 1): (vid, name) for vid, name in to_download}
			for future in as_completed(futures):
				vid, name = futures[future]
				result = future.result()
				if result == 'exists':
					all_exists.add(name)
				elif result == 'success':
					all_success.add(name)
				else:
					failed.append((vid, name))
		# 关键：每轮后刷新已下载
		downloaded = check_downloaded()
		to_download = [(vid, name) for vid, name in failed if name not in downloaded]
		if not to_download:
			break
	# 统一打印统计
	if all_exists:
		print(f"已存在（跳过）: {sorted(all_exists)}")
	if all_success:
		print(f"本次成功下载: {sorted(all_success)}")
	if to_download:
		print("以下视频多次重试仍失败：", [name for _, name in to_download])

# 用法
batch_download_with_retry(videoids, names, max_workers=5, max_retry=3)