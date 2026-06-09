import cv2
import numpy as np
import pyautogui
import os

def find_element(template_path, confidence=0.8):
    """
    Procura um template (ícone) na tela usando OpenCV.
    Retorna (x, y) se encontrado, None caso contrário.
    """
    if not os.path.exists(template_path):
        return None

    screenshot = pyautogui.screenshot()
    frame = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
    template = cv2.imread(template_path)
    if template is None:
        return None
        
    res = cv2.matchTemplate(frame, template, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(res)
    
    if max_val >= confidence:
        h, w = template.shape[:2]
        return (max_loc[0] + w // 2, max_loc[1] + h // 2)
    return None
