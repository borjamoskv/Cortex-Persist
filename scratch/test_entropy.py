import zlib

texts = [
    "Hola a todos, bienvenidos a mi nuevo tutorial sobre Python, hoy vamos a ver unas cuantas cosas chulas que os van a encantar, como por ejemplo qué pasa si pones print hola mundo. Espero que os guste mucho y que le deis like al vídeo porque me ha costado mucho hacerlo. Gracias por venir y suscribiros.",
    "La termodinámica del cómputo en CORTEX se define por la exergía de la inferencia. Axioma Ω2 estipula que el rendimiento estocástico debe minimizarse mediante la cristalización JIT de hechos soberanos.",
]

for t in texts:
    c = zlib.compress(t.encode("utf-8"))
    print(f"Len: {len(t)} | Compressed: {len(c)} | Ratio: {len(c) / len(t):.4f}")
