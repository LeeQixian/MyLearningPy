
// ==UserScript==
// @name         网页内容一键复制（PKUlaw & Douban）
// @namespace    https://github.com/LeeQixian/MyLearningPy
// @version      1.0.1
// @description  在 PKUlaw 和豆瓣图书页面，左上角显示悬浮按钮，点击即复制目标内容 HTML。
// @author       LeeQixian
// @icon         https://www.douban.com/favicon.ico
// @match        https://www.pkulaw.com/*
// @match        https://book.douban.com/subject/*
// @grant        none
// @run-at       document-end
// @license      MIT
// @updateURL    https://raw.githubusercontent.com/LeeQixian/MyLearningPy/main/Test/UserScript/copyHTML.js
// @downloadURL  https://raw.githubusercontent.com/LeeQixian/MyLearningPy/main/Test/UserScript/copyHTML.js
// ==/UserScript==

(function () {
	'use strict';

	// 配置每个站点的目标选择器和内容提取逻辑
	const configs = [
		{
			name: 'PKUlaw',
			test: () => location.hostname.includes('pkulaw.com'),
			findContent: () => {
				const el = document.querySelector('div.content');
				return el ? el.outerHTML : '';
			},
		},
		{
			name: 'DoubanBook',
			test: () => location.hostname.includes('douban.com') && location.pathname.startsWith('/subject/'),
			findContent: () => {
				const wrapper = document.querySelector('div#wrapper');
				if (!wrapper) return '';
				const h1 = wrapper.querySelector('h1');
				const content = wrapper.querySelector('#content');
				const h1html = h1 ? h1.outerHTML : '';
				const contenthtml = content ? content.outerHTML : '';
				return h1html + '\n' + contenthtml;
			},
		},
	];

	const BUTTON_ID = 'unified-copy-btn-v1';

	function createButton() {
		if (document.getElementById(BUTTON_ID)) return document.getElementById(BUTTON_ID);
		const btn = document.createElement('button');
		btn.id = BUTTON_ID;
		btn.type = 'button';
		btn.title = '点击复制 HTML内容';
		btn.textContent = '复制内容HTML';
		Object.assign(btn.style, {
			position: 'fixed',
			left: '16px',
			top: '16px',
			zIndex: 2147483647,
			padding: '8px 12px',
			borderRadius: '8px',
			border: '1px solid rgba(0,0,0,0.15)',
			background: 'white',
			boxShadow: '0 6px 18px rgba(0,0,0,0.12)',
			cursor: 'pointer',
			fontSize: '13px',
			color: '#111',
			opacity: '0.97',
		});
		const hint = document.createElement('span');
		hint.id = BUTTON_ID + '-hint';
		hint.style.marginLeft = '8px';
		hint.style.fontSize = '12px';
		hint.style.opacity = '0.9';
		btn.appendChild(hint);
		// 右键移除按钮
		btn.addEventListener('contextmenu', (e) => {
			e.preventDefault();
			btn.remove();
		});
		return btn;
	}

	function showHint(text) {
		const hint = document.getElementById(BUTTON_ID + '-hint');
		if (!hint) return;
		hint.textContent = ' ' + text;
		clearTimeout(hint._timer);
		hint._timer = setTimeout(() => { hint.textContent = ''; }, 2000);
	}

	async function copyToClipboard(text) {
		try {
			if (navigator.clipboard && navigator.clipboard.writeText) {
				await navigator.clipboard.writeText(text);
				return true;
			} else {
				const ta = document.createElement('textarea');
				ta.value = text;
				ta.style.position = 'fixed';
				ta.style.left = '-9999px';
				document.body.appendChild(ta);
				ta.select();
				const ok = document.execCommand('copy');
				document.body.removeChild(ta);
				return ok;
			}
		} catch (e) {
			console.error('复制失败：', e);
			return false;
		}
	}

	// 主逻辑：检测页面类型，挂载按钮并绑定事件
	function attachWhenReady() {
		const config = configs.find(cfg => cfg.test());
		if (!config) return false;
		let btn = createButton();
		if (!btn.parentElement) document.body.appendChild(btn);
		btn.onclick = async () => {
			try {
				const content = config.findContent();
				if (!content) {
					showHint('未找到内容');
					return;
				}
				const ok = await copyToClipboard(content);
				if (ok) {
					showHint('已复制 HTML');
				} else {
					showHint('复制失败');
				}
			} catch (err) {
				console.error(err);
				showHint('复制出错');
			}
		};
		return true;
	}

	// 首次尝试
	if (!attachWhenReady()) {
		// 若未找到，监听 DOM 变化（动态加载）
		const mo = new MutationObserver((mutations, observer) => {
			if (attachWhenReady()) {
				observer.disconnect();
			}
		});
		mo.observe(document.documentElement || document.body, { childList: true, subtree: true });
		// 后备停止观察（30 秒）
		setTimeout(() => mo.disconnect(), 30000);
	}
	// 支持单页路由
	window.addEventListener('hashchange', () => setTimeout(() => attachWhenReady(), 200));
	window.addEventListener('popstate', () => setTimeout(() => attachWhenReady(), 200));
})();
