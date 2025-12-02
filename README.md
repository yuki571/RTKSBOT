# Discord音楽Bot

## 必要なパッケージ
- discord.py[voice]
- yt-dlp
- ffmpeg（システムにインストール）

## 機能
- ボイスチャンネル参加/退出
- YouTube音楽再生
- 再生/一時停止/スキップ/停止
 - YouTubeのダウンロード（mp3 / mp4）

## 使い方
1. 必要なパッケージをインストール
2. `bot.py`にBotトークンを記入
3. Botを起動

### /ytdl コマンド
スラッシュコマンド `/ytdl` をつかって、YouTube動画を `mp3` または `mp4` でダウンロードしてDiscordへ送信できます。

例: `/ytdl url:https://www.youtube.com/watch?v=... format:mp3`

注意:
- Discordの添付ファイルサイズ制限（通常8MB）を超えるファイルは送信できません。大きなファイルは別のアップロード先が必要です。
- `ffmpeg` のインストールが必要です。

UI埋め込み（ボタン）:
- `format` を省略した場合、コマンドは動画の情報を含む埋め込み（Embed）を返し、MP3 / MP4ダウンロードボタンが表示されます。ボタンをクリックして形式を選択できます。

---

このREADMEはセットアップ後に詳細を追記します。