
# 创建DMG安装包

## 方法一：使用 create-dmg（推荐）

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

## 方法二：手动创建

1. 打开"磁盘工具"
2. 文件 → 新建映像 → 空白映像
3. 将ArtaleKey.app拖入
4. 创建应用程序链接
5. 保存为DMG文件

## 分发注意事项

- 如果应用已签名和公证，用户可以直接运行
- 未签名的应用需要用户手动允许运行
- 建议在DMG中包含使用说明
