#!/bin/bash
cd /Users/pastorello/Documents/pessoal/agent

if [ ! -f SwiftAgent/.build/arm64-apple-macosx/release/Omniscient ]; then
    echo "Compilando SwiftAgent pela primeira vez..."
    cd SwiftAgent && swift build -c release 2>&1 && cd ..
fi

export WESPEAKER_HOME=/Users/pastorello/Documents/pessoal/agent/pretrained_models/wespeaker
exec ./venv/bin/python src/main.py
