import sys
import time
import subprocess
import os
from pathlib import Path

class BotService:
    def __init__(self):
        self.bot_dir = Path(__file__).parent
        self.python_exe = self.bot_dir / '.venv' / 'Scripts' / 'python.exe'
        self.bot_script = self.bot_dir / 'bot.py'
        self.process = None
        self.restart_count = 0
        self.max_restarts = 10  # 1時間以内の最大再起動回数
        self.restart_window = 3600  # 1時間（秒）
        self.restart_times = []

    def should_restart(self):
        """再起動制限チェック"""
        current_time = time.time()
        # 1時間以内の再起動回数をカウント
        self.restart_times = [t for t in self.restart_times if current_time - t < self.restart_window]
        
        if len(self.restart_times) >= self.max_restarts:
            print(f"⚠️ 1時間以内に{self.max_restarts}回再起動しました。1時間待機します。")
            return False
        return True

    def start_bot(self):
        """ボットを起動"""
        try:
            print(f"🚀 ボットを開始: {self.bot_script}")
            self.process = subprocess.Popen(
                [str(self.python_exe), str(self.bot_script)],
                cwd=str(self.bot_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            return True
        except Exception as e:
            print(f"❌ ボット起動失敗: {e}")
            return False

    def monitor_bot(self):
        """ボットの監視とログ出力"""
        if not self.process:
            return False

        try:
            # リアルタイムでログ出力
            for line in iter(self.process.stdout.readline, ''):
                if line:
                    print(line.rstrip())
                
                # プロセスが終了したかチェック
                if self.process.poll() is not None:
                    break
            
            return_code = self.process.wait()
            print(f"🔄 ボットが終了しました（終了コード: {return_code}）")
            return return_code == 0
            
        except Exception as e:
            print(f"❌ 監視エラー: {e}")
            return False

    def run_service(self):
        """サービスのメインループ"""
        print("🔄 Discord Bot Service 開始")
        
        while True:
            try:
                if not self.should_restart():
                    time.sleep(3600)  # 1時間待機
                    continue

                # ボット起動
                if self.start_bot():
                    self.restart_times.append(time.time())
                    
                    # 監視開始
                    success = self.monitor_bot()
                    
                    if success:
                        print("✅ ボットが正常に終了しました")
                        break
                    else:
                        print("⚠️ ボットが異常終了しました。30秒後に再起動します...")
                        time.sleep(30)
                else:
                    print("❌ ボット起動に失敗しました。60秒後に再試行します...")
                    time.sleep(60)

            except KeyboardInterrupt:
                print("\n🛑 サービス停止要求を受信しました")
                if self.process:
                    self.process.terminate()
                    self.process.wait()
                break
            except Exception as e:
                print(f"❌ 予期しないエラー: {e}")
                time.sleep(60)

        print("✅ Discord Bot Service 終了")

if __name__ == "__main__":
    service = BotService()
    service.run_service()