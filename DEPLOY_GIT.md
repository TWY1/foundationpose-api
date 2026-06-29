# FoundationPose API — Git 部署步驟

## 前置需求

- GitHub 帳號 (免費註冊: https://github.com/signup)
- Git 已安裝 (`git --version`)

---

## 步驟 1：在 GitHub 上建立空倉庫

1. 打開 https://github.com/new
2. 填寫 Repository name: `foundationpose-api`
3. 選 **Private** 或 **Public**
4. 不要勾任何選項（README、.gitignore、license 都不要勾）
5. 點 **Create repository**

你會看到一個頁面，裡面有幾串指令。找到長這樣的那行：

```
git remote add origin https://github.com/你的帳號/foundationpose-api.git
```

複製那行，下一步會用到。

---

## 步驟 2：初始化本地 Git + 上傳

在 Mac 或 Ubuntu 上執行：

```bash
cd ~/Documents/ope/FoundationPose

# 初始化 git
git init

# 加入所有檔案（weights 已被 .gitignore 排除）
git add .

# 確認沒把大檔案加進去
git status

# 提交
git commit -m "Initial commit: FoundationPose API service"

# 連接到 GitHub（貼上剛才複製的那行）
git remote add origin https://github.com/你的帳號/foundationpose-api.git

# 上傳
git push -u origin main
```

如果 `git push` 要求輸入帳號密碼，改成用 **Personal Access Token**：

1. 到 https://github.com/settings/tokens → Generate new token (classic)
2. 勾 `repo` 權限
3. 複製 token
4. 在 terminal 輸入帳號時打你的 GitHub 用戶名
5. 密碼欄貼上 token

---

## 步驟 3：對方下載

對方在他的 Ubuntu 機器上：

```bash
# 如果倉庫是 Public
git clone https://github.com/你的帳號/foundationpose-api.git

# 如果倉庫是 Private（需要 token）
git clone https://你的帳號:你的token@github.com/你的帳號/foundationpose-api.git

cd foundationpose-api

# 下載模型權重 (~2GB)
bash scripts/download_weights.sh ./weights

# 用 Docker 啟動
make build
make run

# 或用 docker compose
docker compose up -d --build

# 測試
curl http://localhost:8000/api/v1/health
```

---

## 步驟 4：後續更新

你修改程式碼後：

```bash
cd ~/Documents/ope/FoundationPose
git add .
git commit -m "修改了 XXX"
git push
```

對方更新：

```bash
cd foundationpose-api
git pull
docker compose up -d --build  # 重新 build + 重啟
```

---

## 附錄：改用 GitHub CLI

如果你想用指令建立倉庫，先安裝 `gh`：

```bash
# Mac
brew install gh

# Ubuntu
sudo apt install gh
```

然後：

```bash
gh auth login          # 登入 GitHub
cd ~/Documents/ope/FoundationPose
git init
git add .
git commit -m "Initial commit"
gh repo create foundationpose-api --public --push
```
