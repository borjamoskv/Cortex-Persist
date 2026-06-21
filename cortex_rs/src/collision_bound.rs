//! Módulo de formalización matemática del límite
//! probabilístico de colisión triádica.
//!
//! NO asume independencia entre espacios.
//! Modela correlación empírica medida.

use std::f64::consts::PI;

/// Parámetros de un modelo de embedding
#[derive(Debug, Clone)]
pub struct EmbeddingModel {
    pub name: String,
    /// Dimensionalidad del espacio latente
    pub dimension: usize,
    /// Umbral de similitud coseno para "colisión"
    pub collision_threshold: f64,
}

/// Correlación medida entre dos espacios de embedding
#[derive(Debug, Clone)]
pub struct SpaceCorrelation {
    pub model_a: String,
    pub model_b: String,
    /// Correlación empírica ∈ [0, 1]
    /// 0 = completamente ortogonal
    /// 1 = isomórfico
    pub correlation: f64,
    /// Tasa de transferencia de colisión medida
    /// "Si colisiona en A, ¿con qué probabilidad
    ///  colisiona en B?"
    pub transfer_rate: f64,
}

/// Resultado del análisis de límite probabilístico
#[derive(Debug)]
pub struct CollisionBound {
    /// P(colisión en modelo individual)
    pub p_single: [f64; 3],
    /// P(colisión simultánea) asumiendo independencia
    pub p_joint_independent: f64,
    /// P(colisión simultánea) con correlación empírica
    pub p_joint_correlated: f64,
    /// Bits de seguridad equivalentes
    pub security_bits: f64,
    /// FLOP estimados para fuerza bruta
    pub estimated_flops: f64,
    /// ¿Es viable para un atacante con presupuesto X?
    pub viability: AttackViability,
}

#[derive(Debug)]
pub enum AttackViability {
    /// Inviable con tecnología actual
    Infeasible { years_at_exaflop: f64 },
    /// Viable para estado-nación
    StateLevel { estimated_cost_usd: f64 },
    /// Viable para atacante individual
    Accessible {
        estimated_cost_usd: f64,
        estimated_hours: f64,
    },
}

pub struct CollisionAnalyzer {
    pub models: Vec<EmbeddingModel>,
    pub correlations: Vec<SpaceCorrelation>,
}

impl Default for CollisionAnalyzer {
    fn default() -> Self {
        Self::new()
    }
}

impl CollisionAnalyzer {
    pub fn new() -> Self {
        Self {
            models: Vec::new(),
            correlations: Vec::new(),
        }
    }

    pub fn add_model(&mut self, model: EmbeddingModel) {
        self.models.push(model);
    }

    pub fn add_correlation(&mut self, correlation: SpaceCorrelation) {
        self.correlations.push(correlation);
    }

    /// Calcular el límite probabilístico de colisión
    /// triádica simultánea.
    ///
    /// Método: Cota geométrica sobre casquetes esféricos
    /// en espacios de alta dimensionalidad.
    pub fn compute_bound(&self) -> CollisionBound {
        assert!(
            self.models.len() == 3,
            "Requiere exactamente 3 modelos para tríada"
        );

        let p_single: [f64; 3] = [
            self.spherical_cap_probability(
                self.models[0].dimension,
                self.models[0].collision_threshold,
            ),
            self.spherical_cap_probability(
                self.models[1].dimension,
                self.models[1].collision_threshold,
            ),
            self.spherical_cap_probability(
                self.models[2].dimension,
                self.models[2].collision_threshold,
            ),
        ];

        let p_joint_independent = p_single[0] * p_single[1] * p_single[2];

        let transfer_12 = self.get_transfer_rate(0, 1);
        let transfer_13 = self.get_transfer_rate(0, 2);
        let transfer_23 = self.get_transfer_rate(1, 2);

        let p_2_given_1 = transfer_12 * p_single[1].sqrt() + (1.0 - transfer_12) * p_single[1];

        let max_transfer = transfer_13.max(transfer_23);
        let p_3_given_12 = max_transfer * p_single[2].sqrt() + (1.0 - max_transfer) * p_single[2];

        let p_joint_correlated = p_single[0] * p_2_given_1 * p_3_given_12;

        let security_bits = if p_joint_correlated > 0.0 {
            -(p_joint_correlated.log2())
        } else {
            f64::INFINITY
        };

        let flops_per_attempt: f64 = self
            .models
            .iter()
            .map(|m| 4.0 * m.dimension as f64 * 128.0)
            .sum();

        let attempts_needed = if p_joint_correlated > 0.0 {
            1.0 / p_joint_correlated
        } else {
            f64::INFINITY
        };

        let estimated_flops = flops_per_attempt * attempts_needed;

        let a100_flops_per_second = 3.12e14;
        let seconds_needed = estimated_flops / a100_flops_per_second;
        let hours_needed = seconds_needed / 3600.0;
        let cost_usd = hours_needed * 2.0;

        let viability = if hours_needed > 8760.0 * 100.0 {
            AttackViability::Infeasible {
                years_at_exaflop: estimated_flops / (1e18 * 3.15e7),
            }
        } else if cost_usd > 1_000_000.0 {
            AttackViability::StateLevel {
                estimated_cost_usd: cost_usd,
            }
        } else {
            AttackViability::Accessible {
                estimated_cost_usd: cost_usd,
                estimated_hours: hours_needed,
            }
        };

        CollisionBound {
            p_single,
            p_joint_independent,
            p_joint_correlated,
            security_bits,
            estimated_flops,
            viability,
        }
    }

    fn spherical_cap_probability(&self, d: usize, tau: f64) -> f64 {
        if tau <= 0.0 {
            return 1.0;
        }
        if tau >= 1.0 {
            return 0.0;
        }

        let d_f = d as f64;
        let theta = tau.acos();

        let sin_theta = theta.sin();
        let cos_theta = theta.cos();

        if sin_theta <= 0.0 {
            return 0.0;
        }

        let log_p = (d_f - 2.0) * sin_theta.ln()
            + 0.5 * (2.0 * PI / ((d_f - 1.0) * cos_theta * cos_theta)).ln()
            - (d_f - 1.0).ln();

        let p = log_p.exp();

        p.min(1.0).max(0.0)
    }

    fn get_transfer_rate(&self, idx_a: usize, idx_b: usize) -> f64 {
        let name_a = &self.models[idx_a].name;
        let name_b = &self.models[idx_b].name;

        self.correlations
            .iter()
            .find(|c| {
                (&c.model_a == name_a && &c.model_b == name_b)
                    || (&c.model_a == name_b && &c.model_b == name_a)
            })
            .map(|c| c.transfer_rate)
            .unwrap_or(0.01)
    }

    pub fn print_analysis(&self, bound: &CollisionBound) {
        println!("═══════════════════════════════════════");
        println!("  ANÁLISIS DE LÍMITE PROBABILÍSTICO");
        println!("  COLISIÓN TRIÁDICA SIMULTÁNEA");
        println!("═══════════════════════════════════════\n");

        println!("Modelos en tríada:");
        for (i, m) in self.models.iter().enumerate() {
            println!(
                "  [{}] {} (d={}, τ={:.2})",
                i, m.name, m.dimension, m.collision_threshold
            );
        }

        println!("\nCorrelaciones empíricas:");
        for c in &self.correlations {
            println!(
                "  {} ↔ {}: ρ={:.4}, transfer={:.4}",
                c.model_a, c.model_b, c.correlation, c.transfer_rate
            );
        }

        println!("\n── Probabilidades de Colisión ──");
        for (i, p) in bound.p_single.iter().enumerate() {
            println!("  P(colisión en modelo {}): {:.2e}", i, p);
        }

        println!(
            "\n  P(conjunta, independencia): {:.2e}",
            bound.p_joint_independent
        );
        println!(
            "  P(conjunta, con correlación): {:.2e}",
            bound.p_joint_correlated
        );
        println!("\n  Bits de seguridad: {:.1}", bound.security_bits);
        println!("  FLOP estimados: {:.2e}", bound.estimated_flops);

        println!("\n── Viabilidad del Ataque ──");
        match &bound.viability {
            AttackViability::Infeasible { years_at_exaflop } => {
                println!("  ✅ INVIABLE");
                println!("  Requiere {:.1} años a 1 ExaFLOP/s", years_at_exaflop);
            }
            AttackViability::StateLevel { estimated_cost_usd } => {
                println!("  ⚠️  VIABLE PARA ESTADO-NACIÓN");
                println!("  Costo estimado: ${:.0}", estimated_cost_usd);
            }
            AttackViability::Accessible {
                estimated_cost_usd,
                estimated_hours,
            } => {
                println!("  ❌ ACCESIBLE");
                println!(
                    "  Costo: ${:.0} ({:.1} horas GPU)",
                    estimated_cost_usd, estimated_hours
                );
            }
        }
    }
}
