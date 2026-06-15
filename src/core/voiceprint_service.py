import os
import json
import numpy as np
import torch
import torchaudio
from scipy.spatial.distance import cosine
from core.memory_client import MemoryClient


class VoiceprintService:
    """
    Servico de identificacao por voz (voiceprint).
    Compara embeddings MFCC da voz do usuario com um perfil salvo.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized: return
        self.sample_rate = 16000
        self.n_mfcc = 40
        self.mfcc_transform = torchaudio.transforms.MFCC(
            sample_rate=self.sample_rate,
            n_mfcc=self.n_mfcc,
            melkwargs={'n_fft': 512, 'hop_length': 160, 'n_mels': 64}
        )
        self._profile = None
        self._threshold = 0.75  # Similaridade minima para considerar "mesma pessoa"
        self._memory = MemoryClient()
        self._initialized = True

    def _audio_to_embedding(self, audio_np):
        """Converte audio numpy para embedding MFCC medio."""
        waveform = torch.FloatTensor(audio_np).unsqueeze(0)
        mfcc = self.mfcc_transform(waveform)  # (1, n_mfcc, time)
        # Media temporal = embedding fixo
        embedding = mfcc.mean(dim=2).squeeze(0).numpy()  # (n_mfcc,)
        # Normaliza
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm
        return embedding

    def _cosine_similarity(self, a, b):
        """Similaridade coseno entre dois vetores (1 = identico, 0 = oposto)."""
        return 1 - cosine(a, b)

    def register(self, audio_samples):
        """
        Registra o perfil de voz do usuario.
        audio_samples: lista de arrays numpy (cada um = 2-3 segundos de audio limpo)
        Retorna: True se registro OK, False caso contrario.
        """
        if not audio_samples or len(audio_samples) < 2:
            print("Voiceprint: Preciso de pelo menos 2 amostras de voz.")
            return False

        embeddings = []
        for i, sample in enumerate(audio_samples):
            if len(sample) < self.sample_rate:
                print(f"Voiceprint: Amostra {i} muito curta ({len(sample)/self.sample_rate:.1f}s). Pulando.")
                continue
            emb = self._audio_to_embedding(sample)
            embeddings.append(emb)

        if len(embeddings) < 2:
            print("Voiceprint: Amostras insuficientes para registro.")
            return False

        # Embedding final = media dos embeddings
        avg_embedding = np.mean(embeddings, axis=0)
        norm = np.linalg.norm(avg_embedding)
        if norm > 0:
            avg_embedding = avg_embedding / norm

        # Salva no profile
        self._profile = avg_embedding.tolist()
        self._memory.save_fact("voiceprint_profile", json.dumps(self._profile))
        print(f"Voiceprint: Perfil registrado com {len(embeddings)} amostras.")
        return True

    def load_profile(self):
        """Carrega o perfil de voz salvo na memoria."""
        if self._profile is not None:
            return True

        raw = self._memory.get_fact("voiceprint_profile", exact_only=True)
        if not raw:
            return False

        try:
            clean = raw.strip().strip('"').strip("'")
            parsed = json.loads(clean)
            if not isinstance(parsed, list) or len(parsed) != self.n_mfcc:
                print(f"Voiceprint: Perfil invalido (esperado {self.n_mfcc} floats, got {type(parsed).__name__} len={len(parsed) if isinstance(parsed, list) else '?'})")
                self._profile = None
                return False
            self._profile = parsed
            return True
        except (json.JSONDecodeError, ValueError):
            print("Voiceprint: Perfil corrompido (nao e JSON valido). Ignorando.")
            self._profile = None
            return False

    def identify(self, audio_np):
        """
        Identifica se o audio corresponde ao usuario registrado.
        audio_np: array numpy do audio
        Retorna: (is_user: bool, similarity: float, label: str)
        """
        if not self.load_profile():
            return (False, 0.0, "sem_perfil")

        embedding = self._audio_to_embedding(audio_np)
        similarity = self._cosine_similarity(self._profile, embedding)

        is_user = similarity >= self._threshold
        label = "usuario" if is_user else "desconhecido"

        print(f"Voiceprint: similaridade={similarity:.3f} (threshold={self._threshold}) -> {label}")
        return (is_user, similarity, label)

    def is_registered(self):
        """Verifica se ja existe um perfil registrado."""
        return self.load_profile()

    def delete_profile(self):
        """Remove o perfil de voz."""
        self._profile = None
        self._memory.save_fact("voiceprint_profile", "")
        print("Voiceprint: Perfil removido.")
