
# 创建DMG安装包

如果您想创建DMG安装包，可以：

1. 安装create-dmg工具：
```bash
brew install create-dmg
```

2. 创建DMG：
```bash
create-dmg \
  --volname "ArtaleKey" \
  --window-pos 200 120 \
  --window-size 800 400 \
  --icon-size 100 \
  --icon "ArtaleKey.app" 200 190 \
  --hide-extension "ArtaleKey.app" \
  --app-drop-link 600 185 \
  "ArtaleKey-1.0.0.dmg" \
  "dist/"
```

或者手动创建：
1. 打开"磁盘工具"
2. 文件 -> 新建映像 -> 空白映像
3. 将ArtaleKey.app拖入
4. 创建应用程序链接
5. 保存为DMG文件
