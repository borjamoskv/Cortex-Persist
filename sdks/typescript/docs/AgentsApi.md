# AgentsApi

All URIs are relative to *http://localhost*

| Method | HTTP request | Description |
|------------- | ------------- | -------------|
| [**getAgentV1AgentsAgentIdGet**](AgentsApi.md#getagentv1agentsagentidget) | **GET** /v1/agents/{agent_id} | Get Agent |
| [**listAgentsV1AgentsGet**](AgentsApi.md#listagentsv1agentsget) | **GET** /v1/agents | List Agents |
| [**registerAgentV1AgentsPost**](AgentsApi.md#registeragentv1agentspost) | **POST** /v1/agents | Register Agent |



## getAgentV1AgentsAgentIdGet

> AgentResponse getAgentV1AgentsAgentIdGet(agentId, authorization)

Get Agent

Get agent details and current reputation.

### Example

```ts
import {
  Configuration,
  AgentsApi,
} from '';
import type { GetAgentV1AgentsAgentIdGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new AgentsApi();

  const body = {
    // string
    agentId: agentId_example,
    // string | Bearer <api-key> (optional)
    authorization: authorization_example,
  } satisfies GetAgentV1AgentsAgentIdGetRequest;

  try {
    const data = await api.getAgentV1AgentsAgentIdGet(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters


| Name | Type | Description  | Notes |
|------------- | ------------- | ------------- | -------------|
| **agentId** | `string` |  | [Defaults to `undefined`] |
| **authorization** | `string` | Bearer &lt;api-key&gt; | [Optional] [Defaults to `undefined`] |

### Return type

[**AgentResponse**](AgentResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** | Successful Response |  -  |
| **422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## listAgentsV1AgentsGet

> Array&lt;AgentResponse&gt; listAgentsV1AgentsGet(authorization)

List Agents

List all agents for the current tenant.

### Example

```ts
import {
  Configuration,
  AgentsApi,
} from '';
import type { ListAgentsV1AgentsGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new AgentsApi();

  const body = {
    // string | Bearer <api-key> (optional)
    authorization: authorization_example,
  } satisfies ListAgentsV1AgentsGetRequest;

  try {
    const data = await api.listAgentsV1AgentsGet(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters


| Name | Type | Description  | Notes |
|------------- | ------------- | ------------- | -------------|
| **authorization** | `string` | Bearer &lt;api-key&gt; | [Optional] [Defaults to `undefined`] |

### Return type

[**Array&lt;AgentResponse&gt;**](AgentResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** | Successful Response |  -  |
| **422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## registerAgentV1AgentsPost

> AgentResponse registerAgentV1AgentsPost(agentRegisterRequest, authorization)

Register Agent

Register a new agent for Reputation-Weighted Consensus (Requires Admin).

### Example

```ts
import {
  Configuration,
  AgentsApi,
} from '';
import type { RegisterAgentV1AgentsPostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new AgentsApi();

  const body = {
    // AgentRegisterRequest
    agentRegisterRequest: ...,
    // string | Bearer <api-key> (optional)
    authorization: authorization_example,
  } satisfies RegisterAgentV1AgentsPostRequest;

  try {
    const data = await api.registerAgentV1AgentsPost(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters


| Name | Type | Description  | Notes |
|------------- | ------------- | ------------- | -------------|
| **agentRegisterRequest** | [AgentRegisterRequest](AgentRegisterRequest.md) |  | |
| **authorization** | `string` | Bearer &lt;api-key&gt; | [Optional] [Defaults to `undefined`] |

### Return type

[**AgentResponse**](AgentResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** | Successful Response |  -  |
| **422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

