import numpy as np
import pyaudio
import os
import json
import threading
import time
from pathlib import Path

class WakeWordService:
    """
    Serviço de wake word treinável.
    Grava amostras do usuário dizendo a wake word e detecta por similaridade de áudio.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(WakeWordService, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1
        self.RATE = 16000
        self.CHUNK = 1024
        
        self.data_dir = Path("memory_db/wake_word")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.templates_file = self.data_dir / "templates.npy"
        self.config_file = self.data_dir / "config.json"
        
        self.templates = []  # Lista de arrays numpy (áudios normalizados)
        self.threshold = 0.35  # Similaridade mínima (0-1)
        self.min_samples = 3  # Mínimo de amostras para treinar
        
        self._load_templates()
        self._initialized = True
    
    def _load_templates(self):
        """Carrega templates salvos."""
        if self.templates_file.exists():
            try:
                self.templates = list(np.load(self.templates_file, allow_pickle=True))
                print(f"WakeWord: {len(self.templates)} templates carregados")
            except Exception as e:
                print(f"WakeWord: Erro ao carregar templates: {e}")
                self.templates = []
        
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    self.threshold = config.get('threshold', self.threshold)
            except:
                pass
    
    def _save_templates(self):
        """Salva templates em disco."""
        try:
            np.save(self.templates_file, np.array(self.templates, dtype=object), allow_pickle=True)
            with open(self.config_file, 'w') as f:
                json.dump({'threshold': self.threshold}, f)
            print(f"WakeWord: {len(self.templates)} templates salvos")
        except Exception as e:
            print(f"WakeWord: Erro ao salvar templates: {e}")
    
    def is_trained(self):
        """Verifica se tem templates suficientes."""
        return len(self.templates) >= self.min_samples
    
    def record_sample(self, duration=2.0, prompt=None):
        """
        Grava uma amostra de áudio.
        Retorna: numpy array normalizado ou None se falhou.
        """
        if prompt:
            print(f"\n🎤 {prompt}")
            print(f"   Fale a wake word em {duration} segundos...")
            print("   Gravando...")
        
        p = pyaudio.PyAudio()
        stream = p.open(
            format=self.FORMAT,
            channels=self.CHANNELS,
            rate=self.RATE,
            input=True,
            frames_per_buffer=self.CHUNK
        )
        
        frames = []
        for _ in range(int(self.RATE / self.CHUNK * duration)):
            data = stream.read(self.CHUNK, exception_on_overflow=False)
            frames.append(data)
        
        stream.stop_stream()
        stream.close()
        p.terminate()
        
        # Converter para numpy
        audio = np.frombuffer(b''.join(frames), dtype=np.int16).astype(np.float32)
        audio = audio / 32768.0  # Normalizar
        
        # Verificar se tem áudio (não silêncio)
        energy = np.sqrt(np.mean(audio**2))
        if energy < 0.01:
            print("❌ Áudio muito baixo ou silêncio. Tente novamente.")
            return None
        
        # Normalizar energia
        audio = audio / (np.max(np.abs(audio)) + 1e-8)
        
        print(f"✓ Amostra gravada! Energia: {energy:.4f}")
        return audio
    
    def add_template(self, audio):
        """Adiciona uma amostra como template."""
        # Resample para tamanho fixo (16000 samples = 1 segundo)
        target_len = self.RATE  # 1 segundo
        if len(audio) > target_len:
            # Pegar o meio (onde geralmente está a palavra)
            start = (len(audio) - target_len) // 2
            audio = audio[start:start + target_len]
        elif len(audio) < target_len:
            # Pad com zeros
            audio = np.pad(audio, (0, target_len - len(audio)))
        
        self.templates.append(audio)
        self._save_templates()
        return len(self.templates)
    
    def train(self, num_samples=5, duration_each=2.0):
        """
        Fluxo de treinamento interativo.
        Grava N amostras da wake word.
        """
        print("\n" + "="*50)
        print("🎓 TREINAMENTO DA WAKE WORD")
        print("="*50)
        print(f"Você vai gravar {num_samples} amostras da wake word.")
        print("Dica: Fale 'OMINI' de forma clara e natural.")
        print("="*50)
        
        recorded = 0
        attempts = 0
        max_attempts = num_samples * 3  # Limite de tentativas
        
        while recorded < num_samples and attempts < max_attempts:
            attempts += 1
            sample = self.record_sample(
                duration=duration_each,
                prompt=f"Amostra {recorded + 1}/{num_samples}"
            )
            
            if sample is not None:
                # Perguntar se está bom
                print("\n  ✓ Amostra ok? (Enter para aceitar, 'r' para refazer)")
                choice = input("  > ").strip().lower()
                
                if choice != 'r':
                    self.add_template(sample)
                    recorded += 1
                    print(f"  ✓ Amostra {recorded}/{num_samples} salva!\n")
                else:
                    print("  ↻ Refazendo amostra...\n")
            else:
                print("  ↻ Tentando novamente...\n")
        
        if recorded >= self.min_samples:
            print("\n" + "="*50)
            print(f"✅ TREINAMENTO CONCLUÍDO! {recorded} amostras salvas.")
            print(f"   Threshold atual: {self.threshold}")
            print("   A wake word agora deve reconhecer sua voz!")
            print("="*50)
            return True
        else:
            print(f"\n❌ Treinamento falhou. Apenas {recorded}/{self.min_samples} amostras.")
            return False
    
    def compute_similarity(self, audio1, audio2):
        """
        Calcula similaridade entre dois áudios usando correlação cruzada FFT.
        Retorna valor entre 0 e 1.
        """
        # Garantir mesmo tamanho
        min_len = min(len(audio1), len(audio2))
        a1 = audio1[:min_len]
        a2 = audio2[:min_len]
        
        # Normalizar
        a1 = a1 - np.mean(a1)
        a2 = a2 - np.mean(a2)
        
        norm1 = np.sqrt(np.sum(a1**2))
        norm2 = np.sqrt(np.sum(a2**2))
        
        if norm1 < 1e-8 or norm2 < 1e-8:
            return 0.0
        
        a1 = a1 / norm1
        a2 = a2 / norm2
        
        # Correlação via FFT
        n = len(a1)
        fft1 = np.fft.rfft(a1)
        fft2 = np.fft.rfft(a2)
        
        correlation = np.fft.irfft(fft1 * np.conj(fft2))
        max_corr = np.max(np.abs(correlation))
        
        return float(max_corr)
    
    def detect(self, audio_chunk):
        """
        Detecta se o áudio contém a wake word.
        Retorna: (is_detected, similarity_score)
        """
        if not self.is_trained():
            return False, 0.0
        
        # Normalizar chunk
        if len(audio_chunk) < self.RATE:
            # Pad para 1 segundo
            audio_chunk = np.pad(audio_chunk, (0, self.RATE - len(audio_chunk)))
        elif len(audio_chunk) > self.RATE:
            # Pegar últimos 1 segundo
            audio_chunk = audio_chunk[-self.RATE:]
        
        # Normalizar energia
        max_val = np.max(np.abs(audio_chunk))
        if max_val > 0:
            audio_chunk = audio_chunk / max_val
        
        # Calcular similaridade com todos os templates
        similarities = []
        for template in self.templates:
            sim = self.compute_similarity(audio_chunk, template)
            similarities.append(sim)
        
        # Pegar a maior similaridade
        max_sim = max(similarities) if similarities else 0.0
        
        return max_sim >= self.threshold, max_sim
    
    def set_threshold(self, threshold):
        """Define novo threshold (0-1)."""
        self.threshold = max(0.0, min(1.0, threshold))
        self._save_templates()
        print(f"WakeWord: Threshold definido para {self.threshold}")
    
    def clear_templates(self):
        """Remove todos os templates."""
        self.templates = []
        if self.templates_file.exists():
            self.templates_file.unlink()
        if self.config_file.exists():
            self.config_file.unlink()
        print("WakeWord: Templates limpos")
    
    def get_status(self):
        """Retorna status do serviço."""
        return {
            'trained': self.is_trained(),
            'num_templates': len(self.templates),
            'threshold': self.threshold,
            'min_samples': self.min_samples
        }


# Instância global
wake_word = WakeWordService()
