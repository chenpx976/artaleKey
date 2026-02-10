"""
YAML Syntax Highlighter Module

Provides syntax highlighting for YAML editor.
"""

from PyQt6.QtCore import QRegularExpression
from PyQt6.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor, QFont


class YAMLHighlighter(QSyntaxHighlighter):
    """Syntax highlighter for YAML"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._highlighting_rules = []

        # Define formats
        # Keys (e.g., "name:", "execution:")
        key_format = QTextCharFormat()
        key_format.setForeground(QColor("#0066CC"))  # Blue
        key_format.setFontWeight(QFont.Weight.Bold)
        self._highlighting_rules.append((
            QRegularExpression(r"^\s*[\w_]+(?=:)"),
            key_format
        ))

        # String values (quoted)
        string_format = QTextCharFormat()
        string_format.setForeground(QColor("#008000"))  # Green
        self._highlighting_rules.append((
            QRegularExpression(r'"[^"\\]*(\\.[^"\\]*)*"'),
            string_format
        ))
        self._highlighting_rules.append((
            QRegularExpression(r"'[^'\\]*(\\.[^'\\]*)*'"),
            string_format
        ))

        # Numbers
        number_format = QTextCharFormat()
        number_format.setForeground(QColor("#FF6600"))  # Orange
        self._highlighting_rules.append((
            QRegularExpression(r"\b\d+\.?\d*\b"),
            number_format
        ))

        # Booleans
        boolean_format = QTextCharFormat()
        boolean_format.setForeground(QColor("#9900CC"))  # Purple
        boolean_format.setFontWeight(QFont.Weight.Bold)
        self._highlighting_rules.append((
            QRegularExpression(r"\b(true|false|yes|no|on|off)\b"),
            boolean_format
        ))

        # Comments
        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor("#808080"))  # Gray
        comment_format.setFontItalic(True)
        self._highlighting_rules.append((
            QRegularExpression(r"#[^\n]*"),
            comment_format
        ))

        # List markers
        list_format = QTextCharFormat()
        list_format.setForeground(QColor("#CC0000"))  # Red
        list_format.setFontWeight(QFont.Weight.Bold)
        self._highlighting_rules.append((
            QRegularExpression(r"^\s*-\s"),
            list_format
        ))

        # Special YAML keywords
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor("#9900CC"))  # Purple
        keyword_format.setFontWeight(QFont.Weight.Bold)
        self._highlighting_rules.append((
            QRegularExpression(r"\b(null|~)\b"),
            keyword_format
        ))

    def highlightBlock(self, text):
        """
        Apply syntax highlighting to a block of text

        Args:
            text: Text block to highlight
        """
        # Apply all highlighting rules
        for pattern, format_obj in self._highlighting_rules:
            match_iterator = pattern.globalMatch(text)
            while match_iterator.hasNext():
                match = match_iterator.next()
                self.setFormat(
                    match.capturedStart(),
                    match.capturedLength(),
                    format_obj
                )
