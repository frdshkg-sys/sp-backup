// CHUN KING SharePoint Forms Auto-Bridge Extension (Manifest V3 - Main World)
(function() {
    'use strict';

    if (window.__SP_BRIDGE_INSTALLED__) return;
    window.__SP_BRIDGE_INSTALLED__ = true;

    console.log("🚀 [CHUN KING Extension] SharePoint 智慧表單自動通信與路由橋樑已啟動！");

    function broadcastToAllFrames(win, data) {
        if (!win) return;
        try {
            win.postMessage(data, '*');
        } catch (e1) {}
        try {
            for (var i = 0; i < win.frames.length; i++) {
                broadcastToAllFrames(win.frames[i], data);
            }
        } catch (e2) {}
    }

    function getTopTab() {
        var h = (window.location.hash || '').replace('#', '').trim();
        if (h && ['income', 'project', 'remarks', 'expense', 'edit-tx', 'dashboard'].includes(h)) return h;
        try {
            var params = new URLSearchParams(window.location.search);
            var t = params.get('tab');
            if (t && ['income', 'project', 'remarks', 'expense', 'edit-tx', 'dashboard'].includes(t)) return t;
        } catch (e) {}
        return '';
    }


    function syncTabToFrames() {
        var tab = getTopTab();
        if (tab) {
            console.log("📑 [Bridge] 正在廣播路由頁籤至表單 iframe:", tab);
            broadcastToAllFrames(window, { type: 'SP_SET_TAB', tab: tab });
        }
    }

    // 頁面載入與切換時主動多頻段廣播（適配 SharePoint ODSP blob iframe 非同步渲染時機）
    syncTabToFrames();
    setTimeout(syncTabToFrames, 200);
    setTimeout(syncTabToFrames, 600);
    setTimeout(syncTabToFrames, 1200);
    setTimeout(syncTabToFrames, 2500);

    window.addEventListener('hashchange', syncTabToFrames);
    window.addEventListener('popstate', syncTabToFrames);

    // 監聽來自子表單的請求
    window.addEventListener('message', async function(e) {
        if (!e.data) return;

        // 1. 回應子表單詢問當前頂層視窗的頁籤
        if (e.data.type === 'SP_GET_TOP_HASH') {
            var tab = getTopTab();
            if (tab && e.source && e.source !== window) {
                try {
                    e.source.postMessage({ type: 'SP_SET_TAB', tab: tab }, '*');
                } catch (tabErr) {}
            }
            return;
        }

        // 2. SharePoint API 代理請求
        if (e.data.type !== 'SP_FETCH_PROXY') return;
        var reqId = e.data.id;
        var reqUrl = e.data.url;
        var reqOptions = e.data.options;

        console.log("📨 [SP-Bridge] 收到表單代理請求:", reqUrl);

        try {
            var resp = await fetch(reqUrl, reqOptions);
            var text = await resp.text();
            var json = null;
            try {
                json = JSON.parse(text);
            } catch (jsonErr) {}

            var responseData = {
                type: 'SP_FETCH_RESPONSE',
                id: reqId,
                ok: resp.ok,
                status: resp.status,
                data: json,
                text: text
            };

            console.log("✅ [SP-Bridge] 請求完成，狀態碼:", resp.status);

            broadcastToAllFrames(window, responseData);
            if (e.source && e.source !== window) {
                try {
                    e.source.postMessage(responseData, '*');
                } catch (sendErr) {}
            }
        } catch (err) {
            console.error("❌ [SP-Bridge] 請求發生錯誤:", err);
            var errData = {
                type: 'SP_FETCH_RESPONSE',
                id: reqId,
                ok: false,
                status: 500,
                error: err.toString()
            };
            broadcastToAllFrames(window, errData);
            if (e.source && e.source !== window) {
                try {
                    e.source.postMessage(errData, '*');
                } catch (sendErr2) {}
            }
        }
    });
})();
