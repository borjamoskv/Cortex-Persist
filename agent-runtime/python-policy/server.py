from concurrent import futures
import grpc
import torch
import logging

import pb.agent_pb2 as agent_pb2
import pb.agent_pb2_grpc as agent_pb2_grpc

from policy.model import PolicyNet
from policy.value import ValueNet
from policy.planner import plan

logging.basicConfig(level=logging.INFO)

class PolicyServiceServicer(agent_pb2_grpc.PolicyServiceServicer):
    def __init__(self):
        # State Dim: 128 (Example)
        self.dim = 128
        self.policy_net = PolicyNet(self.dim)
        self.value_net = ValueNet(self.dim)
        self.policy_net.eval()
        self.value_net.eval()

    def GetActions(self, request, context):
        """gRPC handler for Rust requesting action distribution."""
        logging.info(f"Received state vector from Rust (Step {request.step})")
        
        # Convert Rust state vector to PyTorch Tensor
        # Pad or truncate to self.dim for structural consistency
        obs = request.obs_vector
        vec = obs[:self.dim] + [0.0] * max(0, self.dim - len(obs))
        state_tensor = torch.tensor(vec, dtype=torch.float32)

        # Plan using Sanedrín (MCTS + Policy + Value)
        ranked_actions = plan(state_tensor, self.policy_net, self.value_net)
        
        candidates = []
        for op, expected_val in ranked_actions:
            # Emitting pseudo-scores for demonstration
            candidates.append(
                agent_pb2.ActionCandidate(
                    op=op,
                    score=0.9, 
                    expected_value=expected_val
                )
            )

        return agent_pb2.ActionDistribution(candidates=candidates)

    def EvalValue(self, request, context):
        """gRPC handler for Rust requesting epistemic value of a state."""
        obs = request.obs_vector
        vec = obs[:self.dim] + [0.0] * max(0, self.dim - len(obs))
        state_tensor = torch.tensor(vec, dtype=torch.float32)

        with torch.no_grad():
            val = self.value_net(state_tensor).item()

        return agent_pb2.ValueResponse(value=val)

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    agent_pb2_grpc.add_PolicyServiceServicer_to_server(PolicyServiceServicer(), server)
    server.add_insecure_port('[::]:50051')
    logging.info("Policy Server listening on [::]:50051")
    server.start()
    server.wait_for_termination()

if __name__ == '__main__':
    serve()
