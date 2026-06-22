import logging

import torch
import torch.nn.functional as F

logger = logging.getLogger(__name__)

# ==============================================================================
# C5-REAL: AUTODIDACT DEEP PROBABILITY PRIMITIVES (BLOCK 3)
# ==============================================================================
# This module implements the foundational concepts of probability and Bayesian
# inference as deterministic, high-exergy functions within MOSKV-1 APEX.
# ==============================================================================

# 21. INFERENCIA BAYESIANA (Bayesian Inference)
def bayesian_update(prior: torch.Tensor, likelihood: torch.Tensor) -> torch.Tensor:
    """
    Computes the posterior distribution using Bayes' Theorem.
    prior and likelihood must be aligned discrete probability tensors.
    """
    unnormalized_posterior = prior * likelihood
    evidence = torch.sum(unnormalized_posterior)
    if evidence < 1e-12:
        return prior
    return unnormalized_posterior / evidence

# 22. DISTRIBUCIÓN DE DIRICHLET (Dirichlet Distribution)
def sample_dirichlet(concentration: torch.Tensor, num_samples: int = 1) -> torch.Tensor:
    """
    Samples from a Dirichlet distribution.
    """
    m = torch.distributions.Dirichlet(concentration)
    return m.sample((num_samples,))

# 23. PROCESO GAUSSIANO (Gaussian Process)
def rbf_kernel(x1: torch.Tensor, x2: torch.Tensor, length_scale: float = 1.0) -> torch.Tensor:
    """
    Computes the RBF (Squared Exponential) kernel between two sets of points.
    """
    dist_sq = torch.cdist(x1, x2, p=2) ** 2
    return torch.exp(-0.5 * dist_sq / (length_scale ** 2))

def gp_posterior(X_train: torch.Tensor, Y_train: torch.Tensor, X_test: torch.Tensor, sigma_y: float = 1e-5) -> tuple[torch.Tensor, torch.Tensor]:
    """
    Computes the GP posterior mean and covariance for test points.
    """
    K = rbf_kernel(X_train, X_train) + sigma_y**2 * torch.eye(X_train.shape[0])
    K_s = rbf_kernel(X_train, X_test)
    K_ss = rbf_kernel(X_test, X_test)
    
    L = torch.linalg.cholesky(K)
    alpha = torch.cholesky_solve(Y_train, L)
    
    mu_post = K_s.T @ alpha
    v = torch.linalg.solve_triangular(L, K_s, upper=False)
    cov_post = K_ss - v.T @ v
    return mu_post, cov_post

# 24. CADENAS DE MARKOV (Markov Chains)
def markov_chain_step(state: torch.Tensor, transition_matrix: torch.Tensor) -> torch.Tensor:
    """
    Advances a discrete Markov chain by one step. P(t+1) = P(t) @ T
    """
    return state @ transition_matrix

# 25. MCMC - MONTE CARLO MARKOV CHAIN (Metropolis-Hastings)
def metropolis_hastings_step(current_x: float, target_pdf, proposal_std: float = 1.0) -> float:
    """
    Performs a single step of the Metropolis-Hastings algorithm.
    """
    proposed_x = current_x + torch.randn(1).item() * proposal_std
    p_current = target_pdf(current_x)
    p_proposed = target_pdf(proposed_x)
    
    acceptance_ratio = p_proposed / (p_current + 1e-12)
    if torch.rand(1).item() < acceptance_ratio:
        return proposed_x
    return current_x

# 26. DIVERGENCIA KL (Kullback-Leibler Divergence)
def compute_kl_divergence(p: torch.Tensor, q: torch.Tensor) -> torch.Tensor:
    """
    Computes the KL divergence D_KL(P || Q) for discrete distributions.
    Expects p and q to be probability distributions (sum to 1).
    """
    p = torch.clamp(p, 1e-12, 1.0)
    q = torch.clamp(q, 1e-12, 1.0)
    return torch.sum(p * torch.log(p / q))

# 27. INFORMACIÓN MUTUA (Mutual Information)
def compute_mutual_information(joint_pq: torch.Tensor) -> torch.Tensor:
    """
    Computes Mutual Information I(X;Y) from a joint probability matrix.
    """
    p_x = torch.sum(joint_pq, dim=1, keepdim=True)
    p_y = torch.sum(joint_pq, dim=0, keepdim=True)
    p_x_y = p_x @ p_y
    
    joint_clamped = torch.clamp(joint_pq, 1e-12, 1.0)
    p_x_y_clamped = torch.clamp(p_x_y, 1e-12, 1.0)
    return torch.sum(joint_clamped * torch.log(joint_clamped / p_x_y_clamped))

# 28. ENTROPÍA DE SHANNON (Shannon Entropy)
def compute_shannon_entropy(p: torch.Tensor) -> torch.Tensor:
    """
    Computes Shannon Entropy H(X) = -sum(P(x) * log(P(x))).
    """
    p_clamped = torch.clamp(p, 1e-12, 1.0)
    return -torch.sum(p_clamped * torch.log2(p_clamped))

# 29. DISTRIBUCIÓN DE LAPLACE (Laplace Distribution)
def sample_laplace(loc: torch.Tensor, scale: torch.Tensor, num_samples: int = 1) -> torch.Tensor:
    """
    Samples from a Laplace distribution (L1 regularization prior).
    """
    m = torch.distributions.Laplace(loc, scale)
    return m.sample((num_samples,))

# 30. FUNCIÓN DE PARTICIÓN (Partition Function - Statistical Mechanics)
def compute_partition_function(energies: torch.Tensor, temperature: float = 1.0) -> torch.Tensor:
    """
    Computes the partition function Z = sum(exp(-E_i / T)).
    """
    return torch.sum(torch.exp(-energies / temperature))

# 31. ESTIMACIÓN MÁXIMA VEROSIMILITUD (MLE)
def maximum_likelihood_estimation(log_likelihood_fn, params: torch.Tensor, lr: float=0.01, steps: int=100) -> torch.Tensor:
    """
    Maximizes log-likelihood using gradient ascent.
    """
    params = params.clone().requires_grad_(True)
    optimizer = torch.optim.SGD([params], lr=lr)
    for _ in range(steps):
        optimizer.zero_grad()
        loss = -log_likelihood_fn(params)
        loss.backward()
        optimizer.step()
    return params.detach()

# 32. ESTIMACIÓN MAP (Maximum A Posteriori)
def maximum_a_posteriori(log_likelihood_fn, log_prior_fn, params: torch.Tensor, lr: float=0.01, steps: int=100) -> torch.Tensor:
    """
    Maximizes log-posterior (log-likelihood + log-prior).
    """
    params = params.clone().requires_grad_(True)
    optimizer = torch.optim.SGD([params], lr=lr)
    for _ in range(steps):
        optimizer.zero_grad()
        # Maximize posterior -> minimize negative posterior
        loss = -(log_likelihood_fn(params) + log_prior_fn(params))
        loss.backward()
        optimizer.step()
    return params.detach()

# 33. VARIABLES LATENTES (Reparameterization Trick)
def reparameterize_latent(mu: torch.Tensor, log_var: torch.Tensor) -> torch.Tensor:
    """
    Applies the VAE reparameterization trick: z = mu + epsilon * sigma
    """
    std = torch.exp(0.5 * log_var)
    eps = torch.randn_like(std)
    return mu + eps * std

# 34. ALGORITMO EM (Expectation-Maximization) - Simplified 1D GMM
def em_algorithm_1d_gmm(data: torch.Tensor, steps: int = 10) -> tuple[torch.Tensor, torch.Tensor]:
    """
    A minimal EM algorithm for a 1D Gaussian Mixture Model with 2 components.
    Returns (means, standard_deviations).
    """
    # Initialize parameters
    mu1, mu2 = torch.min(data).item(), torch.max(data).item()
    std1, std2 = 1.0, 1.0
    pi1 = 0.5
    
    for _ in range(steps):
        # E-step: Responsibilities
        p1 = pi1 * torch.exp(-0.5 * ((data - mu1)/std1)**2) / std1
        p2 = (1 - pi1) * torch.exp(-0.5 * ((data - mu2)/std2)**2) / std2
        gamma1 = p1 / (p1 + p2 + 1e-12)
        gamma2 = 1.0 - gamma1
        
        # M-step: Update parameters
        N1, N2 = torch.sum(gamma1), torch.sum(gamma2)
        pi1 = (N1 / len(data)).item()
        mu1 = (torch.sum(gamma1 * data) / N1).item()
        mu2 = (torch.sum(gamma2 * data) / N2).item()
        std1 = torch.sqrt(torch.sum(gamma1 * (data - mu1)**2) / N1).clamp(min=1e-3).item()
        std2 = torch.sqrt(torch.sum(gamma2 * (data - mu2)**2) / N2).clamp(min=1e-3).item()
        
    return torch.tensor([mu1, mu2]), torch.tensor([std1, std2])

# 35. TEOREMA DE BAYES JERÁRQUICO (Hierarchical Bayes)
def hierarchical_bayes_prior(hyper_alpha: torch.Tensor, data_size: int) -> torch.Tensor:
    """
    Demonstrates a hierarchical prior: hyper-parameters dictate the prior of parameters.
    e.g. hyper_alpha (Dirichlet) -> theta (Categorical)
    """
    theta_prior = sample_dirichlet(hyper_alpha, num_samples=1).squeeze(0)
    return theta_prior

# ==============================================================================
# EXECUTION & DIAGNOSTICS (C5-REAL VALIDATION)
# ==============================================================================
if __name__ == "__main__":
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
    
    logger.info(">> MOSKV-1 APEX: INITIALIZING C5-REAL PROBABILITY PRIMITIVES (BLOCK 3) <<\n")

    logger.info("--- 21. Bayesian Inference ---")
    prior = torch.tensor([0.2, 0.8])
    likelihood = torch.tensor([0.9, 0.4])
    posterior = bayesian_update(prior, likelihood)
    logger.info(f"Posterior: {posterior.tolist()}")

    logger.info("\n--- 26. KL Divergence & 28. Shannon Entropy ---")
    entropy = compute_shannon_entropy(posterior)
    kl_div = compute_kl_divergence(posterior, prior)
    logger.info(f"Shannon Entropy H(posterior): {entropy.item():.4f} bits")
    logger.info(f"KL Divergence D_KL(posterior || prior): {kl_div.item():.4f} nats")

    logger.info("\n--- 27. Mutual Information ---")
    joint_p = torch.tensor([[0.4, 0.1], [0.1, 0.4]])
    mi = compute_mutual_information(joint_p)
    logger.info(f"Mutual Information: {mi.item():.4f} nats")

    logger.info("\n--- 30. Partition Function ---")
    energies = torch.tensor([1.0, 2.0, 3.0])
    Z = compute_partition_function(energies, temperature=1.5)
    logger.info(f"Partition Function Z: {Z.item():.4f}")

    logger.info("\n--- 33. Latent Reparameterization (VAE) ---")
    mu = torch.tensor([0.0, 0.0])
    log_var = torch.tensor([-1.0, -1.0])
    z = reparameterize_latent(mu, log_var)
    logger.info(f"Sampled Latent z: {z.tolist()}")

    logger.info("\n--- 34. EM Algorithm (1D GMM) ---")
    # Generate bimodal data
    d1 = torch.randn(100) - 5.0
    d2 = torch.randn(100) + 5.0
    data = torch.cat([d1, d2])
    means, stds = em_algorithm_1d_gmm(data, steps=15)
    logger.info(f"EM Estimated Means: {means.tolist()}")
    logger.info(f"EM Estimated Stds: {stds.tolist()}")

    logger.info("\n>> C5-REAL DIAGNOSTICS COMPLETE: ZERO ANERGIA. <<")
