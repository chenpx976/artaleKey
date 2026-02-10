"""
AI Generate Dialog Module

Provides UI for AI-powered script generation.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit,
    QPushButton, QComboBox, QProgressBar, QGroupBox, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from artalekey.core.ai_script_generator import AIScriptGenerator, EXAMPLE_PROMPTS
from artalekey.core.logger import performance_logger


class AIGenerateDialog(QDialog):
    """Dialog for AI script generation"""

    # Signal emitted when script is generated successfully
    script_generated = pyqtSignal(str)  # Generated YAML content

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("AI 脚本生成器")
        self.setMinimumSize(600, 500)
        self.resize(700, 600)

        self.generator = AIScriptGenerator(self)
        self._init_ui()
        self._connect_signals()

    def _init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # Title
        title_label = QLabel("🤖 使用 AI 生成自动化脚本")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)

        # Description
        desc_label = QLabel(
            "用自然语言描述你想要的自动化操作，AI 将为你生成对应的 YAML 脚本。"
        )
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: gray;")
        layout.addWidget(desc_label)

        # Example prompts section
        example_group = QGroupBox("示例 Prompts（可选）")
        example_layout = QVBoxLayout(example_group)

        example_label = QLabel("选择一个示例或自己编写：")
        example_layout.addWidget(example_label)

        self.example_combo = QComboBox()
        self.example_combo.addItem("-- 选择示例 --", "")
        for example in EXAMPLE_PROMPTS:
            self.example_combo.addItem(example['name'], example['prompt'])
        self.example_combo.currentIndexChanged.connect(self._on_example_selected)
        example_layout.addWidget(self.example_combo)

        layout.addWidget(example_group)

        # Prompt input section
        prompt_group = QGroupBox("描述你的需求")
        prompt_layout = QVBoxLayout(prompt_group)

        prompt_label = QLabel("请详细描述你想要的自动化操作：")
        prompt_layout.addWidget(prompt_label)

        self.prompt_input = QTextEdit()
        self.prompt_input.setPlaceholderText(
            "例如：\n"
            "创建一个攻击脚本，按 A 键攻击，等待 800ms，按 S 键攻击，等待 800ms，循环执行\n\n"
            "或者：\n"
            "每 30 秒按一次 F1 和 F2 键来刷新 buff，持续 5 分钟"
        )
        self.prompt_input.setMinimumHeight(150)
        prompt_layout.addWidget(self.prompt_input)

        layout.addWidget(prompt_group)

        # Progress section
        self.progress_group = QGroupBox("生成进度")
        progress_layout = QVBoxLayout(self.progress_group)

        self.progress_label = QLabel("等待开始...")
        progress_layout.addWidget(self.progress_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        self.progress_bar.setVisible(False)
        progress_layout.addWidget(self.progress_bar)

        layout.addWidget(self.progress_group)
        self.progress_group.setVisible(False)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.generate_button = QPushButton("🚀 生成脚本")
        self.generate_button.setMinimumWidth(120)
        self.generate_button.setStyleSheet(
            "QPushButton { "
            "background-color: #4CAF50; "
            "color: white; "
            "font-weight: bold; "
            "padding: 8px; "
            "border-radius: 4px; "
            "} "
            "QPushButton:hover { "
            "background-color: #45a049; "
            "} "
            "QPushButton:disabled { "
            "background-color: #cccccc; "
            "}"
        )
        self.generate_button.clicked.connect(self._on_generate_clicked)
        button_layout.addWidget(self.generate_button)

        self.cancel_button = QPushButton("取消")
        self.cancel_button.setMinimumWidth(100)
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)

        layout.addLayout(button_layout)

        # Tips section
        tips_label = QLabel(
            "💡 提示：\n"
            "• 尽量详细描述操作步骤和时间间隔\n"
            "• 说明是循环执行、执行固定次数还是执行固定时长\n"
            "• 可以参考示例 Prompts 的描述方式"
        )
        tips_label.setWordWrap(True)
        tips_label.setStyleSheet(
            "background-color: #FFF9E6; "
            "padding: 10px; "
            "border-radius: 4px; "
            "border: 1px solid #FFE082;"
        )
        layout.addWidget(tips_label)

    def _connect_signals(self):
        """Connect signals"""
        self.generator.generation_started.connect(self._on_generation_started)
        self.generator.generation_completed.connect(self._on_generation_completed)
        self.generator.generation_failed.connect(self._on_generation_failed)
        self.generator.generation_progress.connect(self._on_generation_progress)

    def _on_example_selected(self, index):
        """Handle example selection"""
        if index > 0:
            prompt = self.example_combo.currentData()
            self.prompt_input.setPlainText(prompt)

    def _on_generate_clicked(self):
        """Handle generate button click"""
        prompt = self.prompt_input.toPlainText().strip()

        if not prompt:
            QMessageBox.warning(
                self,
                "提示",
                "请输入脚本描述"
            )
            return

        # Disable UI during generation
        self.generate_button.setEnabled(False)
        self.prompt_input.setEnabled(False)
        self.example_combo.setEnabled(False)
        self.progress_group.setVisible(True)
        self.progress_bar.setVisible(True)

        # Start generation
        self.generator.set_prompt(prompt)
        self.generator.start()

    def _on_generation_started(self):
        """Handle generation started"""
        self.progress_label.setText("正在生成脚本...")
        performance_logger.info("AI script generation started")

    def _on_generation_progress(self, message: str):
        """Handle generation progress"""
        self.progress_label.setText(message)

    def _on_generation_completed(self, yaml_content: str):
        """Handle generation completed"""
        self.progress_bar.setVisible(False)
        self.progress_label.setText("✅ 生成成功！")

        # Re-enable UI
        self.generate_button.setEnabled(True)
        self.prompt_input.setEnabled(True)
        self.example_combo.setEnabled(True)

        # Show success message
        QMessageBox.information(
            self,
            "成功",
            "脚本生成成功！已加载到编辑器中。"
        )

        # Emit signal with generated content
        self.script_generated.emit(yaml_content)

        # Close dialog
        self.accept()

        performance_logger.info("AI script generation completed successfully")

    def _on_generation_failed(self, error_message: str):
        """Handle generation failed"""
        self.progress_bar.setVisible(False)
        self.progress_label.setText("❌ 生成失败")

        # Re-enable UI
        self.generate_button.setEnabled(True)
        self.prompt_input.setEnabled(True)
        self.example_combo.setEnabled(True)

        # Show error message
        error_dialog = QMessageBox(self)
        error_dialog.setIcon(QMessageBox.Icon.Critical)
        error_dialog.setWindowTitle("生成失败")
        error_dialog.setText("AI 脚本生成失败")
        error_dialog.setDetailedText(error_message)
        error_dialog.exec()

        performance_logger.error(f"AI script generation failed: {error_message}")

    def closeEvent(self, event):
        """Handle dialog close"""
        # Stop generator if running
        if self.generator.isRunning():
            self.generator.terminate()
            self.generator.wait()
        event.accept()
