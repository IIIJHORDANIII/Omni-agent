import os
import numpy as np
import torch
import threading
import wave
import tempfile


def resource_path(relative_path):
    """Retorna o caminho absoluto para recursos, funcionando em dev e bundle."""
    try:
        import sys
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base_path, relative_path)

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class SpeakerVerifier:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(SpeakerVerifier, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.model = None
        self.reference_embedding = None
        self.device = 'cpu'
        self.threshold = 0.65
        self.embedding_path = os.path.expanduser("~/.config/anders/memory_db/speaker_embedding.npy")
        self.model_name = "campplus"
        self.sample_rate = 16000
        self._initialized = True

    def _load_model(self):
        if self.model is not None:
            return
        print("SpeakerVerifier: Carregando CAM++...")
        
        # Monkeypatch torchaudio para compatibilidade com versões novas (>= 2.1.0)
        import torchaudio
        if not hasattr(torchaudio, 'set_audio_backend'):
            torchaudio.set_audio_backend = lambda x: None
        
        # Procura modelos primeiro no bundle, depois em dev
        default_wespeaker = resource_path("pretrained_models/wespeaker")
        env_home = os.environ.get("WESPEAKER_HOME", default_wespeaker)
        
        os.environ["WESPEAKER_HOME"] = env_home
        import wespeaker
        self.model = wespeaker.load_model(self.model_name)
        self.model.set_device(self.device)
        self._warmup()
        print(f"SpeakerVerifier: CAM++ residente em memoria ({self.device}).")

    def _warmup(self):
        dummy = np.zeros(self.sample_rate, dtype=np.float32)
        pcm = torch.tensor(dummy, dtype=torch.float32).unsqueeze(0)
        try:
            self.model.extract_embedding_from_pcm(pcm, self.sample_rate)
        except Exception:
            pass

    def preload(self):
        if self.model is not None:
            return
        try:
            self._load_model()
            print("SpeakerVerifier: Modelo pre-carregado.")
        except Exception as e:
            print(f"SpeakerVerifier: Erro ao pre-carregar: {e}")

    def load_reference(self):
        if self.reference_embedding is not None:
            return True
        if os.path.exists(self.embedding_path):
            try:
                self.reference_embedding = np.load(self.embedding_path)
                print(f"SpeakerVerifier: Perfil de voz carregado ({self.reference_embedding.shape}).")
                return True
            except Exception as e:
                print(f"SpeakerVerifier: Erro ao carregar embedding: {e}")
        print("SpeakerVerifier: Nenhum perfil de voz encontrado. Execute o setup.")
        return False

    def _check_liveness(self, audio_np):
        if len(audio_np) < self.sample_rate * 1.5:
            print(f"SpeakerVerifier: Liveness REJEITADO - audio muito curto ({len(audio_np)/self.sample_rate:.1f}s, min 1.5s).")
            return False
        peak_energy = np.max(np.abs(audio_np))
        if peak_energy < 0.008:
            print("SpeakerVerifier: Liveness REJEITADO - audio praticamente mudo.")
            return False
        speech_mask = np.abs(audio_np) > 0.012
        speech_ratio = np.sum(speech_mask) / len(audio_np)
        if speech_ratio < 0.03:
            print(f"SpeakerVerifier: Liveness REJEITADO - fala insuficiente ({speech_ratio:.0%}).")
            return False
        return True

    def extract_embedding_from_numpy(self, audio_np):
        self._load_model()
        if audio_np.dtype != np.float32:
            audio_np = audio_np.astype(np.float32)
        max_val = np.abs(audio_np).max()
        if max_val > 0:
            audio_np = audio_np / max_val
        pcm = torch.tensor(audio_np, dtype=torch.float32).unsqueeze(0)
        emb = self.model.extract_embedding_from_pcm(pcm, self.sample_rate)
        return emb

    def extract_embedding_from_file(self, file_path):
        self._load_model()
        return self.model.extract_embedding(file_path)

    def enroll_from_samples(self, audio_samples):
        if not audio_samples:
            print("SpeakerVerifier: Nenhuma amostra fornecida.")
            return False
        self._load_model()
        embeddings = []
        for i, sample in enumerate(audio_samples):
            if len(sample) < self.sample_rate * 0.8:
                print(f"SpeakerVerifier: Amostra {i+1} muito curta, ignorando.")
                continue
            try:
                emb = self.extract_embedding_from_numpy(sample)
                if emb is not None:
                    embeddings.append(emb)
            except Exception as e:
                print(f"SpeakerVerifier: Erro na amostra {i+1}: {e}")
        if not embeddings:
            print("SpeakerVerifier: Nenhuma amostra valida para criar perfil.")
            return False
        stacked = torch.stack(embeddings)
        mean_embedding = stacked.mean(dim=0)
        mean_embedding = mean_embedding / mean_embedding.norm(p=2)
        os.makedirs(os.path.dirname(self.embedding_path), exist_ok=True)
        np.save(self.embedding_path, mean_embedding.numpy())
        self.reference_embedding = mean_embedding.numpy()
        print(f"SpeakerVerifier: Perfil salvo com {len(embeddings)} amostras. Threshold={self.threshold}")
        return True

    def enroll_from_files(self, file_paths):
        if not file_paths:
            print("SpeakerVerifier: Nenhum arquivo fornecido.")
            return False
        self._load_model()
        embeddings = []
        for i, path in enumerate(file_paths):
            try:
                emb = self.extract_embedding_from_file(path)
                if emb is not None:
                    embeddings.append(emb)
            except Exception as e:
                print(f"SpeakerVerifier: Erro no arquivo {i+1}: {e}")
        if not embeddings:
            print("SpeakerVerifier: Nenhum embedding valido.")
            return False
        stacked = torch.stack(embeddings)
        mean_embedding = stacked.mean(dim=0)
        mean_embedding = mean_embedding / mean_embedding.norm(p=2)
        os.makedirs(os.path.dirname(self.embedding_path), exist_ok=True)
        np.save(self.embedding_path, mean_embedding.numpy())
        self.reference_embedding = mean_embedding.numpy()
        print(f"SpeakerVerifier: Perfil salvo com {len(embeddings)} arquivos. Threshold={self.threshold}")
        return True

    def verify(self, audio_np, return_score=False):
        if not self.load_reference():
            if return_score:
                return True, 1.0
            return True

        if len(audio_np) < self.sample_rate * 1.5:
            print(f"SpeakerVerifier: Audio muito curto para verificacao ({len(audio_np)/self.sample_rate:.1f}s).")
            if return_score:
                return False, 0.0
            return False

        if not self._check_liveness(audio_np):
            if return_score:
                return False, 0.0
            return False

        self._load_model()

        try:
            live_emb = self.extract_embedding_from_numpy(audio_np)
            if live_emb is None:
                print("SpeakerVerifier: VAD rejeitou o audio.")
                if return_score:
                    return False, 0.0
                return False

            score = self.model.cosine_similarity(
                torch.tensor(self.reference_embedding, dtype=torch.float32),
                live_emb
            )

            is_match = score > self.threshold
            print(f"SpeakerVerifier: score={score:.4f} threshold={self.threshold} match={is_match}")

            if return_score:
                return is_match, score
            return is_match

        except Exception as e:
            print(f"SpeakerVerifier: Erro na verificacao: {e}")
            if return_score:
                return True, 0.0
            return True


speaker_verifier = SpeakerVerifier()