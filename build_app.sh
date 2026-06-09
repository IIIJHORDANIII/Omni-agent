#!/bin/bash

# --- BUILD SCRIPT FOR OMNISCIENT AGENT (.app) ---

echo "🚀 Iniciando processo de empacotamento..."

# 1. Compila o SwiftAgent em Release
echo "📦 Compilando SwiftAgent (Release)..."
cd SwiftAgent
swift build -c release

# Busca o binário real (o path pode variar dependendo da versão do Swift/macOS)
SWIFT_BINARY_PATH=$(swift build -c release --show-bin-path)/Omniscient

if [ ! -f "$SWIFT_BINARY_PATH" ]; then
    echo "❌ Erro: Binário Swift não encontrado em $SWIFT_BINARY_PATH"
    exit 1
fi
echo "✅ Binário Swift localizado: $SWIFT_BINARY_PATH"
cd ..

# 2. Prepara o Ambiente Python
echo "🐍 Garantindo dependências de build no venv..."
./venv/bin/pip install pyinstaller psutil PyQt6

# 3. Empacota com PyInstaller
echo "🛠️ Criando App Bundle (.app)..."
# --windowed: Cria um bundle .app correto no macOS
# --onedir: Modo pasta (mais estável para macOS e MLX)
# --collect-all: Garante que todas as dependências do MLX e parceiros sejam incluídas

MLX_LIB_PATH=$(find ./venv -name "lib" -path "*/mlx/lib" -type d | head -n 1)

./venv/bin/pyinstaller --windowed --onedir --noconfirm \
    --name "OmniscientAgent" \
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

# Injeta a flag LSUIElement no Info.plist para esconder o ícone do Dock
echo "⚓ Configurando Info.plist..."
PLIST="dist/OmniscientAgent.app/Contents/Info.plist"
if [ -f "$PLIST" ]; then
    /usr/libexec/PlistBuddy -c "Add :LSUIElement string 1" "$PLIST"
    
    # Suporte a Dark Mode e Transparência nativa
    /usr/libexec/PlistBuddy -c "Add :NSRequiresAquaSystemAppearance bool false" "$PLIST"
    
    # Adiciona permissões essenciais do macOS para evitar crash
    /usr/libexec/PlistBuddy -c "Add :NSMicrophoneUsageDescription string O Omniscient Agent precisa do microfone para comandos de voz." "$PLIST"
    /usr/libexec/PlistBuddy -c "Add :NSScreenCaptureUsageDescription string O Omniscient Agent precisa da tela para analisar o contexto do seu trabalho." "$PLIST"
    /usr/libexec/PlistBuddy -c "Add :NSAccessibilityUsageDescription string O Omniscient Agent precisa de acessibilidade para registrar atalhos globais." "$PLIST"
    /usr/libexec/PlistBuddy -c "Add :NSAppleEventsUsageDescription string O Omniscient Agent precisa controlar outros apps para realizar automações." "$PLIST"
fi

echo "✅ Build concluído com sucesso!"
echo "📂 O seu aplicativo está em: dist/OmniscientAgent.app"
echo "💡 Você pode mover para /Applications para facilitar o acesso."
