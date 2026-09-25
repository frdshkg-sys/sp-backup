# SharePoint GUID 與 OData 欄位編碼對照表 (Field & GUID Mapping)

本文件整理了 CHUN_KING 系統在 SharePoint 列表、REST API (OData Verbose) 與前端應用程式中使用的 **清單 GUID (List GUIDs)** 及 **16進位編碼欄位代碼 (如 `OData__x9805__x76ee__x7de8__x865f_`) 對應繁體中文** 之完整映射手冊。

---

## 快速目錄
1. [SharePoint 清單 GUID 對照表](#1-sharepoint-清單-guid-對照表)
2. [OData 編碼機制原理說明](#2-odata-編碼機制原理說明)
3. [清單欄位完整對照表](#3-清單欄位完整對照表)
   - [3.1 Projects (項目工程清單)](#31-projects-項目工程清單)
   - [3.2 Transactions (支出與支票記錄)](#32-transactions-支出與支票記錄)
   - [3.3 交易記錄-收入 (Income)](#33-交易記錄-收入-income)
   - [3.4 支票收據文件庫 (Cheque Receipts Library)](#34-支票收據文件庫-cheque-receipts-library)
4. [全域 OData 欄位字串速查字典](#4-全域-odata-欄位字串速查字典)
5. [自動解碼工具代碼 (JavaScript / Python)](#5-自動解碼工具代碼)

---

## 1. SharePoint 清單 GUID 對照表

| 清單名稱 (SharePoint Title) | 系統功能別名 | 清單 GUID (List GUID) | 伺服器端 URL 路徑 | 說明 |
| :--- | :--- | :--- | :--- | :--- |
| **Projects** | `GUID_PROJECTS` | `1958fe5e-336d-43a0-beb2-4da48df59f7b` | `/sites/CHUNKING/Lists/Projects` | 工程項目主檔清單 (合約、成本、收支統計) |
| **Transactions** | `GUID_EXPENSE` | `a09172c2-2be4-4b12-8dfd-418a6fbe0c6d` | `/sites/CHUNKING/Lists/Transactions` | 所有支出款項、開出支票及分判付款表記錄 |
| **交易記錄-收入** | `GUID_INCOME` | `527698fd-139d-4482-b819-b3f6da4e8794` | `/sites/CHUNKING/Lists/Income` | 項目進帳、客戶付款、退款與各銀行收入表記錄 |
| **支票收據** | `GUID_RECEIPTS` | `441ac1bf-d867-4c5f-af6e-6939afcbb2b4` | `/sites/CHUNKING/Lists/ChequeReceipts` | 支票照片與收據圖檔存放文件庫 (Doc Library) |
| **Site Pages** | - | `547bce72-2b86-40d9-8b28-48c97f313a2a` | `/sites/CHUNKING/SitePages` | SharePoint 站台頁面庫 (存放儀表板頁面) |
| **Documents** | - | `3a0db32a-274f-45b6-aadb-facaceee8299` | `/sites/CHUNKING/Shared Documents` | 共用文件庫 |

---

## 2. OData 編碼機制原理說明

SharePoint 在儲存非英文字元（如繁體中文、全形符號）的自訂欄位時，會採用內部規則進行轉碼：

1. **`_xHHHH_` Unicode 轉碼規則**：
   - 每個非 ASCII 字元會被轉為 4 位 16 進位 Unicode (UTF-16) 編碼，並前後加上底線 `_`。
   - **範例**：
     - `項` = Unicode `U+9805` $\rightarrow$ `_x9805_`
     - `目` = Unicode `U+76ee` $\rightarrow$ `_x76ee_`
     - `編` = Unicode `U+7de8` $\rightarrow$ `_x7de8_`
     - `號` = Unicode `U+865f` $\rightarrow$ `_x865f_`
     - **完整 InternalName**：`_x9805__x76ee__x7de8__x865f_` (項目編號)
2. **`OData_` 前綴規則**：
   - 當透過 SharePoint REST API (`_api/web/lists/.../items`) 並使用 verbose 模式 (`Accept: application/json;odata=verbose`) 查詢時，若欄位內部名稱以底線 `_` 或數字開頭，OData 規範會自動在最前置加上 `OData_`。
   - 因此 `_x9805__x76ee__x7de8__x865f_` 變成 `OData__x9805__x76ee__x7de8__x865f_`。
3. **Lookup 欄位與 `Id` 後綴**：
   - 查詢關聯其他列表的欄位（如「所屬項目」Lookup 欄位），在寫入或取值 ID 時需帶 `_Id` 或 `Id` 後綴：
     - `_x6240__x5c6c__x9805__x76ee_Id` 或 `OData__x6240__x5c6c__x9805__x76ee_Id`。
4. **SharePoint 32 字元內部名稱長度截斷現象**：
   - SharePoint 舊版架構將 InternalName 限制在 32 字元以內。例如「預計施工日期」字元轉為 hex 需 35 字元，故末端被截斷：
     - `預計施工` + `日` $\rightarrow$ `_x9810__x8a08__x65bd__x5de5__x65` (最後的 `_x65` 為截斷剩餘字元)。

---

## 3. 清單欄位完整對照表

### 3.1 Projects (項目工程清單)
> **GUID**: `1958fe5e-336d-43a0-beb2-4da48df59f7b`

| 繁體中文欄位名稱 (Title) | OData REST API 屬性名稱 | SharePoint 內部名稱 (InternalName) | 資料類型 (Type) | 必填 | 說明 / 備註 |
| :--- | :--- | :--- | :--- | :---: | :--- |
| **項目名稱 (工程名稱)** | `Title` | `Title` | Text (單行文字) | 是 | 系統預設標題欄位，填寫工程項目全名 |
| **項目編號** | `OData__x9805__x76ee__x7de8__x865f_` | `_x9805__x76ee__x7de8__x865f_` | Text (單行文字) | 否 | 項目工程識別代號 (如 `P2024-001`) |
| **分類** | `OData__x5206__x985e_` | `_x5206__x985e_` | Text (單行文字) | 否 | 項目工程種類別 |
| **負責人** | `OData__x8ca0__x8cac__x4eba_` | `_x8ca0__x8cac__x4eba_` | Text (單行文字) | 否 | 負責跟進工程的專案經理或負責人姓名 |
| **合約價錢** | `OData__x5408__x7d04__x50f9__x9322_` | `_x5408__x7d04__x50f9__x9322_` | Currency (貨幣) | 否 | 該項目之總合約工程總金額 (HKD) |
| **已收金額** | `OData__x5df2__x6536__x91d1__x984d_` | `_x5df2__x6536__x91d1__x984d_` | Currency (貨幣) | 否 | 客戶歷來已清付累積金額 (HKD) |
| **未收金額** | `OData__x672a__x6536__x91d1__x984d_` | `_x672a__x6536__x91d1__x984d_` | Calculated (計算值) | 否 | `[合約價錢] - [已收金額]` |
| **已付成本** | `OData__x5df2__x4ed8__x6210__x672c_` | `_x5df2__x4ed8__x6210__x672c_` | Currency (貨幣) | 否 | 分判商、料件及工程已付出之累計支出 (HKD) |
| **流入／出** | `OData__x6d41__x5165__xff0f__x51fa_` | `_x6d41__x5165__xff0f__x51fa_` | Calculated (計算值) | 否 | 淨現金流：`[已收金額] - [已付成本]` |
| **預計施工日期** | `OData__x9810__x8a08__x65bd__x5de5__x65` | `_x9810__x8a08__x65bd__x5de5__x65` | DateTime (日期) | 否 | 工程進場開工日期 |
| **預計完工日期** | `OData__x9810__x8a08__x5b8c__x5de5__x65` | `_x9810__x8a08__x5b8c__x5de5__x65` | DateTime (日期) | 否 | 預計工程交付/驗收完工日期 |
| **備註** | `OData__x5099__x8a3b_` | `_x5099__x8a3b_` | Note (多行文字) | 否 | 項目詳細備註與注意事項 |
| **VariationOrders** | `VariationOrders` | `VariationOrders` | Note (多行文字) | 否 | 追加工程 (VO) 之 JSON 結構化陣列資料 |
| **識別碼 (ID)** | `Id` | `Id` | Integer (整數) | 是 | 系統主鍵 ID |
| **最後修改時間** | `Modified` | `Modified` | DateTime (日期時間) | 系統 | 記錄最後更新時間 |
| **建立時間** | `Created` | `Created` | DateTime (日期時間) | 系統 | 記錄建立時間 |

---

### 3.2 Transactions (支出與支票記錄)
> **GUID**: `a09172c2-2be4-4b12-8dfd-418a6fbe0c6d`

| 繁體中文欄位名稱 (Title) | OData REST API 屬性名稱 | SharePoint 內部名稱 (InternalName) | 資料類型 (Type) | 必填 | 說明 / 選項內容 |
| :--- | :--- | :--- | :--- | :---: | :--- |
| **交易時間** | `OData__x4ea4__x6613__x6642__x9593_` | `_x4ea4__x6613__x6642__x9593_` | DateTime (日期時間) | 是 | 開票或付款出帳之交易日期時間 |
| **金額** | `OData__x91d1__x984d_` | `_x91d1__x984d_` | Currency (貨幣) | 是 | 支出金額 (HKD) |
| **支票編號** | `OData__x652f__x7968__x7de8__x865f_` | `_x652f__x7968__x7de8__x865f_` | Text (單行文字) | 否 | 支票號碼 (如 `001435`, `802910`) |
| **轉帳銀行** | `OData__x8f49__x5e33__x9280__x884c_` | `_x8f49__x5e33__x9280__x884c_` | Choice (下拉單選) | 否 | 付款戶口：`東亞銀行`、`星展銀行`、`恒生銀行` |
| **所屬項目** | `OData__x6240__x5c6c__x9805__x76ee_` | `_x6240__x5c6c__x9805__x76ee_` | Lookup (關聯) | 是 | 關聯 Projects 項目標題 |
| **所屬項目 Id** | `OData__x6240__x5c6c__x9805__x76ee_Id` | `_x6240__x5c6c__x9805__x76ee_Id` | Integer (整數) | 是 | 關聯 Projects 清單項目的數值主鍵 `Id` |
| **子項目** | `OData__x5b50__x9805__x76ee_` | `_x5b50__x9805__x76ee_` | Text (單行文字) | 否 | 分工工種或費用明細 (如泥水、木工、油漆、雜項) |
| **收款人** | `OData__x6536__x6b3e__x4eba_` | `_x6536__x6b3e__x4eba_` | Text (單行文字) | 否 | 收款師傅、供應商或分判商名稱 (Payee) |
| **負責人** | `OData__x8ca0__x8cac__x4eba_` | `_x8ca0__x8cac__x4eba_` | Text (單行文字) | 否 | 經手主管或項目經理 |
| **付款狀態** | `OData__x4ed8__x6b3e__x72c0__x614b_` | `_x4ed8__x6b3e__x72c0__x614b_` | Choice (下拉單選) | 否 | 選項：`已付`、`未付` |
| **收款銀行** | `OData__x6536__x6b3e__x9280__x884c_` | `_x6536__x6b3e__x9280__x884c_` | Text (單行文字) | 否 | 收款人開戶銀行名稱 |
| **戶口** | `OData__x6236__x53e3_` | `_x6236__x53e3_` | Text (單行文字) | 否 | 收款人銀行戶口號碼 |
| **收據 (URL)** | `OData__x6536__x64da__x9023__x7d50_` | `_x6536__x64da__x9023__x7d50_` | URL (超連結) | 否 | 支票圖檔或付款憑證在 SharePoint 之檔案連結 |
| **Invoice No.** | `Invoice_x0020_No_x002e_` | `Invoice_x0020_No_x002e_` | Text (單行文字) | 否 | 發票單號 / 帳單編號 (對應 Excel 之 `Invoice No.`) |
| **RecordStatus** | `RecordStatus` | `RecordStatus` | Choice (下拉單選) | 否 | 記錄狀態：`有效`、`作廢` |
| **IsIndependent** | `IsIndependent` | `IsIndependent` | Boolean (布林值) | 否 | 是否為獨立款項 (`true`/`false`) |
| **BatchId** | `BatchId` | `BatchId` | Text (單行文字) | 否 | 批次開票對帳批號代碼 |
| **Remarks** | `Remarks` | `Remarks` | Note (多行文字) | 否 | 款項補充備註 |
| **識別碼 (ID)** | `Id` | `Id` | Integer (整數) | 是 | 系統主鍵 ID |

---

### 3.3 交易記錄-收入 (Income)
> **GUID**: `527698fd-139d-4482-b819-b3f6da4e8794`

| 繁體中文欄位名稱 (Title) | OData REST API 屬性名稱 | SharePoint 內部名稱 (InternalName) | 資料類型 (Type) | 必填 | 說明 / 選項內容 |
| :--- | :--- | :--- | :--- | :---: | :--- |
| **交易時間** | `OData__x4ea4__x6613__x6642__x9593_` | `_x4ea4__x6613__x6642__x9593_` | DateTime (日期時間) | 是 | 款項存入或進帳交易日期時間 |
| **金額** | `OData__x91d1__x984d_` | `_x91d1__x984d_` | Currency (貨幣) | 是 | 進帳金額 (HKD) |
| **所屬項目** | `OData__x6240__x5c6c__x9805__x76ee_` | `_x6240__x5c6c__x9805__x76ee_` | Lookup (關聯) | 否 | 關聯 Projects 項目標題 |
| **所屬項目 Id** | `OData__x6240__x5c6c__x9805__x76ee_Id` | `_x6240__x5c6c__x9805__x76ee_Id` | Integer (整數) | 否 | 關聯 Projects 清單項目的數值主鍵 `Id` |
| **收項銀行** | `OData__x6536__x9805__x9280__x884c_` | `_x6536__x9805__x9280__x884c_` | Choice (下拉單選) | 否 | 入帳戶口：`東亞銀行`、`匯豐銀行`、`渣打銀行`、`星展銀行`、`現金`、`達代收`、`退運費` |
| **收據 (URL)** | `OData__x6536__x64da_` | `_x6536__x64da_` | URL (超連結) | 否 | 入帳憑據、銀行入數紙連結 |
| **RecordStatus** | `RecordStatus` | `RecordStatus` | Choice (下拉單選) | 否 | 記錄狀態：`有效`、`作廢` |
| **Remarks** | `Remarks` | `Remarks` | Note (多行文字) | 否 | 收入補充備註 |
| **識別碼 (ID)** | `Id` | `Id` | Integer (整數) | 是 | 系統主鍵 ID |

---

### 3.4 支票收據文件庫 (Cheque Receipts Library)
> **GUID**: `441ac1bf-d867-4c5f-af6e-6939afcbb2b4`

| 繁體中文欄位名稱 (Title) | OData REST API 屬性名稱 | SharePoint 內部名稱 (InternalName) | 資料類型 (Type) | 說明 |
| :--- | :--- | :--- | :--- | :--- |
| **檔案名稱** | `FileLeafRef` / `Title` | `FileLeafRef` / `Title` | Text (單行文字) | 支票圖檔名稱 (如 `CHQ001435.pdf`) |
| **說明** | `Description` | `_ExtendedDescription` | Note (多行文字) | 圖片附加說明文字 |
| **伺服器相對路徑** | `FileRef` | `FileRef` | Text (URL 路徑) | 圖片於 SharePoint 伺服器完整存取路徑 |

---

## 4. 全域 OData 欄位字串速查字典

若在程式碼、API 回應或日誌中見到以 `OData__x` 或 `_x` 開頭的字串，可直接在本字典中反查繁體中文：

| 搜尋代碼 (OData / SharePoint 字串) | 繁體中文名稱 | Unicode 字元分解 |
| :--- | :--- | :--- |
| `OData__x4ea4__x6613__x6642__x9593_` / `_x4ea4__x6613__x6642__x9593_` | **交易時間** | 4ea4(交) + 6613(易) + 6642(時) + 9593(間) |
| `OData__x4ed8__x6b3e__x72c0__x614b_` / `_x4ed8__x6b3e__x72c0__x614b_` | **付款狀態** | 4ed8(付) + 6b3e(款) + 72c0(狀) + 614b(態) |
| `OData__x5099__x8a3b_` / `_x5099__x8a3b_` | **備註** | 5099(備) + 8a3b(註) |
| `OData__x5206__x985e_` / `_x5206__x985e_` | **分類** | 5206(分) + 985e(類) |
| `OData__x5408__x7d04__x50f9__x9322_` / `_x5408__x7d04__x50f9__x9322_` | **合約價錢** | 5408(合) + 7d04(約) + 50f9(價) + 9322(錢) |
| `OData__x5b50__x9805__x76ee_` / `_x5b50__x9805__x76ee_` | **子項目** | 5b50(子) + 9805(項) + 76ee(目) |
| `OData__x5df2__x4ed8__x6210__x672c_` / `_x5df2__x4ed8__x6210__x672c_` | **已付成本** | 5df2(已) + 4ed8(付) + 6210(成) + 672c(本) |
| `OData__x5df2__x6536__x91d1__x984d_` / `_x5df2__x6536__x91d1__x984d_` | **已收金額** | 5df2(已) + 6536(收) + 91d1(金) + 984d(額) |
| `OData__x6236__x53e3_` / `_x6236__x53e3_` | **戶口** | 6236(戶) + 53e3(口) |
| `OData__x6240__x5c6c__x9805__x76ee_` / `_x6240__x5c6c__x9805__x76ee_` | **所屬項目** | 6240(所) + 5c6c(屬) + 9805(項) + 76ee(目) |
| `OData__x6240__x5c6c__x9805__x76ee_Id` | **所屬項目 Id** | 所屬項目關聯項目主鍵 ID |
| `OData__x652f__x7968__x7de8__x865f_` / `_x652f__x7968__x7de8__x865f_` | **支票編號** | 652f(支) + 7968(票) + 7de8(編) + 865f(號) |
| `OData__x6536__x64da_` / `_x6536__x64da_` | **收據** | 6536(收) + 64da(據) |
| `OData__x6536__x64da__x9023__x7d50_` / `_x6536__x64da__x9023__x7d50_` | **收據連結** | 6536(收) + 64da(據) + 9023(連) + 7d50(結) |
| `OData__x6536__x6b3e__x4eba_` / `_x6536__x6b3e__x4eba_` | **收款人** | 6536(收) + 6b3e(款) + 4eba(人) |
| `OData__x6536__x6b3e__x9280__x884c_` / `_x6536__x6b3e__x9280__x884c_` | **收款銀行** | 6536(收) + 6b3e(款) + 9280(銀) + 884c(行) |
| `OData__x6536__x9805__x9280__x884c_` / `_x6536__x9805__x9280__x884c_` | **收項銀行** | 6536(收) + 9805(項) + 9280(銀) + 884c(行) |
| `OData__x672a__x6536__x91d1__x984d_` / `_x672a__x6536__x91d1__x984d_` | **未收金額** | 672a(未) + 6536(收) + 91d1(金) + 984d(額) |
| `OData__x6d41__x5165__xff0f__x51fa_` / `_x6d41__x5165__xff0f__x51fa_` | **流入／出** | 6d41(流) + 5165(入) + ff0f(／) + 51fa(出) |
| `OData__x8ca0__x8cac__x4eba_` / `_x8ca0__x8cac__x4eba_` | **負責人** | 8ca0(負) + 8cac(責) + 4eba(人) |
| `OData__x8f49__x5e33__x9280__x884c_` / `_x8f49__x5e33__x9280__x884c_` | **轉帳銀行** | 8f49(轉) + 5e33(帳) + 9280(銀) + 884c(行) |
| `OData__x91d1__x984d_` / `_x91d1__x984d_` | **金額** | 91d1(金) + 984d(額) |
| `OData__x9805__x76ee__x7de8__x865f_` / `_x9805__x76ee__x7de8__x865f_` | **項目編號** | 9805(項) + 76ee(目) + 7de8(編) + 865f(號) |
| `OData__x9810__x8a08__x5b8c__x5de5__x65` / `_x9810__x8a08__x5b8c__x5de5__x65` | **預計完工日期** | 9810(預)+8a08(計)+5b8c(完)+5de5(工)+截斷字元(日) |
| `OData__x9810__x8a08__x65bd__x5de5__x65` / `_x9810__x8a08__x65bd__x5de5__x65` | **預計施工日期** | 9810(預)+8a08(計)+65bd(施)+5de5(工)+截斷字元(日) |

---

## 5. 自動解碼工具代碼

如果需要自行在專案中將這些編碼欄位自動還原為中文名稱，可使用以下函式：

### JavaScript (用於前端應用程式)
```javascript
/**
 * 將 SharePoint 內部 hex 編碼字串 (如 _x9805__x76ee__x7de8__x865f_ 或 OData__x...) 解碼為中文
 * @param {string} fieldName 
 * @returns {string} 繁體中文名稱
 */
function decodeSharePointFieldName(fieldName) {
  if (!fieldName) return '';
  // 移除 OData_ 前綴
  let cleanName = fieldName.replace(/^OData_/, '');
  // 特殊截斷欄位處理
  const overrides = {
    '_x9810__x8a08__x65bd__x5de5__x65': '預計施工日期',
    '_x9810__x8a08__x5b8c__x5de5__x65': '預計完工日期'
  };
  if (overrides[cleanName]) return overrides[cleanName];

  // 將 _xHHHH_ 轉為 Unicode 字元
  let decoded = cleanName.replace(/_x([0-9a-fA-F]{4})_/g, (_, hex) => {
    return String.fromCharCode(parseInt(hex, 16));
  });

  if (decoded.endsWith('_Id')) {
    decoded = decoded.replace(/_Id$/, ' (ID)');
  }
  return decoded;
}

// 測試範例:
console.log(decodeSharePointFieldName('OData__x9805__x76ee__x7de8__x865f_')); // "項目編號"
console.log(decodeSharePointFieldName('OData__x8ca0__x8cac__x4eba_'));       // "負責人"
console.log(decodeSharePointFieldName('OData__x6240__x5c6c__x9805__x76ee_Id')); // "所屬項目 (ID)"
```

### Python (用於資料處理腳本)
```python
import re

def decode_sharepoint_field(field_name: str) -> str:
    """
    將 SharePoint 16 進位字串還原為繁體中文
    """
    if not field_name:
        return ""
    clean = re.sub(r'^OData_', '', field_name)
    
    # 處理 SharePoint 32 字元限制被截斷的名稱
    known_truncated = {
        '_x9810__x8a08__x65bd__x5de5__x65': '預計施工日期',
        '_x9810__x8a08__x5b8c__x5de5__x65': '預計完工日期'
    }
    if clean in known_truncated:
        return known_truncated[clean]
        
    def hex_to_char(match):
        return chr(int(match.group(1), 16))
        
    decoded = re.sub(r'_x([0-9a-fA-F]{4})_', hex_to_char, clean)
    if decoded.endswith('_Id'):
        decoded = decoded[:-3] + ' (ID)'
    return decoded

# 測試範例:
print(decode_sharepoint_field('OData__x9805__x76ee__x7de8__x865f_'))  # 項目編號
print(decode_sharepoint_field('OData__x5408__x7d04__x50f9__x9322_'))  # 合約價錢
```
