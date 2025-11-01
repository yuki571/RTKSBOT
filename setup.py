#!/usr/bin/env python3
"""
RTKS Discord Bot - 多機能Discordボット
"""

from setuptools import setup, find_packages
import pathlib
import re

# プロジェクトのルートディレクトリ
HERE = pathlib.Path(__file__).parent

# READMEファイルの内容を取得
README = (HERE / "README.md").read_text(encoding="utf-8")

# バージョン情報をbot.pyから抽出
def get_version():
    try:
        with open("bot.py", "r", encoding="utf-8") as f:
            content = f.read()
            version_match = re.search(r"__version__\s*=\s*['\"]([^'\"]*)['\"]", content)
            if version_match:
                return version_match.group(1)
    except:
        pass
    return "1.0.0"

# 必須依存関係をrequirements.txtから読み込み
def get_requirements():
    try:
        with open("requirements/requirements.txt", "r", encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip() and not line.startswith("#")]
    except:
        # フォールバック
        return [
            "discord.py>=2.3.2",
            "aiosqlite>=0.19.0",
            "aiohttp>=3.8.5",
            "flask>=2.3.3",
            "yt-dlp>=2023.7.6",
            "PyNaCl>=1.5.0",
            "python-dotenv>=1.0.0",
            "requests>=2.31.0",
        ]

# 開発用依存関係
EXTRAS_REQUIRE = {
    "dev": [
        "pytest>=7.4.0",
        "pytest-asyncio>=0.21.1",
        "black>=23.7.0",
        "flake8>=6.0.0",
        "mypy>=1.5.0",
        "pre-commit>=3.3.3",
    ],
    "audio": [
        "ffmpeg-python>=0.2.0",
    ],
    "voice": [
        "speechrecognition>=3.10.0",
        "pydub>=0.25.1",
    ]
}

# すべての追加パッケージ
EXTRAS_REQUIRE["all"] = list(set(sum(EXTRAS_REQUIRE.values(), [])))

setup(
    name="rtks-discord-bot",
    version=get_version(),
    description="多機能Discord Bot - 音楽再生、経済システム、自己紹介システム、認証システムなど",
    long_description=README,
    long_description_content_type="text/markdown",
    url="https://github.com/your-username/rtks-discord-bot",
    author="YukiSannn",
    author_email="your-email@example.com",
    license="MIT",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Communications :: Chat",
        "Topic :: Internet",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    keywords="discord bot music economy voice japanese",
    packages=find_packages() + ['modules'],
    package_dir={'modules': 'modules'},
    python_requires=">=3.8",
    install_requires=get_requirements(),
    extras_require=EXTRAS_REQUIRE,
    entry_points={
        "console_scripts": [
            "rtks-bot=bot:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.md", "*.txt", "*.json", "*.sql", "*.bat", "*.sh"],
    },
    zip_safe=False,
    project_urls={
        "Bug Reports": "https://github.com/your-username/rtks-discord-bot/issues",
        "Source": "https://github.com/your-username/rtks-discord-bot",
        "Documentation": "https://github.com/your-username/rtks-discord-bot/wiki",
    },
)