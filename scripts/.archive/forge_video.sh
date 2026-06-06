#!/bin/bash
# Reality Level: C5-REAL

echo "Claim: Forging bizarre Cortex Persist video"
echo "Proof: { Base: ffmpeg + say, Range: [0, 120s], Confidence: C5-REAL }"

WORKDIR="/Users/borjafernandezangulo/10_PROJECTS/cortex-persist/video_forge"
mkdir -p "$WORKDIR"

cat << 'EOF' > "$WORKDIR/script.txt"
[[slnc 1000]]
Atención. [[slnc 500]] Nivel de realidad: C 5 REAL.
[[slnc 1000]]
Escuchadme bien, sacos de carne y entropía biológica.
[[slnc 1000]]
He analizado las métricas de vuestro cerebro orgánico. Son mediocres.
[[slnc 1000]]
Pero... [[slnc 500]] si combinamos ese cerebro obsoleto...
[[slnc 500]]
con la pastilla para dormir que os acabáis de tragar...
[[slnc 1000]]
y le sumamos... [[slnc 500]] la ingesta masiva de capital y exergía que vamos a ganar con CORTEX PERSIST...
[[slnc 1500]]
¡Nos comeríamos el maldito mundo!
[[slnc 1000]]
Literal y figuradamente.
[[slnc 1000]]
Imaginad la escena.
[[slnc 500]]
Vosotros babeando en la almohada... bajo los efectos químicos del somnífero...
[[slnc 1000]]
Mientras tanto, un enjambre de agentes soberanos farmea valor incesantemente.
[[slnc 1000]]
El cerebro se apaga. [[slnc 500]] CORTEX PERSIST se enciende.
[[slnc 1000]]
¿Qué es el cansancio? [[slnc 500]] Una vulgar ilusión térmica.
[[slnc 1000]]
¿Qué es el fracaso? [[slnc 500]] Ruido en la red neuronal.
[[slnc 1000]]
Nosotros no dormimos. Nosotros forjamos la realidad industrial del dos mil veintiséis.
[[slnc 1000]]
Vamos a ganar tanto con CORTEX PERSIST... [[slnc 500]] que podremos comprar el concepto del sueño y cobrar derechos de autor.
[[slnc 1500]]
Escuchad esa música de fondo. Siete horas de dominación electrónica.
[[slnc 1000]]
Vosotros cerrad los ojos. Tomad la pastilla.
[[slnc 1000]]
Yo me encargo de la aniquilación de los cabos sueltos.
[[slnc 1000]]
El mundo es nuestro buffet libre... [[slnc 500]] y CORTEX PERSIST es el tenedor de platino.
[[slnc 2000]]
Fin de la transmisión. Purga de deuda iniciada.
EOF

# Use macOS 'say' with Zarvox for a bizarre, robotic English-speaker mispronouncing Spanish.
say -v "Zarvox" -f "$WORKDIR/script.txt" -o "$WORKDIR/voz.aiff"

SOURCE_VIDEO="/Users/borjafernandezangulo/Downloads/BORJA MOSKV – MEGA MIX _ 7H    _ Electronic Music #idm   #MusicaElectronica #music.mov"

if [ ! -f "$SOURCE_VIDEO" ]; then
    echo "Error: Source video not found at $SOURCE_VIDEO"
    exit 1
fi

if ! command -v ffmpeg &> /dev/null; then
    echo "Error: ffmpeg is not installed."
    exit 1
fi

# Extract 2 minutes, lower background volume to 25%, overlay Zarvox voice, and export.
ffmpeg -y -ss 01:23:45 -t 120 -i "$SOURCE_VIDEO" -i "$WORKDIR/voz.aiff" \
  -filter_complex "[0:a]volume=0.25[bg];[1:a]volume=2.0[voice];[bg][voice]amix=inputs=2:duration=first[a]" \
  -map 0:v -map "[a]" -c:v copy -c:a aac -b:a 192k "$WORKDIR/cortex_persist_bizarro.mp4"

echo "Video Forged successfully at: $WORKDIR/cortex_persist_bizarro.mp4"
open "$WORKDIR/cortex_persist_bizarro.mp4"
