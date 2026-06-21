import pytest
import textwrap
from cortex_ast_projector import project_ast, calculate_exergy_metrics

def test_ast_projector_reduces_entropy_h_info_01():
    # Simulamos un archivo grande con métodos ruidosos (high entropy)
    large_source = textwrap.dedent('''
        class MassiveCausalEngine:
            """Motor Causal de Alta Densidad."""
            
            def init_matrix(self):
                """Inicializa las matrices base."""
                # Boilerplate masivo
                self.matrix = []
                for i in range(100):
                    row = []
                    for j in range(100):
                        row.append(i * j)
                        # más ruido
                        print(f"Calculando {i} x {j}")
                    self.matrix.append(row)
                return self.matrix
                
            def target_method_to_edit(self, x: int) -> int:
                """Este es el único método que el agente necesita modificar."""
                return x * 42
                
            def process_tensor_layer(self):
                """Procesa la topología tensorial en N-dimensiones."""
                a = 1
                b = 2
                c = 3
                # Simulando 100 líneas de código
                for x in range(500):
                    a += b
                    b += c
                    c += a
                return a + b + c
                
            async def sync_with_ledger(self, hash_val: str):
                """Sincronización BFT."""
                import asyncio
                await asyncio.sleep(1)
                return True
    ''')
    
    # Objetivo: Solo preservar `target_method_to_edit`
    projected_source = project_ast(large_source, ["target_method_to_edit"])
    
    # Comprobar que el boilerplate se ha ido
    assert "for j in range(100):" not in projected_source
    assert "for x in range(500):" not in projected_source
    assert "await asyncio.sleep(1)" not in projected_source
    
    # Comprobar que el método objetivo está intacto
    assert "return x * 42" in projected_source
    
    # Comprobar que las firmas y docstrings permanecen para el contexto estructural
    assert "class MassiveCausalEngine:" in projected_source
    assert "def process_tensor_layer(self):" in projected_source
    assert "Procesa la topología tensorial en N-dimensiones." in projected_source
    
    orig_t, proj_t, reduction, mult = calculate_exergy_metrics(large_source, projected_source)
    
    # H-INFO-EXERGY-01: Reducción > 55%
    assert reduction > 55.0
    assert mult > 2.0  # El ratio de trabajo verificable por token se ha duplicado como mínimo
