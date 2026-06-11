import pyautogui
import time
import os

class ComputerUseService:
    """
    Permite ao agente interagir com a UI do macOS (Mouse e Teclado).
    Usa visão computacional para guiar as ações.
    """
    def __init__(self):
        # Configurações de segurança: move mouse para o canto para abortar
        pyautogui.FAILSAFE = True

    def vision_action(self, action, x=None, y=None, text=None):
        """Executa uma ação física baseada em coordenadas ou texto."""
        print(f"🖥️ Computer Use: Executando {action}...")
        
        try:
            if action == "click":
                pyautogui.click(x, y)
                return f"Clique realizado em ({x}, {y})"
            elif action == "type":
                pyautogui.write(text, interval=0.1)
                return f"Texto digitado: {text}"
            elif action == "press":
                pyautogui.press(text)
                return f"Tecla {text} pressionada"
            elif action == "move":
                pyautogui.moveTo(x, y, duration=0.5)
                return f"Mouse movido para ({x}, {y})"
            elif action == "double_click":
                pyautogui.doubleClick(x, y)
                return f"Clique duplo realizado em ({x}, {y})"
            else:
                return f"Ação {action} não suportada."
        except Exception as e:
            return f"Erro no Computer Use: {e}"

    def scroll(self, direction="down", amount=10):
        """Executa scroll na tela."""
        clicks = -amount if direction == "down" else amount
        pyautogui.scroll(clicks)
        return f"Scroll {direction} realizado."

    def start_gesture_control(self, vision_service):
        """Inicia detecção básica de movimento para comandos sem toque."""
        def _gesture_loop():
            print("🖥️ Gesture Control: Monitorando movimentos...")
            # Lógica simplificada de movimento (V1)
            # Detecta mudanças rápidas na webcam e mapeia para ações simples
            pass
        
        import threading
        threading.Thread(target=_gesture_loop, daemon=True).start()
