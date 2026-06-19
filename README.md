# Anders Agent 🤖

> **O seu assistente autônomo e multimodal para macOS, focado em produtividade extrema e execução proativa.**

Anders é um agente virtual alimentado por Inteligência Artificial projetado para rodar em background no macOS. Mais do que um chatbot, ele atua como um sistema integrado ao seu fluxo de trabalho, sendo capaz de rodar comandos no terminal, analisar o que acontece na sua tela, ouvir comandos de voz nativamente, classificar arquivos e te responder de forma minimalista.

## 🚀 Principais Recursos

*   **Arquitetura ReAct (Reasoning + Acting):** O núcleo da IA permite que o Anders decomponha problemas, planeje e execute ações (como rodar scripts) em um terminal persistente interativo (Persistent Shell).
*   **Spotlight HUD:** Uma interface ultraleve, ativada pelo atalho global (`Cmd + Cmd`), que flutua no meio da tela no padrão "glassmorphism", permitindo interações diretas e focadas sem interromper seu fluxo de visão.
*   **Integração de Voz Real-time:** Escuta ativa otimizada através da nuvem (Deepgram), detectando comandos naturais instantaneamente. Responde com áudio cristalino mantendo o contexto.
*   **Memória Semântica (ChromaDB):** O Anders possui um vetor de memória que cataloga projetos, código e informações para resgatar dados anteriores com extrema precisão sem poluir a "janela de contexto".
*   **Vision Service (Qwen2-VL):** Habilidade de compreender elementos visuais da tela para fornecer contexto exato durante pair programming ou depuração de código.
*   **Auto-Organizer & Crawler:** Varreduras invisíveis de arquivos em diretórios como `Downloads` ou `Desktop`, mantendo sua máquina organizada e seu código mapeado e atualizado no banco vetorial.
*   **App Invisível (Background Mode):** Construído sobre `LSUIElement` do macOS. O Anders não gera ícone no Dock nem polui seu `Cmd + Tab`. Ele vive silenciosamente nas sombras até ser chamado.

## 🛠️ Tecnologias Utilizadas

*   **Linguagem & Interface:** Python 3.9+ / PyQt6
*   **Comunicação de IA:** Integração via API ao DEEPSEEK (Motor Principal) e Qwen2-VL (Visão).
*   **Processamento de Áudio:** Deepgram (Speech-to-Text).
*   **Banco de Dados:** ChromaDB (Vetorial/RAG).
*   **Infraestrutura de Sistema:** `AppKit` (macOS Native APIs), `pynput` (Global Hotkeys), Threading Assíncrono com Subprocess.

## 📦 Instalação e Uso

1.  **Clone o repositório:**
    ```bash
    git clone git@github.com:IIIJHORDANIII/Anders-Agent.git
    cd Anders-Agent
    ```

2.  **Crie e ative um ambiente virtual:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Instale as dependências:**
    *(Certifique-se de ter os requisitos de áudio (portaudio) e Chroma instalados no sistema).*
    ```bash
    pip install -r requirements.txt
    ```

4.  **Inicie o Agente:**
    ```bash
    ./venv/bin/python src/main.py
    ```

## ⚙️ Arquitetura de Interação

- O Anders inicia em Background (Tray Icon no menu superior do Mac).
- Ao apertar **`Cmd + Cmd`**, a caixa de Input flutua. Você digita, aperta Enter e ela some. Quando pronta, a resposta reaparece na tela.
- Respostas rápidas e sem distrações visuais ou auditoriais (se acionadas via texto).
- A memória é completamente apagada no restart do processo (`main.py`) garantindo um "clean slate" a cada sessão de desenvolvimento.

---
*Desenvolvido com foco no futuro da interação Humano-IA. 💻 e ☕*
