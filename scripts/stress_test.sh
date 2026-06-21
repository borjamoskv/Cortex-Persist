#!/bin/bash
echo ">>> INICIANDO COLISIÓN TERMODINÁMICA (Legion 10K) <<<"
rm -rf /tmp/cortex_stress
export PYTHONPATH=$(pwd)/python
python3 python/offline_trainer/stress_consumer.py &
PY_PID=$!

# Small delay to let Python spin up
sleep 0.5

cd cortex-swarm-v2/crates/mmap-logger
cargo run --release --bin stress_producer

wait $PY_PID
echo ">>> COLISIÓN FINALIZADA <<<"
