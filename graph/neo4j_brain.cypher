// Cortex-Persist :: Human Brain Mapping → Neo4j Executable Graph
// C4-SIM conversion layer

// NODES
CREATE CONSTRAINT IF NOT EXISTS FOR (n:BrainRegion) REQUIRE n.id IS UNIQUE;

// L1 Motor & Autonomic
MERGE (:BrainRegion {id:'bulbo_raquideo', layer:'L1', function:'vital_rhythms', compute:'PID0_daemon', latency_ms:'<5'});
MERGE (:BrainRegion {id:'puente_varolio', layer:'L1', function:'sleep_wake_routing', compute:'load_balancer_cron', latency_ms:'10'});
MERGE (:BrainRegion {id:'cerebelo', layer:'L1', function:'motor_prediction', compute:'fpu_pid_controller', latency_ms:'15'});
MERGE (:BrainRegion {id:'formacion_reticular', layer:'L1', function:'arousal', compute:'interrupt_controller', latency_ms:'50'});

// L2 Limbic & Memory
MERGE (:BrainRegion {id:'amigdala', layer:'L2', function:'salience_detection', compute:'IDS_nmi', latency_ms:'20'});
MERGE (:BrainRegion {id:'hipocampo', layer:'L2', function:'episodic_memory', compute:'vector_db_commit_log', latency_ms:'150'});
MERGE (:BrainRegion {id:'hipotalamo', layer:'L2', function:'homeostasis', compute:'hardware_monitor', latency_ms:'minutes'});
MERGE (:BrainRegion {id:'cingulado', layer:'L2', function:'error_evaluation', compute:'loss_function_handler', latency_ms:'150'});

// L3 Routing
MERGE (:BrainRegion {id:'talamo', layer:'L3', function:'sensory_router', compute:'bus_router', latency_ms:'30'});
MERGE (:BrainRegion {id:'ganglios_basales', layer:'L3', function:'action_selection', compute:'rl_gating_mutex', latency_ms:'100'});
MERGE (:BrainRegion {id:'cuerpos_mamilares', layer:'L3', function:'spatial_memory', compute:'cache_pathfinding', latency_ms:'100'});

// L4 Cortex
MERGE (:BrainRegion {id:'occipital', layer:'L4', function:'vision', compute:'cnn', latency_ms:'80'});
MERGE (:BrainRegion {id:'temporal', layer:'L4', function:'semantics_audio', compute:'kv_store', latency_ms:'150'});
MERGE (:BrainRegion {id:'parietal', layer:'L4', function:'sensor_fusion', compute:'3d_coordinate_system', latency_ms:'200'});
MERGE (:BrainRegion {id:'frontal', layer:'L4', function:'planning_language', compute:'token_scheduler', latency_ms:'250'});
MERGE (:BrainRegion {id:'prefrontal', layer:'L4', function:'executive_control', compute:'llm_hypervisor', latency_ms:'500'});

// EDGES (CONNECTOME)
MERGE (:BrainRegion {id:'talamo'})-[:ROUTES_TO]->(:BrainRegion {id:'occipital'});
MERGE (:BrainRegion {id:'talamo'})-[:ROUTES_TO]->(:BrainRegion {id:'parietal'});
MERGE (:BrainRegion {id:'talamo'})-[:ROUTES_TO]->(:BrainRegion {id:'temporal'});

MERGE (:BrainRegion {id:'ganglios_basales'})-[:GATES]->(:BrainRegion {id:'frontal'});
MERGE (:BrainRegion {id:'cingulado'})-[:ERROR_FEEDBACK]->(:BrainRegion {id:'prefrontal'});
MERGE (:BrainRegion {id:'amigdala'})-[:INTERRUPT]->(:BrainRegion {id:'prefrontal'});
MERGE (:BrainRegion {id:'hipocampo'})-[:FEEDS_CONTEXT]->(:BrainRegion {id:'prefrontal'});

MERGE (:BrainRegion {id:'prefrontal'})-[:CONTROLS]->(:BrainRegion {id:'frontal'});
MERGE (:BrainRegion {id:'frontal'})-[:EXECUTES]->(:BrainRegion {id:'motor_output'});
