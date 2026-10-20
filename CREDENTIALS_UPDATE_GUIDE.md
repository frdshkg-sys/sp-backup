# GitHub Actions 憑證更新指南 (`SP_COOKIES_JSON` & `GDRIVE_OAUTH_TOKEN_JSON`)

本文件說明如何取得、驗證並更新每週自動備份排程（[`.github/workflows/weekly_backup.yml`](file:///Users/atelierdesmiyabi/Desktop/sp-backup/.github/workflows/weekly_backup.yml)）所需的兩個核心憑證變數：
- **`SP_COOKIES_JSON`**：SharePoint Online 登入連線憑證（`FedAuth` 與 `rtFa`）
- **`GDRIVE_OAUTH_TOKEN_JSON`**：Google Drive OAuth 2.0 授權憑證（包含 `refresh_token`）

---

## 🔗 快速連結

- **GitHub Secrets 設定頁面**：  
  https://github.com/frdshkg-sys/sp-backup/settings/secrets/actions
- **GitHub Actions 手動觸發備份頁面**：  
  https://github.com/frdshkg-sys/sp-backup/actions/workflows/weekly_backup.yml

---

## 1️⃣ 如何更新 `SP_COOKIES_JSON` (SharePoint 憑證)

當 SharePoint 工作階段過期（GitHub Actions 報錯 `HTTP 401 Unauthorized` 或 `HTTP 403 Forbidden`）時，請依以下步驟更新：

### 步驟 1：從 Chrome 瀏覽器取得最新 Cookie
1. 使用 Chrome 開啟並登入 SharePoint 網站：  
   https://k35n.sharepoint.com/sites/CHUNKING
2. 開啟開發人員工具（macOS 按 `Cmd + Option + I`；Windows 按 `F12`）。
3. 切換至頂部的 **Application（應用程式）** 分頁（若未顯示可點選 `>>` 展開）。
4. 在左側選單展開 **Storage > Cookies**，點選 `https://k35n.sharepoint.com`。
5. 在右側表格中找到以下兩個項目，分別雙擊複製它們的 **Value（值）**：
   - `FedAuth`
   - `rtFa`

### 步驟 2：在本機生成並驗證 `cookies.json`
在專案根目錄執行 [`update_cookies.py`](file:///Users/atelierdesmiyabi/Desktop/sp-backup/update_cookies.py)，它會自動向 SharePoint 測試連線並寫入 [`cookies.json`](file:///Users/atelierdesmiyabi/Desktop/sp-backup/cookies.json)：

```bash
python3 update_cookies.py "FedAuth=貼上FedAuth的值; rtFa=貼上rtFa的值"
```

成功時會顯示：
```text
✅ Success! SharePoint accepted the cookies (HTTP 200 FormDigestValue obtained).
💾 Updated .../cookies.json successfully!
```

> **手動格式參考**：`cookies.json` / `SP_COOKIES_JSON` 的內容格式如下：
> ```json
> {
>   "FedAuth": "77u/PD94bWwgdmVyc2lvbj0iMS4wIi...",
>   "rtFa": "c3R0aW5nc2J5dGVz..."
> }
> ```

### 步驟 3：複製並貼上至 GitHub Secret (`SP_COOKIES_JSON`)
1. 複製 `cookies.json` 的完整內容（macOS 可直接在終端機執行 `cat cookies.json | pbcopy`）。
2. 前往 [GitHub Actions Secrets 頁面](https://github.com/frdshkg-sys/sp-backup/settings/secrets/actions)。
3. 找到 **`SP_COOKIES_JSON`**，點擊右側的 **編輯（鉛筆圖示）**。
4. 將完整 JSON 內容貼入 **Value** 欄位，點擊 **Update secret**。

---

## 2️⃣ 如何更新 `GDRIVE_OAUTH_TOKEN_JSON` (Google Drive 憑證)

當 Google OAuth 憑證失效或需要重新授權（例如出現 `invalid_grant` 錯誤）時，請依以下步驟更新：

### 步驟 1：執行 OAuth 授權工具取得新 Token
1. 確認本機已安裝必要的 Python 套件：
   ```bash
   pip install google-auth-oauthlib google-api-python-client
   ```
2. 執行 [`backup/get_gdrive_oauth_token.py`](file:///Users/atelierdesmiyabi/Desktop/sp-backup/backup/get_gdrive_oauth_token.py)：
   ```bash
   python3 backup/get_gdrive_oauth_token.py
   ```
3. **自動讀取或輸入 Client ID**：
   - 若本機已有舊的 `backup/oauth_token.json` 或 `backup/client_secret.json`，腳本會自動沿用既有的 `client_id` 與 `client_secret`。
   - 若為全新環境，請依終端機提示貼上 Google Cloud Console（**APIs & Services > Credentials > OAuth 2.0 Client IDs (Desktop app)**）的 `Client ID` 與 `Client Secret`。
4. **瀏覽器登入授權**：
   - 腳本會自動開啟瀏覽器，請登入用於備份的 Google 帳號並點擊 **Continue / Allow（允許）**。
   - 授權完成後，腳本會將新憑證儲存至 [`backup/oauth_token.json`](file:///Users/atelierdesmiyabi/Desktop/sp-backup/backup/oauth_token.json)，並在終端機直接印出單行 JSON 字串。

> **格式參考**：`GDRIVE_OAUTH_TOKEN_JSON` 的內容格式如下：
> ```json
> {
>   "token": "ya29.a0...",
>   "refresh_token": "1//0g...",
>   "token_uri": "https://oauth2.googleapis.com/token",
>   "client_id": "xxxx.apps.googleusercontent.com",
>   "client_secret": "GOCSPX-xxxx",
>   "scopes": ["https://www.googleapis.com/auth/drive"]
> }
> ```

### 步驟 2：複製並貼上至 GitHub Secret (`GDRIVE_OAUTH_TOKEN_JSON`)
1. 複製終端機印出的 JSON 字串，或直接複製 `backup/oauth_token.json` 的內容（macOS 可執行 `cat backup/oauth_token.json | pbcopy`）。
2. 前往 [GitHub Actions Secrets 頁面](https://github.com/frdshkg-sys/sp-backup/settings/secrets/actions)。
3. 找到 **`GDRIVE_OAUTH_TOKEN_JSON`**，點擊右側的 **編輯（鉛筆圖示）**。
4. 將完整 JSON 內容貼入 **Value** 欄位，點擊 **Update secret**。

---

## 3️⃣ 一鍵驗證兩份憑證是否有效

在更新完本機的 `cookies.json` 與 `backup/oauth_token.json` 後，可執行 [`backup/verify_credentials.py`](file:///Users/atelierdesmiyabi/Desktop/sp-backup/backup/verify_credentials.py) 同時測試 SharePoint 與 Google Drive 連線：

```bash
python3 backup/verify_credentials.py
```

當看到以下輸出時，代表兩份憑證皆有效：
```text
==================================================
ALL PASS: 兩份 JSON 憑證皆正常可用！可以安心貼入 GitHub Secrets。
==================================================
```

---

## 4️⃣ 在 GitHub Actions 手動測試備份

更新完 GitHub Secrets 後，可立即觸發一次測試：
1. 前往 [Weekly SharePoint to Google Drive Backup Workflow](https://github.com/frdshkg-sys/sp-backup/actions/workflows/weekly_backup.yml)。
2. 點擊右側的 **Run workflow** 下拉按鈕 $\rightarrow$ 點擊綠色的 **Run workflow**。
3. 等待執行完成並確認狀態為綠色勾號（`✅`）。

