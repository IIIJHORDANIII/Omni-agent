# Omni-agent 🤖

> **O seu assistente autônomo total para macOS, focado em produtividade e raciocínio profundo.**

Omni-agent é um agente virtual alimentado por IA (DeepSeek-R1 / Qwen2-VL) projetado para rodar nativamente no Apple Silicon via MLX. Ele age como um "Pair Programmer Fantasma", um "Sentinela" (Monitor de Sistema) e um assistente conversacional capaz de interagir com o sistema operacional, analisar a tela e gerar código, tudo enquanto mantém a privacidade e a eficiência local.

## 🚀 Principais Recursos

*   **Cérebro Raciocinante Local:** Utiliza `mlx-community/DeepSeek-R1-Distill-Qwen-1.5B-4bit` para raciocínio avançado.
*   **Visão Real (Protocolo Recall):** Captura e indexa momentos visuais usando `mlx-community/Qwen2-VL-2B-Instruct-4bit`, agindo como uma memória fotográfica.
*   **Sentinela (Oracle Mode):** Monitoramento contínuo de uso de CPU, RAM e da janela ativa, oferecendo sugestões proativas.
*   **Ghost Pair Programmer (Overwatch):** Analisa silenciosamente o código e sugere refatorações de Clean Code.
*   **Interação por Voz:** Ativação por Wake Word e respostas usando recursos nativos do macOS ou modelo Kokoro.
*   **Interface HUD:** Overlay elegante (Vibrancy effect) para telemetria em tempo real.

## 🛠️ Tecnologias Utilizadas

*   **Linguagem:** Python 3.14 (Backend) / Swift (APIs macOS)
*   **Interface:** PyQt6
*   **IA & Inferência:** Apple MLX, Whisper, Qwen2, DeepSeek
*   **Monitoramento:** `psutil`, `mss`

## 📦 Instalação e Uso

1.  **Clone o repositório:**
    ```bash
    git clone git@github.com:IIIJHORDANIII/Omni-agent.git
    cd Omni-agent
    ```

2.  **Crie e ative um ambiente virtual:**
    ```bash
    python -m venv venv
    source venv/bin/activate
    ```

3.  **Inicie o Agente:**
    ```bash
    python src/main.py
    ```

## 🔒 Segurança e Privacidade
O processamento pesado (LLM, Visão) é realizado **localmente** utilizando Apple MLX, garantindo que o conteúdo da sua tela e interações não sejam enviadas para a nuvem sem a sua solicitação.

---
*Desenvolvido com 💻 e ☕*
