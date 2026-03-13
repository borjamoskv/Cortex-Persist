"""
DSP Apotheosis.
Capa determinista de procesamiento de señal en Python (Mastering, Tonal Balance, Phase Alignment).
"""

import logging

import numpy as np
import pyloudnorm as pyln
import scipy.signal

try:
    from numba import njit

    _NUMBA_AVAILABLE = True
except ImportError:
    _NUMBA_AVAILABLE = False

    def njit(func):  # type: ignore[misc]  # noqa: E302
        """No-op decorator when numba is not available."""
        return func


logger = logging.getLogger(__name__)


# Standards and Constants
DEFAULT_SAMPLING_RATE = 44100
MIN_AUDIO_LENGTH = 1024
LUFS_FLOOR = -144.0
PINK_NOISE_SLOPE_OFFSET = 1e-10
MIN_FREQ_HZ = 30
MAX_GAIN_BOOST = 4.0
MIN_GAIN_BOOST = 0.25
ATTACK_ALPHA_MS = 0.002
RELEASE_ALPHA_MS = 0.050
TRANSIENT_BOOST_THRESHOLD = 0.005
TRANSIENT_BOOST_FACTOR = 1.15
STREAMING_LUFS_TARGET = -14.0
MAX_MASTERING_GAIN_DB = 12.0
PEAK_CEILING = 0.99


@njit
def _fast_envelope_follower(
    audio_data: np.ndarray, alpha_attack: float, alpha_release: float
) -> np.ndarray:
    n = len(audio_data)
    envelope = np.zeros(n)
    curr = 0.0
    abs_audio = np.abs(audio_data)
    for i in range(n):
        target = abs_audio[i]
        if target > curr:
            curr = alpha_attack * curr + (1.0 - alpha_attack) * target
        else:
            curr = alpha_release * curr + (1.0 - alpha_release) * target
        envelope[i] = curr
    return envelope


class DSPApotheosis:
    """
    El motor de post-producción O(1).
    Evita la manipulación no predictible de la IA mediante matemática acústica estricta.
    """

    def __init__(self):
        pass

    def calculate_lufs(self, audio_data: np.ndarray, sample_rate: int) -> float:
        """Calcula Integrated LUFS usando pyloudnorm (EBU R128 / ITU-R BS.1770)."""
        if len(audio_data) == 0:
            return LUFS_FLOOR
        # pyloudnorm requiere [samples, channels]
        meter = pyln.Meter(sample_rate)
        try:
            lufs = meter.integrated_loudness(audio_data)
            return float(lufs)
        except (ValueError, AttributeError) as e:
            # Catch specific errors from pyloudnorm internals or buffer shape
            logger.error("Error calculando LUFS: %s", e)
            return LUFS_FLOOR

    def match_pink_noise_curve(self, audio_data: np.ndarray, sample_rate: int) -> np.ndarray:
        """
        Ecualización adaptativa para balancear el espectro hacia una pendiente de -3dB/octavo.
        """
        n = len(audio_data)
        if n < MIN_AUDIO_LENGTH:
            return audio_data
        freqs = np.fft.rfftfreq(n, d=1 / sample_rate)
        spectrum = np.fft.rfft(audio_data)
        magnitude = np.abs(spectrum)

        # Ideal pink noise spectrum: magnitude proportional to 1/sqrt(f)
        ideal_slope = np.zeros_like(freqs)
        # Avoid division by zero at DC
        ideal_slope[1:] = 1.0 / (np.sqrt(freqs[1:]) + PINK_NOISE_SLOPE_OFFSET)
        # Match magnitude above 30Hz
        mask = freqs > MIN_FREQ_HZ
        if np.any(mask):
            scaling = np.median(magnitude[mask]) / (
                np.median(ideal_slope[mask]) + PINK_NOISE_SLOPE_OFFSET
            )
            ideal_slope *= scaling

        # Calculate corrective gain
        gain = np.ones_like(magnitude)
        gain[mask] = ideal_slope[mask] / (magnitude[mask] + PINK_NOISE_SLOPE_OFFSET)

        # Clip gain to avoid extreme resonance (+/- 12dB)
        gain = np.clip(gain, MIN_GAIN_BOOST, MAX_GAIN_BOOST)

        # Smooth gain curve using Savitzky-Golay filter
        win_size = min(101, len(gain) // 4 * 2 + 1)
        if win_size > 5:
            gain = scipy.signal.savgol_filter(gain, win_size, 3)

        # Apply gain in frequency domain
        spectrum_matched = spectrum * gain
        audio_matched = np.fft.irfft(spectrum_matched, n=n)

        return audio_matched

    def apply_transient_shaping(self, audio_data: np.ndarray, sample_rate: int) -> np.ndarray:
        """
        Realza ataques percusivos perdiendo 'bluntness' de IA usando un seguidor de envolvente.
        """
        alpha_at = np.exp(-1.0 / (ATTACK_ALPHA_MS * sample_rate))
        alpha_re = np.exp(-1.0 / (RELEASE_ALPHA_MS * sample_rate))

        # Handle stereo/mono
        if len(audio_data.shape) > 1:
            processed = np.zeros_like(audio_data)
            for ch in range(audio_data.shape[1]):
                env = _fast_envelope_follower(audio_data[:, ch], alpha_at, alpha_re)
                diff = np.diff(env, prepend=0)
                boost = np.where(diff > TRANSIENT_BOOST_THRESHOLD, TRANSIENT_BOOST_FACTOR, 1.0)
                processed[:, ch] = audio_data[:, ch] * boost
            return processed
        else:
            env = _fast_envelope_follower(audio_data, alpha_at, alpha_re)
            diff = np.diff(env, prepend=0)
            boost = np.where(diff > TRANSIENT_BOOST_THRESHOLD, TRANSIENT_BOOST_FACTOR, 1.0)
            return audio_data * boost

    def master_track(self, audio_data: np.ndarray, sample_rate: int) -> np.ndarray:
        """
        Finalización determinista: Tonal Match -> Transient Design -> Loudness Norm -> Peak Limiting.
        """
        logger.info("Iniciando mastering determinista. SR: %dHz", sample_rate)

        # 1. Tonal Balance (Pink Noise matching)
        if len(audio_data.shape) > 1 and audio_data.shape[1] == 2:
            audio_data[:, 0] = self.match_pink_noise_curve(audio_data[:, 0], sample_rate)
            audio_data[:, 1] = self.match_pink_noise_curve(audio_data[:, 1], sample_rate)
        else:
            audio_data = self.match_pink_noise_curve(audio_data, sample_rate)

        # 2. Transient Shaping
        audio_data = self.apply_transient_shaping(audio_data, sample_rate)

        # 3. Loudness Normalization to target (Streaming Standard)
        current_lufs = self.calculate_lufs(audio_data, sample_rate)
        if current_lufs > LUFS_FLOOR:
            gain_db = STREAMING_LUFS_TARGET - current_lufs
            # Prevent excessive boost
            gain_db = min(gain_db, MAX_MASTERING_GAIN_DB)
            gain_linear = 10 ** (gain_db / 20.0)
            audio_data *= gain_linear

        # 4. Final Peak Limiter / Ceiling
        audio_data = np.clip(audio_data, -PEAK_CEILING, PEAK_CEILING)

        final_lufs = self.calculate_lufs(audio_data, sample_rate)
        logger.info("Mastering finalizado. LUFS Final: %.2f", final_lufs)

        return audio_data
