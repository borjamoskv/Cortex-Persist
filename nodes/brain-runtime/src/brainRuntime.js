const { EventBus } = require('./eventBus');
const { Neo4jStore } = require('./neo4j');

let NeuralNetwork;
try {
  NeuralNetwork = require('brain.js').NeuralNetwork;
} catch (err) {
  NeuralNetwork = null;
}

class BrainRuntime {
  constructor(config) {
    this.config = config;
    this.bus = new EventBus();
    this.store = new Neo4jStore(config.neo4j);
    this.net = NeuralNetwork ? new NeuralNetwork({ hiddenLayers: [6, 4] }) : null;
    this.ready = false;
  }

  async init() {
    await this.store.ensureSchema();
    await this.seedGraph();
    this.trainModel();
    this.ready = true;
    return this;
  }

  async seedGraph() {
    const regions = [
      { name: 'Bulbo Raquídeo', layer: 'L1', function: 'Ritmos vitales', latency_ms: 5, compute_model: 'daemon' },
      { name: 'Puente de Varolio', layer: 'L1', function: 'Routing sueño/vigilia', latency_ms: 10, compute_model: 'load_balancer' },
      { name: 'Cerebelo', layer: 'L1', function: 'Corrección motora predictiva', latency_ms: 15, compute_model: 'pid_controller' },
      { name: 'Tálamo', layer: 'L3', function: 'Hub de retransmisión', latency_ms: 25, compute_model: 'router' },
      { name: 'Amígdala', layer: 'L2', function: 'Detección de saliencia', latency_ms: 20, compute_model: 'ids' },
      { name: 'Hipocampo', layer: 'L2', function: 'Memoria episódica', latency_ms: 150, compute_model: 'vector_store' },
      { name: 'Córtex Prefrontal', layer: 'L4', function: 'Función ejecutiva', latency_ms: 400, compute_model: 'hypervisor' },
    ];

    const networks = [
      { name: 'DMN', frequency_hz: 10, state: 'idle' },
      { name: 'CEN', frequency_hz: 40, state: 'focused' },
      { name: 'SN', frequency_hz: 20, state: 'switching' },
    ];

    const modulators = [
      { name: 'Dopamina', source: 'VTA', effect: 'reward_prediction_error' },
      { name: 'Noradrenalina', source: 'Locus Coeruleus', effect: 'signal_to_noise_gain' },
      { name: 'Acetilcolina', source: 'Prosencéfalo Basal', effect: 'attention_encoding' },
      { name: 'Serotonina', source: 'Rafe', effect: 'explore_exploit_balance' },
    ];

    for (const region of regions) await this.store.upsertBrainRegion(region);
    for (const network of networks) await this.store.upsertFunctionalNetwork(network);
    for (const modulator of modulators) await this.store.upsertNeuromodulator(modulator);

    await this.store.attachToNetwork('Córtex Prefrontal', 'CEN');
    await this.store.attachToNetwork('Hipocampo', 'DMN');
    await this.store.attachToNetwork('Amígdala', 'SN');
    await this.store.connectRegions('Bulbo Raquídeo', 'Puente de Varolio', { latency_ms: 5 });
    await this.store.connectRegions('Puente de Varolio', 'Cerebelo', { latency_ms: 10 });
    await this.store.connectRegions('Tálamo', 'Córtex Prefrontal', { latency_ms: 35 });
    await this.store.modulate('Córtex Prefrontal', 'Dopamina', { gain: 1.2 });
    await this.store.modulate('Amígdala', 'Noradrenalina', { gain: 1.4 });
  }

  trainModel() {
    if (!this.net) return;

    const samples = [
      { input: { salience: 0.95, latency: 0.2, reward: 0.4, arousal: 0.9 }, output: { route: 1 } },
      { input: { salience: 0.15, latency: 0.8, reward: 0.1, arousal: 0.2 }, output: { route: 0 } },
      { input: { salience: 0.75, latency: 0.4, reward: 0.8, arousal: 0.7 }, output: { route: 1 } },
      { input: { salience: 0.25, latency: 0.6, reward: 0.2, arousal: 0.3 }, output: { route: 0 } },
    ];

    this.net.train(samples, {
      iterations: 200,
      errorThresh: 0.005,
      log: false,
      learningRate: 0.2,
    });
  }

  computeRoute(payload = {}) {
    if (!this.net) {
      return {
        route: payload.salience > 0.5 ? 'CEN' : 'DMN',
        confidence: 0.5,
        engine: 'rule-fallback',
      };
    }

    const result = this.net.run({
      salience: payload.salience ?? 0,
      latency: payload.latency ?? 0,
      reward: payload.reward ?? 0,
      arousal: payload.arousal ?? 0,
    });

    const route = result.route >= 0.5 ? 'CEN' : 'DMN';
    return {
      route,
      confidence: Math.max(result.route, 1 - result.route),
      raw: result,
      engine: 'brain.js',
    };
  }

  async ingest(eventType, payload = {}, meta = {}) {
    const event = this.bus.publish(eventType, payload, meta);
    await this.store.writeEvent(event);

    if (eventType === 'ATTENTION_SHIFT' || eventType === 'SPIKE' || eventType === 'REWARD_SIGNAL') {
      const decision = this.computeRoute(payload);
      this.bus.publish('ROUTE_DECISION', { ...payload, ...decision }, { derivedFrom: event.id });
    }

    return event;
  }

  async shutdown() {
    await this.store.close();
  }
}

module.exports = { BrainRuntime };
