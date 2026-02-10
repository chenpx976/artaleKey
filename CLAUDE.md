# ArtaleKey - Claude Code Context

## Project Overview

**ArtaleKey** is a macOS game hotkey management assistant tool specifically optimized for MapleStory Worlds and similar games. It provides automated keyboard input, game data tracking, and intelligent window filtering to enhance the gaming experience.

**Version**: 0.1.3
**Language**: Python 3.8+
**GUI Framework**: PyQt6
**Platform**: macOS (primary), with cross-platform support for Windows and Linux

## Quick Start

```bash
# Recommended startup method
uv run python -m artalekey

# Or with standard Python
python -m artalekey
```

## Core Features

### 1. Quick Up Feature
- **Purpose**: Automated rapid upward movement in games
- **Mechanism**: Detects W + Up arrow combination, then automatically alternates left/right arrow keys
- **Configuration**: Adjustable hold time and key press intervals
- **Implementation**: [hotkey_manager.py](artalekey/core/hotkey_manager.py)

### 2. Window Detection & Filtering
- **Purpose**: Restricts hotkey functionality to target applications only
- **Platform Support**: macOS (Quartz), Windows (Win32), Linux (Xlib)
- **Implementation**: [window_detector.py](artalekey/core/window_detector.py)

### 3. Game Data Tracking
- **Captures**: Character level, experience, money, HP/MP, potion counts
- **Storage**: SQLite database with automatic cleanup of old records
- **Visualization**: Real-time charts and statistics
- **Implementation**: [database.py](artalekey/core/database.py)

### 4. LLM Integration
- **Provider**: OpenRouter API
- **Purpose**: AI-powered screenshot analysis for game data extraction
- **Regions**: Map, character, stats, potions, money
- **Implementation**: [llm_processor.py](artalekey/core/llm_processor.py)

### 5. OCR Recognition (Currently Disabled)
- **Engine**: EasyOCR
- **Purpose**: Text extraction from game screenshots
- **Implementation**: [enhanced_ocr.py](artalekey/core/enhanced_ocr.py)

## Project Structure

```
artalekey/
├── artalekey/                    # Main package
│   ├── __main__.py              # Application entry point
│   ├── core/                    # Core functionality modules
│   │   ├── config.py            # Configuration management (QSettings + JSON)
│   │   ├── database.py          # SQLite game data persistence
│   │   ├── hotkey_manager.py   # Keyboard event handling & simulation
│   │   ├── window_detector.py  # Cross-platform window detection
│   │   ├── llm_processor.py    # LLM image processing (OpenRouter)
│   │   ├── enhanced_ocr.py     # OCR functionality (EasyOCR)
│   │   ├── permissions.py      # macOS permission management
│   │   ├── logger.py           # Performance monitoring & logging
│   │   └── window_status.py    # Window status tracking
│   └── ui/                      # User interface components
│       ├── tabbed_main_window.py  # Main application window
│       ├── tabs/                  # Tab system
│       │   ├── base_tab.py       # Base class for all tabs
│       │   ├── quick_up_tab.py   # Quick-up feature controls
│       │   ├── settings_tab.py   # Settings & configuration
│       │   ├── ocr_tab.py        # OCR interface (disabled)
│       │   └── logs_tab.py       # Logging display (disabled)
│       ├── components.py          # Reusable UI components
│       ├── multi_status_bar.py    # Multi-line status widget
│       ├── window_status_widget.py # Window status display
│       ├── simple_target_selector.py # App selection UI
│       ├── qt_chart_widget.py     # Chart visualization
│       └── simple_styles.py       # Cross-platform styling
├── docs/                        # Documentation
├── tests/                       # Test scripts
├── scripts/                     # Utility scripts
├── pyproject.toml              # Project metadata & dependencies
└── README.md                   # User documentation
```

## Architecture Overview

### Component Interaction

```
┌─────────────────────────────────────────────────────────────┐
│                    TabbedMainWindow                         │
│  (Main application window - PyQt6 QMainWindow)              │
└────────────────────┬────────────────────────────────────────┘
                     │
        ┌────────────┼────────────┐
        │            │            │
        ▼            ▼            ▼
    ┌────────┐  ┌──────────┐  ┌──────────────┐
    │TabMgr  │  │HotkeyLis │  │KeySimulator  │
    │        │  │tener     │  │              │
    └────────┘  └──────────┘  └──────────────┘
        │            │              │
        ▼            ▼              ▼
    ┌─────────────────────────────────────┐
    │  Tab System (Quick Up, Settings)    │
    │  - QuickUpTab                       │
    │  - SettingsTab                      │
    └─────────────────────────────────────┘
        │
        ├─► HotkeyCard (Configuration UI)
        ├─► MultiLineStatusWidget (Status Display)
        └─► Components (UI Elements)

┌─────────────────────────────────────────────────────────────┐
│                    Core Modules                             │
├─────────────────────────────────────────────────────────────┤
│ ConfigManager ◄──► QSettings (Persistent Storage)           │
│ HotkeyListener ◄──► WindowDetector (Active Window Check)    │
│ KeySimulator ◄──► KeyboardManager (Keyboard Control)        │
│ GameDataDatabase ◄──► SQLite (Game Data Storage)            │
│ LLMProcessor ◄──► OpenRouter API (AI Processing)            │
│ EnhancedOCR ◄──► EasyOCR (Text Recognition)                 │
│ PermissionManager ◄──► macOS APIs (System Permissions)      │
│ PerformanceLogger ◄──► File/Console (Logging)               │
└─────────────────────────────────────────────────────────────┘
```

### Key Design Patterns

- **Singleton Pattern**: `KeyboardManager`, `ConfigManager`, `GameDataDatabase`
- **Factory Pattern**: `TabFactory` for creating tab instances
- **Observer Pattern**: PyQt signals for component communication
- **Thread-based Architecture**: `HotkeyListener` and `KeySimulator` run in separate QThreads
- **Decorator Pattern**: Performance logging with `@measure_time` decorator
- **Strategy Pattern**: Platform-specific window detection implementations

## Data Flow

### Hotkey Activation Flow
1. User presses W + Up arrow combination
2. `HotkeyListener` detects the key combination
3. Long-press timer triggers after configured hold time
4. `KeySimulator` starts automated key simulation (left/right arrow alternation)
5. User releases keys → `KeySimulator` stops and releases all keys

### Game Data Capture Flow
1. Screenshot triggered (via OCR hotkey or manual)
2. `EnhancedOCR` or `LLMProcessor` extracts game data
3. Data parsed into structured format (character info, stats, etc.)
4. `GameDataDatabase` stores data in SQLite
5. `MultiLineStatusWidget` displays latest data summary

### Configuration Flow
1. User modifies settings in UI tabs
2. Changes emitted via PyQt signals
3. `ConfigManager` persists to QSettings
4. Core components (HotkeyListener, KeySimulator) update their behavior
5. Changes reflected in UI on next load

## Technology Stack

| Category | Technologies |
|----------|-------------|
| **GUI Framework** | PyQt6 |
| **Database** | SQLite3 |
| **Keyboard Control** | pynput |
| **OCR** | EasyOCR |
| **LLM Integration** | OpenRouter API (via requests) |
| **Image Processing** | Pillow, OpenCV, numpy |
| **System Monitoring** | psutil |
| **macOS Integration** | PyObjC (Cocoa, Quartz, ApplicationServices) |
| **Configuration** | QSettings, JSON, YAML, TOML |
| **Packaging** | PyInstaller |
| **Build System** | Hatchling |

## Dependencies

### Core Dependencies
```toml
PyQt6>=6.6.1                    # GUI framework
pynput>=1.7.6                   # Keyboard control
psutil>=5.9.0                   # System monitoring
pillow>=10.0.0                  # Image processing
opencv-python>=4.8.0            # Computer vision
requests>=2.28.0                # HTTP client
pyyaml>=6.0.0                   # YAML parsing
toml>=0.10.2                    # TOML parsing
```

### Platform-Specific Dependencies
```toml
pyobjc-framework-cocoa>=10.3.2           # macOS (Cocoa)
pyobjc-framework-quartz>=10.3.2          # macOS (Quartz)
pyobjc-framework-applicationservices>=10.3.2  # macOS (AppServices)
pywin32>=306                             # Windows
python-xlib>=0.33                        # Linux
```

### Optional Dependencies
```toml
easyocr>=1.7.0                  # OCR (currently disabled)
langchain>=0.2.0                # LLM framework
pandas>=1.5.0                   # Data analysis
openpyxl>=3.1.0                 # Excel export
pyqt6-charts>=6.6.0             # Chart visualization
```

## Configuration Management

### Configuration File Location
- **macOS**: `~/Library/Preferences/com.artalekey.plist`
- **Windows**: Registry or INI file
- **Linux**: `~/.config/artalekey/artalekey.conf`

### Configuration Structure
```python
{
    "hotkeys": {
        "quick_up": {
            "enabled": bool,
            "hold_time": float,      # seconds
            "interval": float,       # seconds
            "keys": ["w", "up"]
        }
    },
    "window_filter": {
        "enabled": bool,
        "target_apps": [str]
    },
    "llm": {
        "api_key": str,
        "model": str,
        "base_url": str
    },
    "ui": {
        "window_geometry": dict,
        "theme": str
    },
    "performance": {
        "logging_enabled": bool,
        "log_level": str
    }
}
```

## Database Schema

### Game Data Table
```sql
CREATE TABLE game_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    character_name TEXT,
    level INTEGER,
    experience INTEGER,
    money INTEGER,
    hp INTEGER,
    mp INTEGER,
    hp_potion_count INTEGER,
    mp_potion_count INTEGER,
    map_name TEXT,
    screenshot_path TEXT
);
```

## macOS Permissions

### Required Permissions
1. **Accessibility**: Required for global hotkey detection and keyboard simulation
2. **Input Monitoring**: Required for monitoring keyboard events
3. **Screen Recording**: Required for screenshot capture (OCR/LLM features)

### Permission Management
- Implemented in [permissions.py](artalekey/core/permissions.py)
- Automatic permission checking on startup
- User-friendly prompts to guide permission granting
- System Preferences deep-linking for easy access

## Building & Packaging

### Development Build
```bash
# Install dependencies
uv pip install -r requirements.txt

# Run in development mode
uv run python -m artalekey
```

### macOS App Bundle
```bash
# Install build dependencies
pip install -r requirements-build.txt

# Build app bundle
python build_macos_app.py

# Output: dist/ArtaleKey.app
```

### DMG Installer
See [docs/macOS打包指南.md](docs/macOS打包指南.md) for detailed instructions on:
- Creating DMG installers
- Code signing
- Notarization
- Distribution

## Testing

### Test Scripts
```bash
# Performance testing
python tests/test_performance.py

# Window detection testing
python tests/test_window_detection.py
```

## Common Development Tasks

### Adding a New Tab
1. Create new tab class in `artalekey/ui/tabs/` inheriting from `BaseTab`
2. Implement required methods: `setup_ui()`, `load_config()`, `save_config()`
3. Register tab in `TabFactory` in `artalekey/ui/tabs/__init__.py`
4. Add tab to `TabbedMainWindow` in [tabbed_main_window.py](artalekey/ui/tabbed_main_window.py)

### Adding a New Hotkey
1. Define hotkey configuration in [config.py](artalekey/core/config.py)
2. Add hotkey detection logic in [hotkey_manager.py](artalekey/core/hotkey_manager.py)
3. Create UI controls in appropriate tab
4. Connect signals between UI and hotkey manager

### Modifying Game Data Schema
1. Update database schema in [database.py](artalekey/core/database.py)
2. Add migration logic for existing databases
3. Update data extraction logic in [llm_processor.py](artalekey/core/llm_processor.py) or [enhanced_ocr.py](artalekey/core/enhanced_ocr.py)
4. Update UI display components

## Performance Considerations

### Threading Model
- **Main Thread**: PyQt6 event loop, UI rendering
- **HotkeyListener Thread**: Global keyboard event monitoring
- **KeySimulator Thread**: Automated key press simulation
- **LLM Processing**: Thread pool for concurrent API requests

### Optimization Strategies
- Window information caching to reduce system calls
- Lazy loading of heavy dependencies (EasyOCR, LangChain)
- Database connection pooling
- Performance logging with `@measure_time` decorator
- Automatic cleanup of old database records

## Security Considerations

### API Key Management
- API keys stored in QSettings (encrypted on macOS)
- Never logged or exposed in UI
- Configurable via settings tab

### System Permissions
- Minimal permission requests (only what's needed)
- Clear user communication about permission purposes
- Graceful degradation when permissions denied

### Input Simulation
- Restricted to target applications only (when window filtering enabled)
- User-controlled activation/deactivation
- No background operation without user consent

## Known Issues & Limitations

### Current Limitations
1. **OCR Feature**: Currently disabled in recent versions (v0.1.2+)
2. **Logs Tab**: Currently disabled in recent versions
3. **Platform Support**: Primary focus on macOS, limited testing on Windows/Linux
4. **Game Compatibility**: Optimized for MapleStory Worlds, may need adjustments for other games

### Troubleshooting
- See [docs/permissions_guide.md](docs/permissions_guide.md) for permission issues
- See [docs/MACOS_USAGE_GUIDE.md](docs/MACOS_USAGE_GUIDE.md) for macOS-specific issues
- Check logs in `~/Library/Logs/ArtaleKey/` (macOS)

## Contributing Guidelines

### Code Style
- Follow PEP 8 guidelines
- Use Ruff for linting (configured in pyproject.toml)
- Line length: 100 characters
- Type hints encouraged but not required

### Commit Message Format
```
<type>: <subject>

<body>

<footer>
```

Types: feat, fix, docs, style, refactor, test, chore

### Pull Request Process
1. Fork the repository
2. Create a feature branch
3. Make changes with clear commit messages
4. Test thoroughly on target platform(s)
5. Submit PR with detailed description

## Documentation

### Available Documentation
- [README.md](README.md) - User guide and quick start
- [docs/启动说明.md](docs/启动说明.md) - Startup instructions (Chinese)
- [docs/macOS打包指南.md](docs/macOS打包指南.md) - macOS packaging guide (Chinese)
- [docs/DMG_GUIDE.md](docs/DMG_GUIDE.md) - DMG creation guide
- [docs/MACOS_USAGE_GUIDE.md](docs/MACOS_USAGE_GUIDE.md) - macOS usage guide
- [docs/permissions_guide.md](docs/permissions_guide.md) - Permissions guide
- [docs/开发文档.md](docs/开发文档.md) - Development documentation (Chinese)
- [docs/API文档.md](docs/API文档.md) - API documentation (Chinese)

## License

MIT License

## Contact & Support

- **Repository**: https://github.com/chenpx976/artaleKey
- **Issues**: https://github.com/chenpx976/artaleKey/issues

---

**Last Updated**: 2026-02-10
**Document Version**: 1.0
**Project Version**: 0.1.3
