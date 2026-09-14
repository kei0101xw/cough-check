# Cough Check（iPhone）

iOS 17以降・縦画面。Xcodeで cough-check.xcodeproj を開き、iPhoneを選択して実行します。

トップ → 録音開始 → 停止 → API解析結果の3画面です。
参考SwiftUIの青い背景、白い上部角丸パネル、青色の大きなボタンを踏襲しています。

## API接続

AppInfo.plist の CoughAPIURL が接続先です。
初期値は http://localhost:8000/api/cough-check/analyze/（シミュレータ用）。
Xcode Schemeの環境変数 COUGH_API_URL で上書きもできます。

実機の localhost はiPhone自身を指すため、Macのホスト名
（例：http://your-mac.local:8000/api/cough-check/analyze/）またはHTTPSのサーバーURLに変更してください。
ローカル接続ではMacとiPhoneを同じネットワークに接続し、Djangoを
uv run python manage.py runserver 0.0.0.0:8000 で起動します。
バックエンドの ALLOWED_HOSTS に接続先のホスト名を許可してください。
配布時はHTTPSの接続先を設定してください。

録音は44.1kHz / モノラル / 16bit PCM WAVとして一時保存し、
multipart/form-data の audio フィールドで送信します。
解析終了・ホーム移動・再録音で一時ファイルを削除します。
バックグラウンド移行や音声割り込み時は録音を中断し、再録音を案内します。

average_positive_score（0〜1）を百分率と円形ゲージで表示します。
バックエンド仕様上、未校正のモデルスコアなので診断確率とは表記しません。
咳が0回でスコアがnullの場合は、0%ではなく再録音の案内を表示します。
