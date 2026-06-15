#!/bin/bash
set -e

# --- BUILD SCRIPT FOR OMNISCIENT AGENT (.app) ---

echo "🚀 Iniciando processo de empacotamento..."

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 1. Compila o SwiftAgent em Release
echo "📦 Compilando SwiftAgent (Release)..."
cd SwiftAgent
swift build -c release

SWIFT_BINARY_PATH=$(swift build -c release --show-bin-path)/Omniscient

if [ ! -f "$SWIFT_BINARY_PATH" ]; then
    echo "❌ Erro: Binário Swift não encontrado em $SWIFT_BINARY_PATH"
    exit 1
fi
echo "✅ Binário Swift localizado: $SWIFT_BINARY_PATH"
cd "$SCRIPT_DIR"

# 2. Prepara o Ambiente Python
echo "🐍 Garantindo dependências de build no venv..."
if [ ! -d "./venv" ]; then
    echo "   Criando venv..."
    python3 -m venv venv
fi
./venv/bin/pip install --quiet pyinstaller psutil PyQt6

# 3. Prepara o Ícone (.icns)
echo "🎨 Gerando ícone nativo (.icns)..."
ICON_PNG="src/ui/icon.png"
ICON_SET="icon.iconset"
mkdir -p "$ICON_SET"

sips -z 16 16     "$ICON_PNG" --out "$ICON_SET/icon_16x16.png" > /dev/null 2>&1
sips -z 32 32     "$ICON_PNG" --out "$ICON_SET/icon_16x16@2x.png" > /dev/null 2>&1
sips -z 32 32     "$ICON_PNG" --out "$ICON_SET/icon_32x32.png" > /dev/null 2>&1
sips -z 64 64     "$ICON_PNG" --out "$ICON_SET/icon_32x32@2x.png" > /dev/null 2>&1
sips -z 128 128   "$ICON_PNG" --out "$ICON_SET/icon_128x128.png" > /dev/null 2>&1
sips -z 256 256   "$ICON_PNG" --out "$ICON_SET/icon_128x128@2x.png" > /dev/null 2>&1
sips -z 256 256   "$ICON_PNG" --out "$ICON_SET/icon_256x256.png" > /dev/null 2>&1
sips -z 512 512   "$ICON_PNG" --out "$ICON_SET/icon_256x256@2x.png" > /dev/null 2>&1
sips -z 512 512   "$ICON_PNG" --out "$ICON_SET/icon_512x512.png" > /dev/null 2>&1
sips -z 1024 1024 "$ICON_PNG" --out "$ICON_SET/icon_512x512@2x.png" > /dev/null 2>&1

iconutil -c icns "$ICON_SET"
rm -rf "$ICON_SET"
echo "✅ Ícone gerado: icon.icns"

# 4. Empacota com PyInstaller
echo "🛠️ Criando App Bundle (.app)..."
MLX_LIB_PATH=$(find ./venv -name "lib" -path "*/mlx/lib" -type d | head -n 1)

if [ -z "$MLX_LIB_PATH" ]; then
    echo "⚠️ AVISO: MLX lib não encontrada,Continuando sem ela..."
    MLX_LIB_PATH="."
fi

./venv/bin/pyinstaller --windowed --noconsole --noconfirm \
    --name "OmniscientAgent" \
    --icon "icon.icns" \
    --add-data "$SWIFT_BINARY_PATH:." \
    --add-data "src/ui/icon.png:src/ui" \
    --add-data "$MLX_LIB_PATH:mlx/lib" \
    --collect-all mlx \
    --collect-all mlx_lm \
    --collect-all mlx_vlm \
    --collect-all mlx_whisper \
    --hidden-import "psutil" \
    --hidden-import "PyQt6.QtCore" \
    --hidden-import "PyQt6.QtWidgets" \
    --hidden-import "PyQt6.QtGui" \
    --hidden-import "AppKit" \
    --hidden-import "objc" \
    src/main.py

# 5. Configura o Bundle e Permissões
echo "⚓ Configurando Info.plist e Permissões..."
PLIST="dist/OmniscientAgent.app/Contents/Info.plist"

if [ -f "$PLIST" ]; then
    /usr/libexec/PlistBuddy -c "Add :LSUIElement string 1" "$PLIST" 2>/dev/null || /usr/libexec/PlistBuddy -c "Set :LSUIElement 1" "$PLIST"
    /usr/libexec/PlistBuddy -c "Add :NSRequiresAquaSystemAppearance bool false" "$PLIST" 2>/dev/null
    /usr/libexec/PlistBuddy -c "Add :NSMicrophoneUsageDescription string O Omniscient precisa do microfone para te ouvir." "$PLIST" 2>/dev/null
    /usr/libexec/PlistBuddy -c "Add :NSScreenCaptureUsageDescription string O Omniscient precisa ver a tela para te ajudar." "$PLIST" 2>/dev/null
    /usr/libexec/PlistBuddy -c "Add :NSAccessibilityUsageDescription string Necessário para atalhos globais." "$PLIST" 2>/dev/null
    
    echo "✅ Info.plist atualizado."
    
    echo "🔐 Assinando aplicativo com permissões de hardware..."
    codesign --force --options runtime --entitlements entitlements.plist --sign - "dist/OmniscientAgent.app"
    echo "✅ Assinatura concluída."
else
    echo "❌ Erro: Info.plist não encontrado em $PLIST."
    exit 1
fi

# 6. Gera o DMG
echo "📀 Gerando imagem de disco (.dmg)..."
DMG_NAME="OmniscientAgent_Setup.dmg"
rm -f "$DMG_NAME"
hdiutil create -volname "Omniscient Agent" -srcfolder "dist/OmniscientAgent.app" -ov -format UDZO "$DMG_NAME"

echo "✅ Build concluído com sucesso!"
echo "📂 O seu aplicativo está em: dist/OmniscientAgent.app"
echo "📀 O instalador está em: $DMG_NAME"

# Limpeza
rm -f icon.icns

