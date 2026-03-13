# BR-TTS Neural Network Edition

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/)

ニューラルネットワーク音声合成システム / Neural Network Text-to-Speech System for Japanese

わずか数秒の音声サンプルから、高品質な日本語音声を生成します。

## 特徴

- 🎯 **高品質な音声合成**: 深層学習による自然なイントネーション
- ⚡ **Few-shot Learning**: 3-10秒の音声サンプルで声を再現
- 🎨 **使いやすいGUI**: 専門知識不要の直感的なインターフェース
- 🔢 **数字自動変換**: 「15時」→「十五時」など自動変換
- 📊 **ログ機能**: 処理ログの詳細記録
- 🌐 **オープンソース**: GPL v3ライセンス

## デモ

![BR-TTS NNW Screenshot](docs/screenshot.png)

## インストール

### 必須環境

- Windows 10/11 (64bit)
- Python 3.11
- メモリ: 8GB以上（推奨: 16GB以上）
- GPU: NVIDIA GPU推奨（CUDA対応）

### 手順

1. リポジトリをクローン

```bash
git clone https://github.com/br-systems/br-tts-nnw.git
cd br-tts-nnw
```

2. Conda環境を作成

```bash
conda create -n tts_nnw0 python=3.11 -y
conda activate tts_nnw0
```

3. 依存パッケージをインストール

```bash
pip install -r requirements.txt
```

4. PyTorch（CUDA版）をインストール

```bash
pip install torch==2.1.0+cu118 torchaudio==2.1.0+cu118 --index-url https://download.pytorch.org/whl/cu118
```

## 使い方

### 基本的な使い方

1. アプリケーションを起動

```bash
python tts_gui.py
```

2. 音声サンプルを選択
   - 「選択」ボタンから音声サンプル（.wavファイル）を選択
   - 推奨: 3-10秒、クリアな音質

3. テキストを入力
   - テキスト欄に音声化したい文章を入力

4. 音声合成
   - 「音声合成」ボタンをクリック
   - 処理完了後、「再生」または「保存」

### 音声サンプルについて

最適な音声サンプル：
- 形式: WAVファイル（16bit, 22050Hz推奨）
- 長さ: 3-10秒
- 内容: クリアで雑音の少ない、感情表現が豊かな録音

## 技術仕様

| 項目 | 詳細 |
|------|------|
| 音声合成エンジン | Coqui TTS (XTTS v2) |
| アーキテクチャ | VITS + ECAPA-TDNN |
| 対応言語 | 日本語（主）、その他多言語 |
| GPU加速 | CUDA 11.8 |
| 平均処理時間 | 約20-30秒/文章 |

## ライセンス

本ソフトウェアは [GNU General Public License v3.0](LICENSE) の下でライセンスされています。

### サードパーティライセンス

- Coqui TTS - Mozilla Public License 2.0
- PyTorch - BSD License
- PyQt5 - GPL v3

詳細は [THIRD_PARTY_NOTICES.txt](THIRD_PARTY_NOTICES.txt) を参照。

## 生成された音声の使用について

本ソフトウェアで生成された音声の著作権は、ユーザーに帰属します。商用利用を含め、自由に使用できます。

**注意**: 音声サンプルに使用した音声の権利処理は、ユーザーの責任で行ってください。

## 商用版

技術サポート付きの商用版（exe形式）も提供しています：

- 価格: 9,800円（税込）
- インストーラー付き
- 日本語マニュアル
- メールサポート（30日間）

詳細: [https://brsystems.jp/comitia/br-tts-neural-network-edition/](https://brsystems.jp/comitia/br-tts-neural-network-edition/)

## 貢献

プルリクエストを歓迎します！大きな変更の場合は、まずIssueを開いて変更内容を議論してください。

## サポート

- **商用版サポート**: support@brsystems.jp
- **GitHub Issues**: [Issues](https://github.com/br-systems/br-tts-nnw/issues)
- **公式サイト**: [https://brsystems.jp](https://brsystems.jp)

## 開発者

**BR SYSTEMS**
- Website: [https://brsystems.jp](https://brsystems.jp)
- Email: info@brsystems.jp

## 謝辞

本プロジェクトは以下のオープンソースプロジェクトを使用しています：

- [Coqui TTS](https://github.com/coqui-ai/TTS)
- [PyTorch](https://pytorch.org/)
- その他多数のオープンソースライブラリ

## 更新履歴

### Version 1.0.0 (2025-03-12)
- 初回リリース
- 基本的な音声合成機能
- 数字自動変換機能
- GUI実装
- ログ機能

---

Copyright (C) 2025 BR SYSTEMS. All rights reserved.
