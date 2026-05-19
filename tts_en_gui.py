#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
BR-TTS Neural Network Edition - 英語対応版
多言語音声合成システム（日本語・英語）
"""

import sys
import os
import tempfile
import logging
from datetime import datetime
from pathlib import Path

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QTextEdit, QFileDialog, QMessageBox,
    QSlider, QCheckBox, QGroupBox, QComboBox, QDialog, QDialogButtonBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QIcon, QPixmap

logger = logging.getLogger(__name__)

# torch.load パッチ
import torch
original_load = torch.load
def patched_load(*args, **kwargs):
    kwargs['weights_only'] = False
    return original_load(*args, **kwargs)
torch.load = patched_load

from TTS.api import TTS
import subprocess

# ログ設定
LOG_DIR = Path('logs')
LOG_DIR.mkdir(exist_ok=True)
log_file = LOG_DIR / f"tts_en_gui_{datetime.now().strftime('%Y%m%d')}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


class SynthesisThread(QThread):
    """音声合成を別スレッドで実行"""
    finished = pyqtSignal(str)
    error = pyqtSignal(str)
    
    def __init__(self, tts_model, text, speaker_wav, language, output_file):
        super().__init__()
        self.tts_model = tts_model
        self.text = text
        self.speaker_wav = speaker_wav
        self.language = language
        self.output_file = output_file
    
    def run(self):
        try:
            self.tts_model.tts_to_file(
                text=self.text,
                file_path=self.output_file,
                speaker_wav=self.speaker_wav,
                language=self.language
            )
            self.finished.emit(self.output_file)
        except Exception as e:
            self.error.emit(str(e))


class TTSEnApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.tts_model = None
        self.current_audio_file = None
        self.speaker_wav_path = None
        self.synthesis_thread = None
        
        self.init_ui()
        self.load_model()
        
        logger.info("=" * 60)
        logger.info("BR-TTS EN (多言語版) 起動")
        logger.info(f"起動時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 60)
    
    def init_ui(self):
        """UI initialization"""
        self.setWindowTitle('BR SYSTEMS - TTS Multi-Language Speech Synthesis')
        self.setGeometry(100, 100, 900, 750)
        
        # Main widget
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        
        # Header with title and logo
        header_layout = QHBoxLayout()
        
        # Title
        title_label = QLabel('Neural Network Multi-Language Speech Synthesis')
        title_label.setFont(QFont('Arial', 16, QFont.Bold))
        title_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        
        # Logo (right side, 60% size)
        try:
            logo_label = QLabel()
            logo_pixmap = QPixmap('BRS_LOGO.png')
            if not logo_pixmap.isNull():
                # 60% size: 200 * 0.6 = 120, 60 * 0.6 = 36
                scaled_logo = logo_pixmap.scaled(120, 36, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                logo_label.setPixmap(scaled_logo)
            else:
                logo_label.setText('BR SYSTEMS')
                logo_label.setFont(QFont('Arial', 10, QFont.Bold))
        except:
            logo_label = QLabel('BR SYSTEMS')
            logo_label.setFont(QFont('Arial', 10, QFont.Bold))
        
        logo_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(logo_label)
        layout.addLayout(header_layout)
        
        # Language selection
        lang_group = QGroupBox('Language Selection')
        lang_layout = QHBoxLayout()
        
        lang_label = QLabel('Language:')
        self.language_combo = QComboBox()
        # Primary languages first (Japanese, English), then alphabetical
        self.language_combo.addItems([
            'Japanese',
            'English', 
            'Chinese',
            'French',
            'German',
            'Italian',
            'Korean',
            'Portuguese',
            'Russian',
            'Spanish'
        ])
        self.language_combo.setCurrentIndex(1)  # Default: English
        
        lang_layout.addWidget(lang_label)
        lang_layout.addWidget(self.language_combo)
        lang_layout.addStretch()
        lang_group.setLayout(lang_layout)
        layout.addWidget(lang_group)
        
        # Text input
        text_group = QGroupBox('Text to Synthesize')
        text_layout = QVBoxLayout()
        
        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText('Enter the text you want to synthesize here.')
        self.text_edit.setFont(QFont('Arial', 11))
        text_layout.addWidget(self.text_edit)
        
        # Auto conversion checkbox
        self.convert_numbers_cb = QCheckBox('Auto-convert numbers (Japanese only: 15時→十五時)')
        self.convert_numbers_cb.setChecked(True)
        text_layout.addWidget(self.convert_numbers_cb)
        
        text_group.setLayout(text_layout)
        layout.addWidget(text_group)
        
        # Voice sample selection
        sample_group = QGroupBox('Voice Sample')
        sample_layout = QHBoxLayout()
        
        self.sample_label = QLabel('Not selected')
        sample_btn = QPushButton('Select')
        sample_btn.clicked.connect(self.select_speaker)
        
        sample_layout.addWidget(QLabel('Voice Sample:'))
        sample_layout.addWidget(self.sample_label, 1)
        sample_layout.addWidget(sample_btn)
        
        sample_group.setLayout(sample_layout)
        layout.addWidget(sample_group)
        
        # Synthesize button
        synth_btn = QPushButton('Synthesize Speech')
        synth_btn.setFont(QFont('Arial', 12, QFont.Bold))
        synth_btn.setMinimumHeight(50)
        synth_btn.clicked.connect(self.synthesize)
        layout.addWidget(synth_btn)
        
        # Playback speed
        speed_group = QGroupBox('Playback Speed')
        speed_layout = QHBoxLayout()
        
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setMinimum(5)
        self.speed_slider.setMaximum(20)
        self.speed_slider.setValue(10)
        self.speed_slider.setTickPosition(QSlider.TicksBelow)
        self.speed_slider.setTickInterval(5)
        
        self.speed_label = QLabel('1.0x')
        self.speed_slider.valueChanged.connect(self.update_speed_label)
        
        speed_layout.addWidget(QLabel('Slow'))
        speed_layout.addWidget(self.speed_slider)
        speed_layout.addWidget(QLabel('Fast'))
        speed_layout.addWidget(self.speed_label)
        
        speed_group.setLayout(speed_layout)
        layout.addWidget(speed_group)
        
        # Play, Save, View Log, and Exit buttons
        control_layout = QHBoxLayout()
        
        play_btn = QPushButton('Play')
        play_btn.clicked.connect(self.play_audio)
        
        save_btn = QPushButton('Save As')
        save_btn.clicked.connect(self.save_audio)
        
        view_log_btn = QPushButton('View Log')
        view_log_btn.clicked.connect(self.view_log)
        
        control_layout.addWidget(play_btn)
        control_layout.addWidget(save_btn)
        control_layout.addWidget(view_log_btn)
        control_layout.addStretch()
        
        # Exit button
        exit_btn = QPushButton('Exit')
        exit_btn.clicked.connect(self.close)
        control_layout.addWidget(exit_btn)
        
        layout.addLayout(control_layout)
        
        # Status
        self.status_label = QLabel('Ready')
        layout.addWidget(self.status_label)
    
    def load_model(self):
        """Load TTS model"""
        try:
            self.status_label.setText('Loading model...')
            QApplication.processEvents()
            
            self.tts_model = TTS(model_name="tts_models/multilingual/multi-dataset/xtts_v2")
            
            # GPU check
            if torch.cuda.is_available():
                self.tts_model.to('cuda')
                device = 'cuda'
            else:
                device = 'cpu'
            
            self.status_label.setText(f'Ready (Device: {device})')
            logger.info(f"Model loaded: {device}")
            
        except Exception as e:
            error_msg = f"Model load error: {str(e)}"
            self.status_label.setText(error_msg)
            logger.error(error_msg)
            QMessageBox.critical(self, 'Error', error_msg)
    
    def get_language_code(self):
        """Get language code from selection"""
        lang_map = {
            'Japanese': 'ja',
            'English': 'en',
            'Chinese': 'zh-cn',
            'Spanish': 'es',
            'French': 'fr',
            'German': 'de',
            'Italian': 'it',
            'Portuguese': 'pt',
            'Korean': 'ko',
            'Russian': 'ru'
        }
        return lang_map.get(self.language_combo.currentText(), 'en')
    
    def select_speaker(self):
        """Select voice sample"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, 'Select Voice Sample',
            '', 'WAV Files (*.wav)'
        )
        
        if file_path:
            self.speaker_wav_path = file_path
            self.sample_label.setText(os.path.basename(file_path))
            logger.info(f"Voice sample selected: {file_path}")
    
    def convert_numbers_to_kanji(self, text):
        """数字を漢数字に変換（日本語のみ）"""
        # ... 既存のconvert_numbers_to_kanji関数をここにコピー ...
        # （前回作成した完全版）
        return text
    
    
    def synthesize(self):
        """Execute speech synthesis"""
        text = self.text_edit.toPlainText().strip()
        
        if not text:
            QMessageBox.warning(self, 'Warning', 'Please enter text.')
            return
        
        if not self.speaker_wav_path:
            QMessageBox.warning(self, 'Warning', 'Please select a voice sample.')
            return
        
        # Get language code
        language = self.get_language_code()
        
        # Auto-convert numbers (Japanese only)
        if language == 'ja' and self.convert_numbers_cb.isChecked():
            text = self.convert_numbers_to_kanji(text)
        
        # ★★★ Remove mid-sentence exclamation marks ★★★
        text = self.remove_mid_sentence_exclamation(text)
        
        logger.info(f"Synthesis started: language={language}, text='{text[:50]}...'")
        
        # Temporary file
        self.current_audio_file = tempfile.mktemp(suffix='.wav')
        
        # Synthesize in separate thread
        self.synthesis_thread = SynthesisThread(
            self.tts_model, text, self.speaker_wav_path, 
            language, self.current_audio_file
        )
        self.synthesis_thread.finished.connect(self.on_synthesis_finished)
        self.synthesis_thread.error.connect(self.on_synthesis_error)
        
        self.status_label.setText('Synthesizing...')
        self.synthesis_thread.start()

# ===============================================
# 関数1: convert_numbers_to_kanji
# ===============================================

    def convert_numbers_to_kanji(self, text):
        """数字、英語略語、カタカナを変換（日本語のみ）"""
        
        def num_to_kanji(num):
            """0-9999の数値を漢数字に変換"""
            if num == 0:
                return '零'
            
            kanji_map = ['', '一', '二', '三', '四', '五', '六', '七', '八', '九']
            
            if num < 10:
                return kanji_map[num]
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
            elif num < 1000:
                hundreds = num // 100
                remainder = num % 100
                result = kanji_map[hundreds] + '百'
                if remainder > 0:
                    result += num_to_kanji(remainder)
                return result
            else:
                thousands = num // 1000
                remainder = num % 1000
                if thousands == 1:
                    result = '千'
                else:
                    result = kanji_map[thousands] + '千'
                if remainder > 0:
                    result += num_to_kanji(remainder)
                return result
        
        import re
        single_digit_map = {
            '0': 'ぜろ', '1': 'いち', '2': 'に', '3': 'さん', '4': 'よん',
            '5': 'ご', '6': 'ろく', '7': 'なな', '8': 'はち', '9': 'きゅう',
        }
        
        for digit, hira in single_digit_map.items():
            text = re.sub(rf'(^|[、。\s]){digit}([、。\s]|$)', rf'\1{hira}\2', text)
        
        katakana_to_hiragana = {
            'マイク': 'まいく', 'テスト': 'てすと', 'ボリューム': 'ぼりゅーむ',
            'パソコン': 'ぱそこん', 'スマホ': 'すまほ', 'データ': 'でーた',
        }
        
        for kata, hira in katakana_to_hiragana.items():
            text = text.replace(kata, hira)
        
        abbreviations = {
            'AI': 'エーアイ', 'IT': 'アイティー', 'PC': 'ピーシー',
            'CPU': 'シーピーユー', 'GPU': 'ジーピーユー',
        }
        
        for abbr, reading in abbreviations.items():
            text = text.replace(abbr, reading)
        
        for hour in range(24, -1, -1):
            text = text.replace(f'{hour}時', num_to_kanji(hour) + '時')
        
        for minute in range(59, -1, -1):
            text = text.replace(f'{minute}分', num_to_kanji(minute) + '分')
        
        for age in range(120, -1, -1):
            if 70 <= age <= 79:
                ones = age % 10
                ones_hira = ['', 'いち', 'に', 'さん', 'よん', 'ご', 'ろく', 'なな', 'はち', 'きゅう']
                if ones == 0:
                    converted = 'ななじゅうさい'
                else:
                    converted = f'ななじゅう{ones_hira[ones]}さい'
                text = text.replace(f'{age}歳', converted)
            else:
                text = text.replace(f'{age}歳', num_to_kanji(age) + '歳')
        
        for decade in [10, 20, 30, 40, 50, 60, 70, 80, 90]:
            text = text.replace(f'{decade}代', num_to_kanji(decade) + '代')
        
        return text


# ===============================================
# 関数2: remove_mid_sentence_exclamation
# ===============================================

    def remove_mid_sentence_exclamation(self, text):
        """Remove mid-sentence exclamation marks (keep end-of-sentence)"""
        import re
        
        # 文中の「！」を「。」に置き換え
        text = re.sub(r'！(?=.)', '。', text)
        
        # 文中の「？」を「。」に置き換え
        text = re.sub(r'？(?=.)', '。', text)
        
        # 文中の「!」（半角）を処理
        text = re.sub(r'!(?=.)', '. ', text)  # 英語用
        
        # 文中の「?」（半角）を処理
        text = re.sub(r'\?(?=.)', '. ', text)
        
        return text
    
    def on_synthesis_finished(self, file_path):

        """Synthesis completed (trimming disabled)"""
        # Trimming disabled
        self.current_audio_file = file_path
        self.status_label.setText('Synthesis completed')
        logger.info(f"Synthesis completed: {self.current_audio_file}")
        QMessageBox.information(self, 'Completed', 'Synthesis completed.')
    
    def trim_silence(self, audio_file, threshold_db=-40):
        """音声の末尾無音を削除"""
        try:
            from pydub import AudioSegment
            from pydub.silence import detect_silence
            
            # 音声読み込み
            audio = AudioSegment.from_wav(audio_file)
            original_length = len(audio)
            
            # 無音検出（末尾から）
            silence_ranges = detect_silence(
                audio,
                min_silence_len=300,  # 300ms以上の無音
                silence_thresh=threshold_db
            )
            
            if silence_ranges:
                # 最後の無音区間の開始位置
                last_silence_start = silence_ranges[-1][0]
                
                # 無音が音声の後半（70%以降）にある場合のみトリミング
                if last_silence_start > original_length * 0.7:
                    # 無音開始位置でカット
                    trimmed = audio[:last_silence_start]
                    
                    # 末尾に短い無音を追加（自然な終わり方）
                    silence = AudioSegment.silent(duration=200)  # 200ms
                    trimmed = trimmed + silence
                    
                    # 一時ファイルに保存
                    import tempfile
                    trimmed_file = tempfile.mktemp(suffix='_trimmed.wav')
                    trimmed.export(trimmed_file, format='wav')
                    
                    logger.info(f"末尾トリミング: {original_length}ms → {len(trimmed)}ms")
                    return trimmed_file
            
            logger.info("トリミング不要（無音検出なし）")
            return None
            
        except ImportError:
            logger.warning("pydubがインストールされていません。トリミングをスキップします。")
            return None
        except Exception as e:
            logger.error(f"トリミングエラー: {e}")
            return None
    
    def on_synthesis_error(self, error_msg):
        """Synthesis error"""
        self.status_label.setText(f'Error: {error_msg}')
        logger.error(f"Synthesis error: {error_msg}")
        QMessageBox.critical(self, 'Error', f'Synthesis error:\n{error_msg}')
    
    def update_speed_label(self):
        """再生速度ラベル更新"""
        speed = self.speed_slider.value() / 10.0
        self.speed_label.setText(f'{speed:.1f}x')
    
    def play_audio(self):
        """Play audio"""
        if not self.current_audio_file or not os.path.exists(self.current_audio_file):
            QMessageBox.warning(self, 'Warning', 'No audio to play.')
            return
        
        try:
            speed = self.speed_slider.value() / 10.0
            subprocess.Popen(['ffplay', '-nodisp', '-autoexit', 
                            '-af', f'atempo={speed}', 
                            self.current_audio_file],
                           stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL)
            logger.info(f"Playing audio: {self.current_audio_file} (speed: {speed}x)")
        except Exception as e:
            QMessageBox.warning(self, 'Warning', f'Playback error:\n{str(e)}')
    
    def save_audio(self):
        """Save audio"""
        if not self.current_audio_file or not os.path.exists(self.current_audio_file):
            QMessageBox.warning(self, 'Warning', 'No audio to save.')
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, 'Save Audio',
            'output.wav', 'WAV Files (*.wav)'
        )
        
        if file_path:
            import shutil
            shutil.copy(self.current_audio_file, file_path)
            logger.info(f"Audio saved: {file_path}")
            QMessageBox.information(self, 'Completed', f'Audio saved:\n{file_path}')
    
    def view_log(self):
        """View log file in dialog"""
        try:
            # Log file path
            log_file = LOG_DIR / f"tts_en_gui_{datetime.now().strftime('%Y%m%d')}.log"
            
            if not log_file.exists():
                QMessageBox.information(self, 'Log', 'No log file found for today.')
                return
            
            # Read log file
            with open(log_file, 'r', encoding='utf-8') as f:
                log_content = f.read()
            
            # Create dialog
            from PyQt5.QtWidgets import QDialog, QTextEdit, QVBoxLayout, QDialogButtonBox
            
            dialog = QDialog(self)
            dialog.setWindowTitle('Log Viewer')
            dialog.setGeometry(200, 200, 800, 600)
            
            layout = QVBoxLayout(dialog)
            
            # Log text area
            log_text = QTextEdit()
            log_text.setReadOnly(True)
            log_text.setPlainText(log_content)
            log_text.setFont(QFont('Courier New', 9))
            layout.addWidget(log_text)
            
            # Buttons
            button_box = QDialogButtonBox(QDialogButtonBox.Close)
            button_box.rejected.connect(dialog.close)
            
            # Refresh button
            refresh_btn = button_box.addButton('Refresh', QDialogButtonBox.ActionRole)
            refresh_btn.clicked.connect(lambda: self.refresh_log(log_text, log_file))
            
            # Clear button
            clear_btn = button_box.addButton('Clear Log', QDialogButtonBox.ActionRole)
            clear_btn.clicked.connect(lambda: self.clear_log(log_file, log_text))
            
            layout.addWidget(button_box)
            
            dialog.exec_()
            
        except Exception as e:
            QMessageBox.warning(self, 'Error', f'Failed to open log:\n{str(e)}')
    
    def refresh_log(self, text_widget, log_file):
        """Refresh log content"""
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                log_content = f.read()
            text_widget.setPlainText(log_content)
            # Scroll to bottom
            text_widget.verticalScrollBar().setValue(
                text_widget.verticalScrollBar().maximum()
            )
        except Exception as e:
            QMessageBox.warning(self, 'Error', f'Failed to refresh log:\n{str(e)}')
    
    def clear_log(self, log_file, text_widget):
        """Clear log file"""
        reply = QMessageBox.question(
            self, 'Confirm',
            'Are you sure you want to clear the log?',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                with open(log_file, 'w', encoding='utf-8') as f:
                    f.write('')
                text_widget.setPlainText('')
                logger.info("Log cleared by user")
                QMessageBox.information(self, 'Success', 'Log cleared.')
            except Exception as e:
                QMessageBox.warning(self, 'Error', f'Failed to clear log:\n{str(e)}')


def main():
    app = QApplication(sys.argv)
    window = TTSEnApp()
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
