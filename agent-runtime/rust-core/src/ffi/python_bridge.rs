pub mod pb {
    tonic::include_proto!("agent");
}

use pb::policy_service_client::PolicyServiceClient;
use pb::State as GrpcState;
use crate::runtime::state::State;
use crate::runtime::action::Action;
use tonic::transport::Channel;

pub struct PythonBridge {
    client: PolicyServiceClient<Channel>,
}

impl PythonBridge {
    pub async fn new(endpoint: String) -> anyhow::Result<Self> {
        let client = PolicyServiceClient::connect(endpoint).await?;
        Ok(Self { client })
    }

    pub async fn get_actions(&mut self, state: &State) -> anyhow::Result<Vec<Action>> {
        let grpc_state = GrpcState {
            obs_vector: state.obs_vector.clone(),
            blacklist: state.blacklist.clone(),
            step: state.step,
        };

        let request = tonic::Request::new(grpc_state);
        let response = self.client.get_actions(request).await?.into_inner();

        let actions = response.candidates.into_iter().map(|c| Action {
            op: c.op,
            score: c.score,
            expected_value: c.expected_value,
        }).collect();

        Ok(actions)
    }
}
