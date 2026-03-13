# -*- coding: utf-8 -*-
"""
TTS GUI - 音声合成ツール（プロトタイプ）
"""

# -*- coding: utf-8 -*-
"""
TTS GUI - 音声合成ツール（PySide6版）
"""

import sys
import os
import logging
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTextEdit, QPushButton, QLabel,
                             QFileDialog, QSlider, QCheckBox, QProgressBar,
                             QDialog, QTableWidget, QTableWidgetItem, QHeaderView,
                             QMessageBox)
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QFrame
from PyQt5.QtWidgets import QTextEdit  # ログビューアー用
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from TTS.api import TTS
import torch
from pydub import AudioSegment
import tempfile

class TTSWorker(QThread):
    """音声合成を別スレッドで実行"""
    finished = pyqtSignal(str)  # 完了シグナル（ファイルパス）
    error = pyqtSignal(str)     # エラーシグナル

    def __init__(self, tts, text, speaker_wav, output_path):
        super().__init__()
        self.tts = tts
        self.text = text
        self.speaker_wav = speaker_wav
        self.output_path = output_path
    
    def run(self):
        try:
            self.tts.tts_to_file(
                text=self.text,
                file_path=self.output_path,
                speaker_wav=self.speaker_wav,
                language="ja"
            )
            self.finished.emit(self.output_path)
        except Exception as e:
            self.error.emit(str(e))

###################################################################################
class SpeakerSelectionDialog(QDialog):
    """音声サンプル選択ダイアログ"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_file = None
        self.init_ui()
        self.load_wav_files()
    
    def init_ui(self):
        """UI初期化"""
        self.setWindowTitle('音声サンプルを選択')
        self.setGeometry(200, 200, 700, 500)
        
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # タイトル
        title = QLabel('音声サンプルを選択してください')
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)
        
        # 説明
        info = QLabel('試聴してから最適な音声サンプルを選択できます')
        info.setStyleSheet("color: #666;")
        layout.addWidget(info)
        
        # フォルダ選択（ここを追加）
        folder_layout = QHBoxLayout()
        folder_layout.addWidget(QLabel('フォルダ:'))
        self.folder_label = QLabel('C:/TTS-NNW/voice_data/yuji4thvoice/wavs')
        self.folder_label.setStyleSheet("color: #666;")
        folder_layout.addWidget(self.folder_label)
        folder_layout.addStretch()
        change_folder_btn = QPushButton('フォルダ変更')
        change_folder_btn.clicked.connect(self.change_folder)
        folder_layout.addWidget(change_folder_btn)
        layout.addLayout(folder_layout)        
        
        # テーブル作成
        from PyQt5.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(['ファイル名', '長さ(秒)', 'サイズ(KB)', '試聴', '選択'])
        
        # 列幅調整
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        
        layout.addWidget(self.table)
        
        # 選択中のファイル表示
        self.selected_label = QLabel('選択中: なし')
        self.selected_label.setStyleSheet("font-weight: bold; color: #4CAF50;")
        layout.addWidget(self.selected_label)
        
        # ボタン
        button_layout = QHBoxLayout()
        
        self.ok_btn = QPushButton('OK')
        self.ok_btn.clicked.connect(self.accept)
        self.ok_btn.setEnabled(False)
        button_layout.addWidget(self.ok_btn)
        
        cancel_btn = QPushButton('キャンセル')
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
    
    def load_wav_files(self):
        """wavファイルを読み込み"""
        import wave
        from PyQt5.QtWidgets import QTableWidgetItem
        
        folder = self.folder_label.text()  # ← ここを変更
        
        if not os.path.exists(folder):
            QMessageBox.warning(self, 'エラー', f'フォルダが見つかりません: {folder}')
            return
        
        wav_files = [f for f in os.listdir(folder) if f.endswith('.wav')]
        
        if len(wav_files) == 0:
            QMessageBox.information(self, '情報', 'wavファイルが見つかりませんでした')
            return
        
        wav_files.sort()
        
        self.table.setRowCount(len(wav_files))
        
        for idx, filename in enumerate(wav_files):
            filepath = os.path.join(folder, filename)
            
            # ファイル名
            name_item = QTableWidgetItem(filename)
            self.table.setItem(idx, 0, name_item)
            
            # 長さ取得
            try:
                with wave.open(filepath, 'rb') as wav_file:
                    frames = wav_file.getnframes()
                    rate = wav_file.getframerate()
                    duration = frames / float(rate)
                    
                duration_item = QTableWidgetItem(f"{duration:.1f}")
                self.table.setItem(idx, 1, duration_item)
            except:
                duration_item = QTableWidgetItem("N/A")
                self.table.setItem(idx, 1, duration_item)
            
            # サイズ
            size_kb = os.path.getsize(filepath) / 1024
            size_item = QTableWidgetItem(f"{size_kb:.1f}")
            self.table.setItem(idx, 2, size_item)
            
            # 試聴ボタン
            preview_btn = QPushButton('▶ 試聴')
            preview_btn.clicked.connect(lambda checked, f=filepath: self.preview_audio(f))
            self.table.setCellWidget(idx, 3, preview_btn)
            
            # 選択ボタン
            select_btn = QPushButton('選択')
            select_btn.setStyleSheet("background-color: #2196F3; color: white;")
            select_btn.clicked.connect(lambda checked, f=filepath, n=filename: self.select_file(f, n))
            self.table.setCellWidget(idx, 4, select_btn)
    
    def preview_audio(self, filepath):
        """音声を試聴"""
        try:
            import subprocess
            # バックグラウンドで再生（ノンブロッキング）
            subprocess.Popen(['ffplay', '-nodisp', '-autoexit', filepath],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(self, 'エラー', f'再生エラー: {str(e)}')
    
    def select_file(self, filepath, filename):
        """ファイルを選択"""
        self.selected_file = filepath
        self.selected_label.setText(f'選択中: {filename}')
        self.ok_btn.setEnabled(True)
    
    def change_folder(self):
        """フォルダを変更"""
        folder = QFileDialog.getExistingDirectory(
            self, 'wavファイルのフォルダを選択',
            self.folder_label.text()
        )
        
        if folder:
            self.folder_label.setText(folder)
            self.load_wav_files()

class TTSApp(QMainWindow):
    def __init__(self):
        super().__init__()
        #
        self.setup_logging()
        logging.info("=" * 60)
        logging.info("BR-TTS NNW 起動")
        logging.info(f"起動時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logging.info("=" * 60)        
        #
        self.tts = None
        self.current_audio_file = None
        self.speaker_wav = None
        self.init_ui()
        self.load_model()
    
    def init_ui(self):

        """UI初期化"""
        self.setWindowTitle('BR SYSTEMS - TTS 音声合成ツール')
        self.setGeometry(100, 100, 650, 550)
        
        # メインウィジェット
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout()
        main_widget.setLayout(layout)
        
        # ヘッダー（ロゴ + タイトル）
        header_layout = QHBoxLayout()
                
        # タイトル
        title = QLabel('ニューラルネットワーク音声合成')
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # ロゴ（右上）
        logo_label = QLabel()
        logo_path = "C:/TTS-NNW/BRS_LOGO.png"
        if os.path.exists(logo_path):
            from PyQt5.QtGui import QPixmap
            pixmap = QPixmap(logo_path)
            # ロゴサイズ調整（幅150px）
            pixmap = pixmap.scaledToWidth(150, Qt.SmoothTransformation)
            logo_label.setPixmap(pixmap)
        else:
            logo_label.setText('BR SYSTEMS')
            logo_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        header_layout.addWidget(logo_label)
        
        layout.addLayout(header_layout)
        
        # 区切り線
        from PyQt5.QtWidgets import QFrame
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)
        
        # テキスト入力エリア
        layout.addWidget(QLabel('合成するテキスト:'))
        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText('ここに音声化したいテキストを入力してください...')
        self.text_edit.setMaximumHeight(150)
        layout.addWidget(self.text_edit)
        
        # 数字変換オプション
        self.convert_numbers_cb = QCheckBox('数字を自動変換（15時→十五時）')
        self.convert_numbers_cb.setChecked(True)
        layout.addWidget(self.convert_numbers_cb)
        
        # 音声サンプル選択
        speaker_layout = QHBoxLayout()
        speaker_layout.addWidget(QLabel('音声サンプル:'))
        self.speaker_label = QLabel('未選択')
        speaker_layout.addWidget(self.speaker_label)
        self.speaker_btn = QPushButton('選択')
        self.speaker_btn.clicked.connect(self.select_speaker)
        speaker_layout.addWidget(self.speaker_btn)
        layout.addLayout(speaker_layout)
        
        # 合成ボタン
        self.synthesize_btn = QPushButton('音声合成')
        self.synthesize_btn.clicked.connect(self.synthesize)
        self.synthesize_btn.setStyleSheet("font-size: 14px; padding: 10px;")
        self.synthesize_btn.setEnabled(False)
        layout.addWidget(self.synthesize_btn)
        
        # 進捗表示
        self.status_label = QLabel('準備完了')
        layout.addWidget(self.status_label)
        
        # 再生速度調整
        speed_layout = QHBoxLayout()
        speed_layout.addWidget(QLabel('再生速度:'))
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setMinimum(50)   # 0.5倍
        self.speed_slider.setMaximum(200)  # 2.0倍
        self.speed_slider.setValue(100)    # 1.0倍
        self.speed_slider.setTickInterval(10)
        self.speed_slider.setTickPosition(QSlider.TicksBelow)
        self.speed_slider.valueChanged.connect(self.update_speed_label)
        speed_layout.addWidget(self.speed_slider)
        self.speed_label = QLabel('1.0x')
        speed_layout.addWidget(self.speed_label)
        layout.addLayout(speed_layout)
        
        # 再生・保存ボタン
        button_layout = QHBoxLayout()
        self.play_btn = QPushButton('再生')
        self.play_btn.clicked.connect(self.play_audio)
        self.play_btn.setEnabled(False)
        button_layout.addWidget(self.play_btn)
        
        self.save_btn = QPushButton('名前を付けて保存')
        self.save_btn.clicked.connect(self.save_audio)
        self.save_btn.setEnabled(False)
        button_layout.addWidget(self.save_btn)
        layout.addLayout(button_layout)
        
        # Exitボタン
        exit_layout = QHBoxLayout()
        #
        self.log_btn = QPushButton('ログ表示')
        self.log_btn.clicked.connect(self.show_log_viewer)
        self.log_btn.setStyleSheet("padding: 5px 20px;")
        exit_layout.addWidget(self.log_btn)       
        #
        exit_layout.addStretch()
        self.exit_btn = QPushButton('Exit')
        self.exit_btn.clicked.connect(self.close)
        self.exit_btn.setStyleSheet("padding: 5px 20px;")
        exit_layout.addWidget(self.exit_btn)
        layout.addLayout(exit_layout)
        
        layout.addStretch()
        #
    def setup_logging(self):
        """ロギング設定"""
        # logsフォルダ作成
        log_dir = "logs"
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        # ログファイル名（日付付き）
        log_file = os.path.join(log_dir, f"tts_gui_{datetime.now().strftime('%Y%m%d')}.log")
        
        # ロギング設定
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler()  # コンソールにも出力
            ]
        )        
        #
    def load_model(self):
        """TTSモデルをロード"""
        self.status_label.setText('モデルロード中...')
        QApplication.processEvents()
        
        try:
            # weights_only問題の回避
            original_load = torch.load
            def patched_load(*args, **kwargs):
                kwargs['weights_only'] = False
                return original_load(*args, **kwargs)
            torch.load = patched_load
            
            device = "cuda" if torch.cuda.is_available() else "cpu"
            self.tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(device)
            
            # デフォルト音声サンプル
            default_speaker = "C:/TTS-NNW/voice_data/yuji4thvoice/wavs/conv_0005.wav"
            if os.path.exists(default_speaker):
                self.speaker_wav = default_speaker
                self.speaker_label.setText('conv_0005.wav')
                self.synthesize_btn.setEnabled(True)
            
            self.status_label.setText(f'準備完了（デバイス: {device}）')
        except Exception as e:
            self.status_label.setText(f'エラー: {str(e)}')
    
    def select_speaker(self):
        """音声サンプルファイルを選択""" 
        # ダイアログを表示
        dialog = SpeakerSelectionDialog(self)
              
        if dialog.exec_() == QDialog.Accepted and dialog.selected_file:
            self.speaker_wav = dialog.selected_file
            self.speaker_label.setText(os.path.basename(dialog.selected_file))
            self.synthesize_btn.setEnabled(True)
    
    def convert_numbers_to_kanji(self, text):
        """数字を漢数字に変換（完全版・修正済み）"""
       
        def num_to_kanji(num):
            """0-999の数値を漢数字に変換"""
            if num == 0:
                return '零'
            
            kanji_map = ['', '一', '二', '三', '四', '五', '六', '七', '八', '九']
            
            # 1-9
            if num < 10:
                return kanji_map[num]
            
            # 10-99
            elif num < 100:
                tens = num // 10
                ones = num % 10
                
                if num == 10:
                    return '十'
                elif num < 20:
                    return '十' + kanji_map[ones]
                else:
                    result = kanji_map[tens] + '十'
                    if ones > 0:
                        result += kanji_map[ones]
                    return result
            
            # 100-999
            else:
                hundreds = num // 100
                remainder = num % 100
                result = kanji_map[hundreds] + '百'
                if remainder > 0:
                    result += num_to_kanji(remainder)
                return result
        
        # 時刻の変換（0-24時）
        for hour in range(24, -1, -1):
            text = text.replace(f'{hour}時', num_to_kanji(hour) + '時')
        
        # 分の変換（0-59分）
        for minute in range(59, -1, -1):
            text = text.replace(f'{minute}分', num_to_kanji(minute) + '分')
        
        # 秒の変換（0-59秒）
        for second in range(59, -1, -1):
            text = text.replace(f'{second}秒', num_to_kanji(second) + '秒')
        
        # 期間の「ヶ月」「カ月」の変換（0-120ヶ月）
        for months in range(120, -1, -1):
            text = text.replace(f'{months}ヶ月', num_to_kanji(months) + 'カ月')
            text = text.replace(f'{months}カ月', num_to_kanji(months) + 'カ月')
            text = text.replace(f'{months}か月', num_to_kanji(months) + 'カ月')
            text = text.replace(f'{months}ケ月', num_to_kanji(months) + 'カ月')
        
        # 年齢の変換（0-120歳）
        # 70代は発音を明確にするため、ひらがな混在に変換
        for age in range(120, -1, -1):
            if 70 <= age <= 79:
                # 70代専用処理
                ones = age % 10
                ones_hira = ['', 'いち', 'に', 'さん', 'よん', 'ご', 'ろく', 'なな', 'はち', 'きゅう']
                if ones == 0:
                    converted = 'ななじゅうさい'
                else:
                    converted = f'ななじゅう{ones_hira[ones]}さい'
                text = text.replace(f'{age}歳', converted)
            else:
                # 通常処理
                text = text.replace(f'{age}歳', num_to_kanji(age) + '歳')
        
        # 日付の変換（1-31日）
        for day in range(31, 0, -1):
            text = text.replace(f'{day}日', num_to_kanji(day) + '日')
        
        # 月の変換（1-12月）
        for month in range(12, 0, -1):
            text = text.replace(f'{month}月', num_to_kanji(month) + '月')
        
        # 年の変換（1900-2099年）
        for year in range(2099, 1899, -1):
            if f'{year}年' in text:
                kanji_map = ['', '一', '二', '三', '四', '五', '六', '七', '八', '九']
                
                thousands = year // 1000
                hundreds = (year % 1000) // 100
                tens = (year % 100) // 10
                ones = year % 10
                
                year_kanji = ''
                if thousands > 0:
                    year_kanji += kanji_map[thousands] + '千'
                if hundreds > 0:
                    year_kanji += kanji_map[hundreds] + '百'
                if tens > 0:
                    year_kanji += kanji_map[tens] + '十'
                if ones > 0:
                    year_kanji += kanji_map[ones]
                
                text = text.replace(f'{year}年', year_kanji + '年')
        
        # その他の単位
        units = ['個', '人', '回', '本', '台', '枚', '冊', '匹', '杯', '件', '円']
        for unit in units:
            for num in range(999, -1, -1):
                if f'{num}{unit}' in text:
                    text = text.replace(f'{num}{unit}', num_to_kanji(num) + unit)
        
        return text

    def synthesize(self):
        """音声合成実行"""
    
        text = self.text_edit.toPlainText().strip()
        if not text:
            self.status_label.setText('テキストを入力してください')
            return
        
        if not self.speaker_wav:
            self.status_label.setText('音声サンプルを選択してください')
            return
        
        logging.info(f"音声合成開始: テキスト='{text[:50]}...'")  # ★追加★       
        
        # 数字変換
        if self.convert_numbers_cb.isChecked():
            text = self.convert_numbers_to_kanji(text)
        
        # 一時ファイル
        self.current_audio_file = tempfile.mktemp(suffix='.wav')
        
        # 合成開始の視覚的フィードバック
        self.status_label.setStyleSheet("font-size: 14px; color: #FF9800;")
        self.status_label.setText('🔄 音声合成中... お待ちください')
        self.synthesize_btn.setStyleSheet(
            "font-size: 14px; padding: 10px; background-color: #CCCCCC;"
        )
        self.synthesize_btn.setEnabled(False)
        QApplication.processEvents()
        
        # 以下、既存のコード...
        # ワーカースレッド起動
        self.worker = TTSWorker(self.tts, text, self.speaker_wav, self.current_audio_file)
        self.worker.finished.connect(self.on_synthesis_finished)
        self.worker.error.connect(self.on_synthesis_error)
        self.worker.start()
    
    def on_synthesis_finished(self, file_path):
        """合成完了"""
        logging.info(f"音声合成完了: {file_path}")  # ★追加★        
        # ボタンを緑色に変更
        self.synthesize_btn.setStyleSheet(
            "font-size: 14px; padding: 10px; "
            "background-color: #4CAF50; color: white; font-weight: bold;"
        )
        self.synthesize_btn.setText('音声合成 ✓ 完了')
        self.synthesize_btn.setEnabled(True)
        
        # ステータスメッセージを強調
        self.status_label.setStyleSheet(
            "font-size: 16px; color: #4CAF50; font-weight: bold;"
        )
        self.status_label.setText('✓ 合成完了！再生できます')
        
        # 再生・保存ボタンを有効化
        self.play_btn.setEnabled(True)
        self.save_btn.setEnabled(True)
        
        # 2秒後にボタンを元に戻す
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(2000, self.reset_synthesize_button)

    def reset_synthesize_button(self):
        """音声合成ボタンを元に戻す"""
        self.synthesize_btn.setStyleSheet("font-size: 14px; padding: 10px;")
        self.synthesize_btn.setText('音声合成')
        self.status_label.setStyleSheet("")
        self.status_label.setText('準備完了')
        #
    def show_log_viewer(self):
        """ログビューアーを表示"""
        dialog = LogViewerDialog(self)
        dialog.exec_()               
#
    def on_synthesis_error(self, error_msg):
        """合成エラー"""
        logging.error(f"音声合成エラー: {error_msg}")  # ★追加★
        self.status_label.setText(f'エラー: {error_msg}')
        self.synthesize_btn.setEnabled(True)
    
    def update_speed_label(self):
        """速度ラベル更新"""
        speed = self.speed_slider.value() / 100.0
        self.speed_label.setText(f'{speed:.1f}x')
    
    def play_audio(self):
        """音声再生（速度調整付き）"""
        if not self.current_audio_file or not os.path.exists(self.current_audio_file):
            return
        
        try:
            self.status_label.setText('再生中...')
            QApplication.processEvents()
            
            # 速度調整
            speed = self.speed_slider.value() / 100.0
            
            if speed == 1.0:
                # 速度変更なし：元ファイルを直接再生
                import subprocess
                subprocess.run(['ffplay', '-nodisp', '-autoexit', self.current_audio_file], 
                             check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                # 速度変更あり：一時ファイルを作成して再生
                audio = AudioSegment.from_wav(self.current_audio_file)
                audio = audio._spawn(audio.raw_data, overrides={
                    "frame_rate": int(audio.frame_rate * speed)
                }).set_frame_rate(audio.frame_rate)
                
                # 出力フォルダに一時ファイルを作成
                temp_file = "C:/TTS-NNW/outputs/temp_playback.wav"
                audio.export(temp_file, format="wav")
                
                import subprocess
                subprocess.run(['ffplay', '-nodisp', '-autoexit', temp_file],
                             check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                
                # 再生後に削除
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            
            self.status_label.setText('再生完了')
        except Exception as e:
            self.status_label.setText(f'再生エラー: {str(e)}')
    
    def save_audio(self):
        """音声ファイルを保存"""
        if not self.current_audio_file or not os.path.exists(self.current_audio_file):
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, '名前を付けて保存',
            'C:/TTS-NNW/outputs/output.wav',
            'WAV Files (*.wav)'
        )
        
        if file_path:
            try:
                import shutil
                shutil.copy(self.current_audio_file, file_path)
                self.status_label.setText(f'保存完了: {os.path.basename(file_path)}')
            except Exception as e:
                self.status_label.setText(f'保存エラー: {str(e)}')

class LogViewerDialog(QDialog):
    """ログビューアーダイアログ"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        self.load_log()
    
    def init_ui(self):
        """UI初期化"""
        self.setWindowTitle('ログビューアー')
        self.setGeometry(200, 200, 800, 600)
        
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # タイトル
        title = QLabel('処理ログ')
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)
        
        # ログ表示エリア
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("font-family: 'Courier New', monospace; font-size: 10pt;")
        layout.addWidget(self.log_text)
        
        # ボタン
        button_layout = QHBoxLayout()
        
        refresh_btn = QPushButton('更新')
        refresh_btn.clicked.connect(self.load_log)
        button_layout.addWidget(refresh_btn)
        
        clear_btn = QPushButton('ログクリア')
        clear_btn.clicked.connect(self.clear_log)
        button_layout.addWidget(clear_btn)
        
        close_btn = QPushButton('閉じる')
        close_btn.clicked.connect(self.close)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
    
    def load_log(self):
        """ログファイルを読み込み"""
        log_file = os.path.join("logs", f"tts_gui_{datetime.now().strftime('%Y%m%d')}.log")
        
        if os.path.exists(log_file):
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.log_text.setPlainText(content)
                # 最後の行にスクロール
                self.log_text.moveCursor(self.log_text.textCursor().End)
            except Exception as e:
                self.log_text.setPlainText(f'ログ読み込みエラー: {str(e)}')
        else:
            self.log_text.setPlainText('ログファイルが見つかりません。')
    
    def clear_log(self):
        """ログをクリア"""
        reply = QMessageBox.question(
            self, '確認',
            'ログをクリアしますか？',
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            log_file = os.path.join("logs", f"tts_gui_{datetime.now().strftime('%Y%m%d')}.log")
            if os.path.exists(log_file):
                with open(log_file, 'w', encoding='utf-8') as f:
                    f.write('')
                logging.info("ログがクリアされました")
                self.load_log()
                
# ★ LogViewerDialogクラスの後、TTSAppクラス内にshow_log_viewer関数を追加 ★

def main():
    app = QApplication(sys.argv)
    window = TTSApp()
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()