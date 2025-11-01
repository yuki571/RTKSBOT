# Discord Bot をWindowsタスクスケジューラーに登録するPowerShellスクリプト

$TaskName = "DiscordBot-AutoStart"
$BotPath = $PSScriptRoot
$ServiceScript = Join-Path $BotPath "service_wrapper.py"
$PythonExe = Join-Path $BotPath ".venv\Scripts\python.exe"

Write-Host "🔧 Discord Bot タスクスケジューラー設定" -ForegroundColor Cyan
Write-Host "📁 ボットパス: $BotPath" -ForegroundColor Yellow
Write-Host "🐍 Python実行ファイル: $PythonExe" -ForegroundColor Yellow

# 既存のタスクがある場合は削除
if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    Write-Host "⚠️ 既存のタスク '$TaskName' を削除します..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

# タスクアクション（実行するコマンド）
$Action = New-ScheduledTaskAction -Execute $PythonExe -Argument $ServiceScript -WorkingDirectory $BotPath

# タスクトリガー（起動条件）
$Trigger = @()
$Trigger += New-ScheduledTaskTrigger -AtStartup  # PC起動時
$Trigger += New-ScheduledTaskTrigger -Daily -At "00:00"  # 毎日0時（メンテナンス）

# タスク設定
$Settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -RestartCount 5 -RestartInterval (New-TimeSpan -Minutes 5) -ExecutionTimeLimit (New-TimeSpan -Days 365)

# タスクプリンシパル（実行ユーザー）
$Principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Highest

# タスク登録
try {
    Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -Principal $Principal
    Write-Host "✅ タスク '$TaskName' を正常に登録しました！" -ForegroundColor Green
    
    Write-Host "`n📋 タスク詳細:" -ForegroundColor Cyan
    Write-Host "  - 名前: $TaskName" -ForegroundColor White
    Write-Host "  - トリガー: PC起動時 + 毎日0時" -ForegroundColor White
    Write-Host "  - 実行ファイル: $PythonExe" -ForegroundColor White
    Write-Host "  - 作業ディレクトリ: $BotPath" -ForegroundColor White
    Write-Host "  - 自動再起動: 5回まで（5分間隔）" -ForegroundColor White
    
    Write-Host "`n🎯 使用方法:" -ForegroundColor Cyan
    Write-Host "  - タスク開始: Start-ScheduledTask -TaskName '$TaskName'" -ForegroundColor White
    Write-Host "  - タスク停止: Stop-ScheduledTask -TaskName '$TaskName'" -ForegroundColor White
    Write-Host "  - タスク削除: Unregister-ScheduledTask -TaskName '$TaskName' -Confirm:`$false" -ForegroundColor White
    
    # 即座にタスクを開始するか確認
    $Start = Read-Host "`n🚀 今すぐタスクを開始しますか？ (y/n)"
    if ($Start -eq "y" -or $Start -eq "Y") {
        Start-ScheduledTask -TaskName $TaskName
        Write-Host "✅ タスクを開始しました！" -ForegroundColor Green
    }
    
} catch {
    Write-Host "❌ タスク登録に失敗しました: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "💡 管理者権限でPowerShellを実行してください" -ForegroundColor Yellow
}

Write-Host "`nPress any key to continue..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")