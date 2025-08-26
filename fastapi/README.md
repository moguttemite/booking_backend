# FastAPI 講座予約システム バックエンド

## 起動方法

### 方法1：uvicorn で直接起動（推奨）
```bash
# 開発環境（自動リロード付き）
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 本番環境
uvicorn main:app --host 0.0.0.0 --port 8000
```

### 方法2：開発スクリプトで起動
```bash
python start.py
```

### 方法3：uvicorn 設定ファイルを使用
```bash
uvicorn main:app --config uvicorn.conf
```

## アクセスURL

- **API ドキュメント**: http://localhost:8000/docs
- **ReDoc ドキュメント**: http://localhost:8000/redoc
- **ヘルスチェック**: http://localhost:8000/health
- **API ルートパス**: http://localhost:8000/

## プロジェクト構造

```
fastapi/
├── main.py              # FastAPI アプリケーションエントリーポイント
├── start.py             # 開発起動スクリプト
├── requirements.txt     # 依存パッケージ
└── app/
    ├── api/             # API ルート
    ├── core/            # コア設定
    ├── db/              # データベース
    ├── models/          # データモデル
    ├── schemas/         # Pydantic モデル
    └── services/        # ビジネスロジック
```

## なぜ uvicorn で直接起動を推奨するのか？

1. **より柔軟**: ポート、ホスト、リロードなどのパラメータを簡単に設定可能
2. **本番標準**: 本番環境での標準的な方法
3. **より良いパフォーマンス**: より良いパフォーマンスと設定オプション
4. **デプロイしやすい**: コンテナ化デプロイとプロセス管理が容易
