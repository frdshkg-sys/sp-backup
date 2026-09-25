# CHUN KING 業務智慧表單與財務看板系統

本專案為 **CHUN KING** 量身打造的高效能 SharePoint Online 業務整合系統，集成了「新增支出記錄（多項目分攤）」、「新增收入記錄」、「編輯收支記錄（全庫即時搜尋與批次分攤編輯）」、「工程項目管理」、「工程備忘錄」及「財務即時看板」等全流程功能。

本系統支援 **本地開發環境**（透過 Python 智慧代理連線至 SharePoint 線上資料庫）與 **SharePoint 線上正式環境**（透過 SiteAssets 內嵌與自動通信橋樑）無縫雙軌運作。

---

## 📌 系統功能亮點

### 1. 新增支出記錄 (Expense Allocation)
* **多項目分攤支出 (Multi-project Allocation)**：
  * 支援單張支票一次性分攤至多個工程項目與費用小類。
  * 即時計算分攤總額，並提供工程項目快速關鍵字搜尋下拉選單。
* **自動支票編號計算**：
  * 支援字頭：`CK`、`WS`、`CHQ`、`DBS`、`TEST` 及手動輸入模式。
  * 自動向伺服器拉取並計算最大序號，防止跳號或重複。
* **付款狀態切換與防呆**：
  * 支援「已付」與「未付」切換；選取「未付」時自動鎖定支票欄位。
* **智慧收據管理 (Receipt Management)**：
  * **自動依支票號碼命名**：上傳之收據（`.pdf`、`.jpg`、`.jpeg`、`.png`）會自動依當前支票號碼更名（如 `CK1003.pdf`、`WS2016.png`），並在預覽卡片中即時呈現目標檔名與原始檔名資訊。
  * **動態連動同步**：若先選取收據再切換支票字頭或修改支票號碼，更名目標與上傳檔案自動即時刷新。
  * **未付狀態禁止上傳**：付款狀態為「未付」時，收據拖放與上傳區域全面鎖定（提示 `🔒 未付記錄無需且不支援上傳收據`），防止無支票號碼時誤傳；切換為未付時會自動清空已選暫存檔。

### 2. 新增收入記錄 (Income Management)
* **自動單號生成**：自動遞增生成如 `INC-001171` 之標準單號。
* **工程與銀行關聯**：支援關聯工程項目、收入金額與入賬銀行。
* **收據自動命名與歸檔**：收入收據自動以單號命名（如 `INC-001171.pdf`），並自動歸檔至 `/sites/CHUNKING/DocLib/收入/{銀行}`。

### 3. 編輯收支記錄 (Transaction Editor)
* **全庫即時搜尋 (Always Server Search)**：
  * 移除本地快取限制，每次搜尋（支援關鍵字、單號、支票號碼、金額等）直接向 SharePoint 伺服器發起全量即時檢索，確保多使用者協作下的資料新鮮度。
* **多項目分攤批次檢視模式 (Batch View Mode)**：
  * **未付連續記錄** 與 **已付同支票號記錄** 自動聚合為分攤卡片批次檢視。
  * 支援在分攤卡片中直接編輯各筆記錄的 **所屬項目**、**小類** 與 **分攤金額**。
  * 自動隱藏無關控制項與欄位，介面乾淨聚焦。
* **批次作廢連動與成本扣除**：
  * 批次模式下切換狀態為「作廢」時，整批記錄一次性同步更新，並自動全額扣除各工程項目的累計已付成本。
* **收據更換與鎖定**：
  * 支援更換收據並自動更名為支票編號；未付狀態下同樣嚴格鎖定上傳區塊。

### 4. 財務看板與工程統計 (Dashboard & Project Sync)
* **合約金額與成本動態同步**：每次新增、編輯、分攤或作廢交易時，自動增量計算並同步更新工程項目的累計成本與累計收入。
* **變更工程 (VO) 動態統計**：完整追蹤合約金額調整與預算執行情況。

---

## 📂 專案目錄結構

```text
mitigation/
├── smart_forms_app.html            # 核心單頁應用程式 (表單中心 + 財務看板)
├── server.py                       # 本地開發代理伺服器 (反向代理 SharePoint REST API)
├── start_app.bat                   # 本地一鍵啟動腳本
├── deploy_app_to_sharepoint.py     # 全系統自動化 SharePoint 部署腳本 (包含表單中心與看板)
├── sharepoint-bridge.user.js       # Tampermonkey 自動通信與路由橋樑腳本
├── cookies.json                    # SharePoint 認證 Cookies (本機連線憑證)
├── chrome-extension/               # Chrome 擴充功能 (SharePoint Forms Auto-Bridge)
│   ├── manifest.json
│   ├── content.js
│   └── 使用說明.txt
├── CHUN_KING_表單中心與財務看板使用指引.pdf # 操作指引手冊
└── README.md                       # 專案說明文件 (本文件)
```

---

## 🛠️ 本地開發與測試指引

本專案提供免安裝龐大相依套件的輕量化本機開發環境，透過 `server.py` 自動轉發 REST API 至 SharePoint 線上網站：

### 1. 前置需求
* Python 3.8+
* 已安裝 `requests` 套件：
  ```bash
  pip install requests
  ```
* 確保 `cookies.json` 包含有效的 SharePoint 登入憑證（可由瀏覽器開發人員工具中複製 SharePoint 網站之 Cookie）。

### 2. 啟動伺服器
* **方式 A（推薦）**：滑鼠雙擊 `start_app.bat`。
* **方式 B**：在終端機中執行：
  ```bash
  python server.py
  ```
伺服器將在 `http://localhost:8080` 啟動，並自動在瀏覽器中開啟表單。

### 3. 本地測試頁面
* 支出表記錄：`http://localhost:8080/smart_forms_app.html#expense`
* 收入表記錄：`http://localhost:8080/smart_forms_app.html#income`
* 編輯收支表記錄：`http://localhost:8080/smart_forms_app.html#edit-tx`
* 財務看板：`http://localhost:8080/smart_forms_app.html#dashboard`

---

## 🚀 SharePoint 正式環境部署指引

當本機測試完畢並確認功能無誤後，可直接執行 Python 部署腳本將程式發布至 SharePoint 正式文件庫：

### 1. 執行部署命令
```bash
python deploy_app_to_sharepoint.py
```

### 2. 部署流程
1. 自動讀取 `cookies.json` 並向 SharePoint 請求最新 `FormDigestValue`（包含 429 速率限制重試機制）。
2. 將 `smart_forms_app.html` 同步上傳至雙重路徑（兼具現有連結相容性與 SharePoint 介面視覺可見性）：
   * **視覺可見目錄（SharePoint 網站資產介面直接瀏覽）**：
     * `/sites/CHUNKING/SiteAssets/app/smart_forms_app.html`
     * `/sites/CHUNKING/SiteAssets/app/app.html`
   * **現有系統目錄（確保既有 Web Part 連結不受影響）**：
     * `/sites/CHUNKING/SiteAssets/forms/app.html`
     * `/sites/CHUNKING/SiteAssets/forms/smart_forms_app.html`
3. 執行二進位大小驗證，確保線上檔案與本機完全一致。

### 3. SharePoint 線上正式入口
* **網站資產介面可見入口**：  
  `https://k35n.sharepoint.com/sites/CHUNKING/SiteAssets/app/smart_forms_app.html` (或 `.../app.html`)
* **既有相容入口**：  
  `https://k35n.sharepoint.com/sites/CHUNKING/SiteAssets/forms/app.html`

---

## 🗄️ SharePoint 列表與文件庫架構

| 項目類型 | 名稱 / GUID | 儲存路徑 / 說明 |
| :--- | :--- | :--- |
| **支出記錄** | `Transactions` / `GUID_EXPENSE` | 記錄所有分攤支出記錄、支票號碼、付款狀態、收據 URL |
| **收入記錄** | `List` / `GUID_INCOME` | 記錄所有收入傳票、金額、入賬銀行、收據 URL |
| **工程項目** | `Projects` / `GUID_PROJECT` | 記錄工程合約、累計已付成本、累計收入、變更工程 (VO) |
| **支出收據文件庫** | `DocLib` | `/sites/CHUNKING/DocLib/{CK\|WS\|CHQ\|DBS\|TEST}/{支票號碼}.{ext}` |
| **收入收據文件庫** | `DocLib` | `/sites/CHUNKING/DocLib/收入/{銀行名稱}/{單號}.{ext}` |

---

## 🧩 瀏覽器通信橋樑 (Auto-Bridge)

當表單內嵌於 SharePoint 現代化頁面的 `iframe` 中時，為了支援父視窗網址列頁籤連動（如 `#expense`、`#edit-tx`）以及跨來源 API 代理通信，系統提供了兩種部署模式：

1. **Chrome 擴充功能**（見 `chrome-extension/`）：
   * 前往 `chrome://extensions/` 開啟開發人員模式。
   * 點選「載入未封裝項目」選取 `chrome-extension` 目錄即可完成安裝。
2. **Tampermonkey 使用者腳本**（見 `sharepoint-bridge.user.js`）：
   * 在 Tampermonkey / Violentmonkey 中建立新腳本並貼上內容即可。

---

## 📝 最近更新紀錄 (Changelog)

* **2026-09-23**：
  * **突破全庫搜尋 5,000 筆掃描限制**：移除 CAML 中的 OrderBy 限制，徹底解決大資料量（10,000+ 筆）下因微軟視圖閥值導致早期記錄（如 `EXP-01282 ～ EXP-01286`）被截斷之問題；同時支援單號範圍字串（`EXP-01282 ～ EXP-01286`）直接檢索。
  * **未付分攤批次成員聯網動態聚合**：當點選任一未付單據時，自動聯網查詢同廠商與同日期之其餘未付成員，完整呈現在多項目分攤面板中。
  * **收據自動更名**：支援 `.pdf`、`.jpg`、`.jpeg`、`.png`，上傳時自動更名為支票編號（支出）或交易單號（收入），並支援動態輸入連動。
  * **未付狀態禁止上傳**：付款狀態為「未付」時自動鎖定收據上傳區域並清除暫存檔。
  * **批次分攤編輯升級**：支援在多項目分攤面板中逐行編輯所屬項目、小類與分攤金額，並優化介面控制項呈現。
  * **成功部署至 SharePoint 線上生產環境**。
