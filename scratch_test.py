import sys
from cortex.math.babylon import Babylon60
from cortex.engine._genome_types import Lineage, FitnessRecord

lineage = Lineage(generation=0, parent_hash='GENESIS')
print("lineage.avg_fitness type:", type(lineage.avg_fitness))
print("lineage.avg_fitness repr:", repr(lineage.avg_fitness))
