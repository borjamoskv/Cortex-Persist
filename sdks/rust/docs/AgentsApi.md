# \AgentsApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**get_agent_v1_agents_agent_id_get**](AgentsApi.md#get_agent_v1_agents_agent_id_get) | **GET** /v1/agents/{agent_id} | Get Agent
[**list_agents_v1_agents_get**](AgentsApi.md#list_agents_v1_agents_get) | **GET** /v1/agents | List Agents
[**register_agent_v1_agents_post**](AgentsApi.md#register_agent_v1_agents_post) | **POST** /v1/agents | Register Agent



## get_agent_v1_agents_agent_id_get

> models::AgentResponse get_agent_v1_agents_agent_id_get(agent_id, authorization)
Get Agent

Get agent details and current reputation.

### Parameters


Name | Type | Description  | Required | Notes
------------- | ------------- | ------------- | ------------- | -------------
**agent_id** | **String** |  | [required] |
**authorization** | Option<**String**> | Bearer <api-key> |  |

### Return type

[**models::AgentResponse**](AgentResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)


## list_agents_v1_agents_get

> Vec<models::AgentResponse> list_agents_v1_agents_get(authorization)
List Agents

List all agents for the current tenant.

### Parameters


Name | Type | Description  | Required | Notes
------------- | ------------- | ------------- | ------------- | -------------
**authorization** | Option<**String**> | Bearer <api-key> |  |

### Return type

[**Vec<models::AgentResponse>**](AgentResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)


## register_agent_v1_agents_post

> models::AgentResponse register_agent_v1_agents_post(agent_register_request, authorization)
Register Agent

Register a new agent for Reputation-Weighted Consensus (Requires Admin).

### Parameters


Name | Type | Description  | Required | Notes
------------- | ------------- | ------------- | ------------- | -------------
**agent_register_request** | [**AgentRegisterRequest**](AgentRegisterRequest.md) |  | [required] |
**authorization** | Option<**String**> | Bearer <api-key> |  |

### Return type

[**models::AgentResponse**](AgentResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

