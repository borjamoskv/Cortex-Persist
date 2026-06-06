# \SwarmApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**create_worktree_v1_swarm_worktrees_post**](SwarmApi.md#create_worktree_v1_swarm_worktrees_post) | **POST** /v1/swarm/worktrees | Create Worktree
[**delete_worktree_v1_swarm_worktrees_worktree_id_delete**](SwarmApi.md#delete_worktree_v1_swarm_worktrees_worktree_id_delete) | **DELETE** /v1/swarm/worktrees/{worktree_id} | Delete Worktree
[**get_swarm_status_v1_swarm_status_get**](SwarmApi.md#get_swarm_status_v1_swarm_status_get) | **GET** /v1/swarm/status | Get Swarm Status
[**get_worktree_status_v1_swarm_worktrees_worktree_id_get**](SwarmApi.md#get_worktree_status_v1_swarm_worktrees_worktree_id_get) | **GET** /v1/swarm/worktrees/{worktree_id} | Get Worktree Status
[**run_psychohistory_simulation_v1_swarm_psychohistory_post**](SwarmApi.md#run_psychohistory_simulation_v1_swarm_psychohistory_post) | **POST** /v1/swarm/psychohistory | Run Psychohistory Simulation



## create_worktree_v1_swarm_worktrees_post

> models::WorktreeResponse create_worktree_v1_swarm_worktrees_post(worktree_create_request, authorization)
Create Worktree

Provision a new isolated execution environment (Hito 3).

### Parameters


Name | Type | Description  | Required | Notes
------------- | ------------- | ------------- | ------------- | -------------
**worktree_create_request** | [**WorktreeCreateRequest**](WorktreeCreateRequest.md) |  | [required] |
**authorization** | Option<**String**> | Bearer <api-key> |  |

### Return type

[**models::WorktreeResponse**](WorktreeResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)


## delete_worktree_v1_swarm_worktrees_worktree_id_delete

> serde_json::Value delete_worktree_v1_swarm_worktrees_worktree_id_delete(worktree_id, authorization)
Delete Worktree

Cleanly destroy an isolated worktree.

### Parameters


Name | Type | Description  | Required | Notes
------------- | ------------- | ------------- | ------------- | -------------
**worktree_id** | **String** |  | [required] |
**authorization** | Option<**String**> | Bearer <api-key> |  |

### Return type

[**serde_json::Value**](serde_json::Value.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)


## get_swarm_status_v1_swarm_status_get

> models::SwarmStatusResponse get_swarm_status_v1_swarm_status_get(authorization)
Get Swarm Status

Aggregate swarm health and load metrics.

### Parameters


Name | Type | Description  | Required | Notes
------------- | ------------- | ------------- | ------------- | -------------
**authorization** | Option<**String**> | Bearer <api-key> |  |

### Return type

[**models::SwarmStatusResponse**](SwarmStatusResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)


## get_worktree_status_v1_swarm_worktrees_worktree_id_get

> models::WorktreeResponse get_worktree_status_v1_swarm_worktrees_worktree_id_get(worktree_id, authorization)
Get Worktree Status

Get metadata for a specific worktree.

### Parameters


Name | Type | Description  | Required | Notes
------------- | ------------- | ------------- | ------------- | -------------
**worktree_id** | **String** |  | [required] |
**authorization** | Option<**String**> | Bearer <api-key> |  |

### Return type

[**models::WorktreeResponse**](WorktreeResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)


## run_psychohistory_simulation_v1_swarm_psychohistory_post

> serde_json::Value run_psychohistory_simulation_v1_swarm_psychohistory_post(psychohistory_request, authorization)
Run Psychohistory Simulation

Trigger the Psychohistory Fracture Simulator (Hito 4). Orchestrates 50 specialized agents using a Semaphore to calculate catastrophic cascades. Extracts a Byzantine consensus O(1) Contingency Crystal.

### Parameters


Name | Type | Description  | Required | Notes
------------- | ------------- | ------------- | ------------- | -------------
**psychohistory_request** | [**PsychohistoryRequest**](PsychohistoryRequest.md) |  | [required] |
**authorization** | Option<**String**> | Bearer <api-key> |  |

### Return type

[**serde_json::Value**](serde_json::Value.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

