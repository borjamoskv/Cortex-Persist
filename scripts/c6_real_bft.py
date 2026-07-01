
class RedDinamicaBFT:
    def __init__(self, nodos_iniciales, fallos_maximos):
        self.nodos_honestos = list(range(nodos_iniciales - fallos_maximos))
        self.nodos_bizantinos = list(range(len(self.nodos_honestos), nodos_iniciales))
        self.ledger_comun = ["Bloque_Génesis"]
        
    def mutar_topologia(self, nuevos_nodos, nodos_salientes):
        # Simulación de Churn (Entrada y salida de nodos de la red)
        for nodo in nodos_salientes:
            if nodo in self.nodos_honestos and len(self.nodos_honestos) > 3:
                self.nodos_honestos.remove(nodo)
                
        for nuevo_id in nuevos_nodos:
            self.nodos_honestos.append(nuevo_id)
            
        # Recalcular la tolerancia del sistema actual
        n_total = len(self.nodos_honestos) + len(self.nodos_bizantinos)
        f_tolerables = (n_total - 1) // 3
        return n_total, len(self.nodos_bizantinos), f_tolerables

    def verificar_consenso_dinamico(self):
        # Invariante crítica: El sistema debe mantener la resiliencia
        n, b, f = self.mutar_topologia(nuevos_nodos=[4, 5], nodos_salientes=[0])
        
        # ASSERT CRÍTICO: La red mutada sigue cumpliendo la regla fundamental BFT en C6-REAL
        assert n >= 3 * b + 1, f"Ruptura de seguridad BFT: N={n}, B={b}. Umbral mínimo violado."
        return f"Red reconfigurada con éxito. Nodos totales: {n}. Capacidad de fallo respetada."

# Instanciación y compilación del entorno C6-REAL
simulador_c6 = RedDinamicaBFT(nodos_iniciales=4, fallos_maximos=1)
resultado_c6 = simulador_c6.verificar_consenso_dinamico()
print(resultado_c6)
