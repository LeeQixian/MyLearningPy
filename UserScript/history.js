// ==UserScript==
// @name         北大法宝·本法变迁一键打开
// @namespace    https://github.com/LeeQixian/MyLearningPy
// @version      1.1.2
// @description  在北大法宝的法律详情页，于“本法变迁”处添加一个按钮，用于一键在新标签页中打开所有历史版本的法规。
// @author       LeeQixian
// @icon         https://www.pkulaw.com/favicon.ico
// @match        https://www.pkulaw.com/chl/*.html*
// @grant        GM_openInTab
// @license      MIT
// @updateURL    https://raw.githubusercontent.com/LeeQixian/MyLearningPy/main/Test/UserScript/history.js
// @downloadURL  https://raw.githubusercontent.com/LeeQixian/MyLearningPy/main/Test/UserScript/history.js
// ==/UserScript==

(function() {
    'use strict';

    // 1. 寻找核心区域
    const titleDiv = document.querySelector('div.change-title');
    if (!titleDiv || titleDiv.textContent.trim() !== '本法变迁') {
        // 如果页面上没有“本法变迁”模块，则不执行任何操作
        console.log('未找到“本法变迁”模块，脚本终止。');
        return;
    }

    const targetBox = titleDiv.nextElementSibling;
    if (!targetBox || !targetBox.classList.contains('box')) {
        // 如果“本法变迁”后面没有紧跟着的 div.box，也终止
        console.log('未找到“本法变迁”模块的内容区域，脚本终止。');
        return;
    }

    // 2. 提取所有历史版本的正文链接
    const versionLinks = [];
    const themeDivs = targetBox.querySelectorAll('ul li div.theme');
    themeDivs.forEach(themeDiv => {
        const a = themeDiv.querySelector('a[href^="/chl/"]');
        if (a) {
            versionLinks.push('https://www.pkulaw.com' + a.getAttribute('href'));
        }
    });

    if (versionLinks.length === 0) {
        console.log('未找到任何历史版本正文链接。');
        return;
    }

    // 3. 处理数据：去重并排除当前页面
    // 3.1 获取当前页面的正文链接
    let currentLawUrl = null;
    const regexCurrentLaw = /\/chl\/([a-zA-Z0-9]+)\.html/;
    const currentLawMatch = window.location.href.match(regexCurrentLaw);
    if (currentLawMatch && currentLawMatch[0]) {
        currentLawUrl = 'https://www.pkulaw.com' + currentLawMatch[0];
    }

    // 3.2 去重并过滤
    const uniqueLinks = [...new Set(versionLinks)];
    const finalLinksToOpen = uniqueLinks.filter(link => link !== currentLawUrl);

    // 4. 创建并注入UI（按钮）
    const button = document.createElement('button');
    button.textContent = `一键打开所有历史版本 (${finalLinksToOpen.length})`;
    button.title = '在新标签页中打开本法的所有其他历史版本';
    // 添加一些样式，使其看起来更和谐
    Object.assign(button.style, {
        marginLeft: '20px',
        padding: '4px 12px',
        fontSize: '14px',
        cursor: 'pointer',
        border: '1px solid #ccc',
        borderRadius: '4px',
        backgroundColor: '#f0f0f0',
        color: '#333'
    });
    button.onmouseover = () => button.style.backgroundColor = '#e0e0e0';
    button.onmouseout = () => button.style.backgroundColor = '#f0f0f0';

    titleDiv.appendChild(button);

    // 5. 绑定点击事件
// 5. 绑定点击事件 (增强版：分批延时打开)
button.addEventListener('click', async () => {
    // --- 可配置参数 ---
    const BATCH_SIZE = 5; // 每批打开多少个标签页
    const DELAY_MS = 1000;   // 每批之间的间隔时间（毫秒），1000毫秒 = 1秒
    // -----------------

    if (finalLinksToOpen.length === 0) {
        alert('没有找到可供打开的其他历史版本。');
        return;
    }

    const confirmationMessage = `即将分批打开 ${finalLinksToOpen.length} 个新标签页。\n\n设置：每批 ${BATCH_SIZE} 个，间隔 ${DELAY_MS / 1000} 秒。\n\n是否继续？`;

    if (window.confirm(confirmationMessage)) {
        const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
        button.disabled = true;
        button.style.cursor = 'not-allowed';
        button.style.backgroundColor = '#d3d3d3';
        for (let i = 0; i < finalLinksToOpen.length; i++) {
            const urlToOpen = finalLinksToOpen[i];
            button.textContent = `正在打开... (${i + 1}/${finalLinksToOpen.length})`;
            GM_openInTab(urlToOpen, { active: false, insert: true });
            if ((i + 1) % BATCH_SIZE === 0 && (i + 1) < finalLinksToOpen.length) {
                await sleep(DELAY_MS);
            }
        }
        button.textContent = `已全部打开 (${finalLinksToOpen.length})`;
    }
});

})();