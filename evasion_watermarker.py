import hashlib
import os
import json
import logging
import struct
from pathlib import Path

# Configuración Soberana
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [EVASION-WATERMARK] - %(message)s')

class SovereignWatermarker:
    """
    Inyecta entropía criptográfica (SHA-256) y metadatos de evasión directamente 
    en las cabeceras BWF (Broadcast Wave Format) o INFO chunks de un archivo .wav.
    """
    
    def __init__(self, owner_address: str, project_name: str):
        self.owner_address = owner_address
        self.project_name = project_name
        self.evasion_version = "v2.2-Spatial"
        
    def _calculate_audio_hash(self, file_path: str) -> str:
        """Calcula el hash SHA-256 del archivo WAV completo."""
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            while chunk := f.read(8192):
                sha256.update(chunk)
        return sha256.hexdigest()

    def generate_merkle_payload(self, file_path: str) -> dict:
        """Genera el payload criptográfico que irá al blockchain y al archivo."""
        audio_hash = self._calculate_audio_hash(file_path)
        
        payload = {
            "origin": "Mastering Evasion Protocol",
            "version": self.evasion_version,
            "owner": self.owner_address,
            "project": self.project_name,
            "audio_sha256": audio_hash,
            "anti_scraping_policy": "NO_AI_TRAINING_ALLOWED",
            # Merkle Proof simulado para el ejemplo
            "merkle_root": hashlib.sha256(f"{audio_hash}{self.owner_address}".encode()).hexdigest() 
        }
        return payload

    def inject_bext_metadata(self, input_wav: str, output_wav: str):
        """
        Lee el WAV original y lo copia a output_wav, inyectando un chunk 'INFO' o 'bext' custom
        con la política de evasión y la raíz de Merkle.
        (Implementación a nivel binario de RIFF para asegurar compatibilidad).
        """
        if not os.path.exists(input_wav):
            logging.error(f"El archivo {input_wav} no existe.")
            return

        payload = self.generate_merkle_payload(input_wav)
        payload_bytes = json.dumps(payload).encode('utf-8')
        
        # Debe ser par (word alignment)
        if len(payload_bytes) % 2 != 0:
            payload_bytes += b'\x00'
            
        logging.info(f"Cripto-Payload generado: {payload['merkle_root'][:16]}...")

        with open(input_wav, 'rb') as f_in, open(output_wav, 'wb') as f_out:
            # Leer cabecera RIFF
            riff_header = f_in.read(12)
            if not riff_header.startswith(b'RIFF'):
                logging.error("Ignorado: No es un archivo WAV RIFF válido.")
                return
                
            # Escribir cabecera temporal (la actualizaremos al final)
            f_out.write(riff_header)
            
            # Copiar el resto de chunks originales
            while True:
                chunk_header = f_in.read(8)
                if len(chunk_header) < 8:
                    break
                chunk_id, chunk_size = struct.unpack('<4sI', chunk_header)
                f_out.write(chunk_header)
                
                # Leer y copiar datos del chunk
                chunk_data = f_in.read(chunk_size)
                f_out.write(chunk_data)
                
                # Padding si es impar
                if chunk_size % 2 != 0:
                    pad = f_in.read(1)
                    f_out.write(pad)

            # --- INYECCIÓN DEL CHUNK de EVASIÓN (Formato custom 'evas') ---
            logging.info(f"Inyectando chunk criptográfico soberano [evas] ({len(payload_bytes)} bytes)...")
            f_out.write(b'evas')
            f_out.write(struct.pack('<I', len(payload_bytes)))
            f_out.write(payload_bytes)

            # Actualizar el file size de la cabecera RIFF principal
            file_size = f_out.tell()
            f_out.seek(4)
            f_out.write(struct.pack('<I', file_size - 8))
            
        logging.info(f"Mastering sellado correctamente en: {output_wav}")


# Bloque de prueba
if __name__ == "__main__":
    # Datos simulados del autor (Tu wallet / ID)
    AUTHOR_WALLET = "0x29f804ecc... (Borja Moskv)"
    PROJECT = "CORTEX-Demo-Track"
    
    watermarker = SovereignWatermarker(owner_address=AUTHOR_WALLET, project_name=PROJECT)
    
    # Crea un dummy wav si quieres probarlo rápido
    test_in = "dummy_mix.wav"
    test_out = "master_evaded.wav"
    
    if not os.path.exists(test_in):
        # Crear un micro WAV mudo de prueba
        import wave
        with wave.open(test_in, 'wb') as w:
            w.setnchannels(2)
            w.setsampwidth(2)
            w.setframerate(44100)
            w.writeframes(b'\x00' * 44100) # 1 segundo mudo
            
    watermarker.inject_bext_metadata(test_in, test_out)
    logging.info("Firmas inyectadas y listas para auditoría en Polygon.")
