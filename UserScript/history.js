// ==UserScript==
// @name         北大法宝·本法变迁一键打开
// @namespace    https://github.com/LeeQixian/MyLearningPy
// @version      1.1.1
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

    // 2. 提取所有历史版本的ID
    const versionIds = [];
    const compareLinks = targetBox.querySelectorAll('ul li div.theme a.lawChange.contrast');

    const regexCompareId = /\/compare\/.*-(.*)\.html/;
    compareLinks.forEach(link => {
        const href = link.getAttribute('href');
        if (href) {
            const match = href.match(regexCompareId);
            if (match && match[1]) {
                versionIds.push(match[1]);
            }
        }
    });

    if (versionIds.length === 0) {
        console.log('未找到任何可供对比的历史版本链接。');
        return;
    }

    // 3. 处理数据：去重并排除当前页面
    // 3.1 获取当前页面的ID
    let currentId = null;
    const regexCurrentId = /chl\/(.*?)\.html/;
    const currentUrlMatch = window.location.href.match(regexCurrentId);
    if (currentUrlMatch && currentUrlMatch[1]) {
        currentId = currentUrlMatch[1];
    }

    // 3.2 去重并过滤
    const uniqueIds = [...new Set(versionIds)];
    const finalIdsToOpen = uniqueIds.filter(id => id !== currentId);

    // 4. 创建并注入UI（按钮）
    const button = document.createElement('button');
    button.textContent = `一键打开所有历史版本 (${finalIdsToOpen.length})`;
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
button.addEventListener('click', async () => { // <--- 注意这里添加了 async
    // --- 可配置参数 ---
    const BATCH_SIZE = 5; // 每批打开多少个标签页
    const DELAY_MS = 1000;   // 每批之间的间隔时间（毫秒），1000毫秒 = 1秒
    // -----------------

    if (finalIdsToOpen.length === 0) {
        alert('没有找到可供打开的其他历史版本。');
        return;
    }

    const confirmationMessage = `即将分批打开 ${finalIdsToOpen.length} 个新标签页。\n\n设置：每批 ${BATCH_SIZE} 个，间隔 ${DELAY_MS / 1000} 秒。\n\n是否继续？`;

    if (window.confirm(confirmationMessage)) {
        // 定义一个延时函数
        const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));

        // 立即禁用按钮，防止重复点击
        button.disabled = true;
        button.style.cursor = 'not-allowed';
        button.style.backgroundColor = '#d3d3d3';

        for (let i = 0; i < finalIdsToOpen.length; i++) {
            const id = finalIdsToOpen[i];
            const urlToOpen = `https://www.pkulaw.com/chl/${id}.html?way=listView`;

            // 更新按钮文本以显示进度
            button.textContent = `正在打开... (${i + 1}/${finalIdsToOpen.length})`;

            GM_openInTab(urlToOpen, { active: false, insert: true });

            // 判断是否达到一批的数量，并且不是最后一个
            if ((i + 1) % BATCH_SIZE === 0 && (i + 1) < finalIdsToOpen.length) {
                // 等待指定的间隔时间
                await sleep(DELAY_MS);
            }
        }

        // 所有任务完成后，更新按钮最终状态
        button.textContent = `已全部打开 (${finalIdsToOpen.length})`;
    }
});

})();