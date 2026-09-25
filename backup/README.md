# CHUN KING: SharePoint to Google Drive Weekly Backup Pipeline

本目錄包含自動將 CHUN KING SharePoint 線上資料（清單表格、合約成本、支出收入記錄與所有支票收據、入數紙 PDF / 圖檔）安全、定期備份至 **Google Drive** 的自動化程式碼與設定。

---

## 📂 檔案目錄結構

```text
backup/
├── backup_sharepoint_to_gdrive.py   # 主備份排程執行腳本 (清單匯出 + 增量媒體同步 + 報表生成)
├── sharepoint_client.py             # SharePoint API 客戶端 (內建 429 速率限制保護、Retry-After、退避與熔斷機制)
├── gdrive_client.py                 # Google Drive REST API 客戶端 (Service Account 認證、斷點續傳、清單狀態管理)
├── requirements.txt                 # Python 相依套件清單
├── README.md                        # 本說明文件
├── manifest.json                    # (執行時自動生成/更新) SHA-256 檔案校驗與增量同步狀態庫
└── staging/                         # (本地執行時) 暫存與匯出目錄
```

---

## 🛡️ SharePoint 速率限制 (Throttling) 與 429 預防保護

為防止巨量下載觸發 Microsoft 365 的 `HTTP 429 Too Many Requests` 或 `HTTP 503 Server Busy`，本管線內建五層保護：

1. **遠端清單增量同步 (Layer 1)**：每次執行先比對 Google Drive 上的 `manifest.json`，**已備份過且未變動的檔案 100% 略過**，單次備份僅下載本週新增的約 10–50 張新收據，降低 98% 以上的請求量。
2. **禮貌性間隔與低併發 (Layer 2)**：檔案下載之間強制加入 **80ms 禮貌性延遲**，採用單線程平滑流式傳輸，避免瞬間塞滿 SharePoint 閘道。
3. **動態解析 `Retry-After` (Layer 3)**：收到 429/503 時自動讀取微軟標頭指示之冷卻秒數，並加上隨機擾動 (Jitter) 與指數退避重試。
4. **離峰時段排程 (Layer 4)**：GitHub Actions 預設排程在 **每週日凌晨 03:00 HKT** (週六 19:00 UTC) 離峰時段執行，不與日間同仁作業衝突。
5. **熔斷機制 (Layer 5 - Circuit Breaker)**：若連續遭遇 5 次 429 且無法恢復，腳本將主動中止並發出警告，絕不暴力重試以保護租戶穩定性。

---

## 🚀 設定步驟 (GitHub Actions 自動排程)

### 步驟 1: 設定 Google Cloud 服務帳號 (Service Account)
1. 前往 [Google Cloud Console](https://console.cloud.google.com/)，建立或選取專案（如 `chun-king-backup`）。
2. 在 **API 和服務 > 程式庫** 中搜尋並啟用 **Google Drive API**。
3. 前往 **IAM 與管理 > 服務帳戶**，點擊 **建立服務帳戶**：
   - 名稱設定為：`gdrive-backup-bot`
   - 建立完成後點入該帳戶，切換到 **金鑰 (Keys)** 分頁 > **新增金鑰 > 建立新的金鑰 (JSON)**。
   - 將下載得到的 JSON 檔案妥善保存。
4. 複製該服務帳戶的電子郵件（例如 `gdrive-backup-bot@chun-king-backup.iam.gserviceaccount.com`）。

### 步驟 2: 建立並共用 Google Drive 備份資料夾
1. 在您的 Google Drive 中建立根資料夾：`CHUN_KING_Backups`。
2. 點擊該資料夾右鍵 > **共用**，將剛才複製的服務帳戶電子郵件貼上，權限設定為 **「編輯者 (Editor)」**。
3. 從瀏覽器網址列複製該資料夾的 ID（例如網址為 `https://drive.google.com/drive/folders/1a2b3c4d5e...`，則 ID 為 `1a2b3c4d5e...`）。

### 步驟 3: 設定 GitHub Repository Secrets
前往您儲存庫的 **Settings > Secrets and variables > Actions > New repository secret**，新增以下機密變數：

| Secret 名稱 | 內容說明 |
| :--- | :--- |
| `GDRIVE_SERVICE_ACCOUNT_JSON` | 貼上步驟 1 下載的完整 Service Account JSON 檔案內容 |
| `GDRIVE_FOLDER_ID` | 貼上步驟 2 取得的 Google Drive 資料夾 ID |
| `SP_COOKIES_JSON` | 貼上專案中 `cookies.json` 的完整內容 (或定期更新之 SharePoint Cookies) |

### 步驟 4: 測試執行
1. 前往 GitHub 儲存庫的 **Actions** 分頁。
2. 在左側選單點選 **Weekly SharePoint to Google Drive Backup**。
3. 點擊右側的 **Run workflow** 按鈕進行手動測試。
4. 執行完成後，您可以在 Google Drive 的 `CHUN_KING_Backups` 資料夾中看見：
   - `Weekly_Snapshots/YYYY-MM-DD/`（包含繁體中文版 `CHUN_KING_Financial_Master_YYYY-MM-DD.xlsx` 與 JSON）
   - `Receipts_Live_Mirror/`（包含自動歸檔之支票收據與各銀行收入單據）
   - `manifest.json`（檔案雜湊與同步狀態）

---

## 💻 本地測試指引 (Local Dry Run)

若要在本機直接測試 SharePoint 清單匯出與防呆機制：
```bash
# 1. 確保已安裝 openpyxl 與 requests
pip install -r backup/requirements.txt

# 2. 執行備份腳本 (若未設定 GDrive 金鑰，會自動切換為本地暫存模式)
python backup/backup_sharepoint_to_gdrive.py
```
執行完畢後，可在 `backup/staging/YYYY-MM-DD/` 目錄中直接檢視生成的收支 Master Excel 試算表與報表。
