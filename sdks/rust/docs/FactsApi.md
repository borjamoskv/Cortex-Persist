# \FactsApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**batch_store_v1_facts_batch_post**](FactsApi.md#batch_store_v1_facts_batch_post) | **POST** /v1/facts/batch | Batch Store
[**cast_vote_v1_facts_fact_id_vote_post**](FactsApi.md#cast_vote_v1_facts_fact_id_vote_post) | **POST** /v1/facts/{fact_id}/vote | Cast Vote
[**cast_vote_v2_v1_facts_fact_id_vote_v2_post**](FactsApi.md#cast_vote_v2_v1_facts_fact_id_vote_v2_post) | **POST** /v1/facts/{fact_id}/vote-v2 | Cast Vote V2
[**deprecate_fact_v1_facts_fact_id_delete**](FactsApi.md#deprecate_fact_v1_facts_fact_id_delete) | **DELETE** /v1/facts/{fact_id} | Deprecate Fact
[**get_causal_chain_v1_facts_fact_id_chain_get**](FactsApi.md#get_causal_chain_v1_facts_fact_id_chain_get) | **GET** /v1/facts/{fact_id}/chain | Get Causal Chain
[**get_fact_by_id_v1_facts_fact_id_get**](FactsApi.md#get_fact_by_id_v1_facts_fact_id_get) | **GET** /v1/facts/{fact_id} | Get Fact By Id
[**get_fact_history_v1_facts_fact_id_history_get**](FactsApi.md#get_fact_history_v1_facts_fact_id_history_get) | **GET** /v1/facts/{fact_id}/history | Get Fact History
[**list_all_facts_v1_facts_get**](FactsApi.md#list_all_facts_v1_facts_get) | **GET** /v1/facts | List All Facts
[**list_votes_v1_facts_fact_id_votes_get**](FactsApi.md#list_votes_v1_facts_fact_id_votes_get) | **GET** /v1/facts/{fact_id}/votes | List Votes
[**propagate_taint_v1_facts_fact_id_taint_post**](FactsApi.md#propagate_taint_v1_facts_fact_id_taint_post) | **POST** /v1/facts/{fact_id}/taint | Propagate Taint
[**recall_facts_v1_projects_project_facts_get**](FactsApi.md#recall_facts_v1_projects_project_facts_get) | **GET** /v1/projects/{project}/facts | Recall Facts
[**search_facts_v1_facts_search_post**](FactsApi.md#search_facts_v1_facts_search_post) | **POST** /v1/facts/search | Search Facts
[**store_fact_v1_facts_post**](FactsApi.md#store_fact_v1_facts_post) | **POST** /v1/facts | Store Fact
[**verify_ledger_v1_facts_verify_get**](FactsApi.md#verify_ledger_v1_facts_verify_get) | **GET** /v1/facts/verify | Verify Ledger



## batch_store_v1_facts_batch_post

> std::collections::HashMap<String, serde_json::Value> batch_store_v1_facts_batch_post(batch_store_request, authorization)
Batch Store

Batch store up to 100 facts in a single request.

### Parameters


Name | Type | Description  | Required | Notes
------------- | ------------- | ------------- | ------------- | -------------
**batch_store_request** | [**BatchStoreRequest**](BatchStoreRequest.md) |  | [required] |
**authorization** | Option<**String**> | Bearer <api-key> |  |

### Return type

[**std::collections::HashMap<String, serde_json::Value>**](serde_json::Value.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)


## cast_vote_v1_facts_fact_id_vote_post

> models::VoteResponse cast_vote_v1_facts_fact_id_vote_post(fact_id, vote_request, authorization)
Cast Vote

Cast a consensus vote (verify/dispute) on a fact.

### Parameters


Name | Type | Description  | Required | Notes
------------- | ------------- | ------------- | ------------- | -------------
**fact_id** | **i32** |  | [required] |
**vote_request** | [**VoteRequest**](VoteRequest.md) |  | [required] |
**authorization** | Option<**String**> | Bearer <api-key> |  |

### Return type

[**models::VoteResponse**](VoteResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)


## cast_vote_v2_v1_facts_fact_id_vote_v2_post

> models::VoteResponse cast_vote_v2_v1_facts_fact_id_vote_v2_post(fact_id, vote_v2_request, authorization)
Cast Vote V2

Cast a reputation-weighted consensus vote (RWC).

### Parameters


Name | Type | Description  | Required | Notes
------------- | ------------- | ------------- | ------------- | -------------
**fact_id** | **i32** |  | [required] |
**vote_v2_request** | [**VoteV2Request**](VoteV2Request.md) |  | [required] |
**authorization** | Option<**String**> | Bearer <api-key> |  |

### Return type

[**models::VoteResponse**](VoteResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)


## deprecate_fact_v1_facts_fact_id_delete

> std::collections::HashMap<String, serde_json::Value> deprecate_fact_v1_facts_fact_id_delete(fact_id, authorization)
Deprecate Fact

Soft-deprecate a fact (mark as invalid).

### Parameters


Name | Type | Description  | Required | Notes
------------- | ------------- | ------------- | ------------- | -------------
**fact_id** | **i32** |  | [required] |
**authorization** | Option<**String**> | Bearer <api-key> |  |

### Return type

[**std::collections::HashMap<String, serde_json::Value>**](serde_json::Value.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)


## get_causal_chain_v1_facts_fact_id_chain_get

> Vec<std::collections::HashMap<String, serde_json::Value>> get_causal_chain_v1_facts_fact_id_chain_get(fact_id, direction, max_depth, authorization)
Get Causal Chain

Get the causal chain for a fact (up=ancestors, down=descendants).

### Parameters


Name | Type | Description  | Required | Notes
------------- | ------------- | ------------- | ------------- | -------------
**fact_id** | **i32** |  | [required] |
**direction** | Option<**String**> | 'up' or 'down' |  |[default to down]
**max_depth** | Option<**i32**> |  |  |[default to 10]
**authorization** | Option<**String**> | Bearer <api-key> |  |

### Return type

[**Vec<std::collections::HashMap<String, serde_json::Value>>**](std::collections::HashMap.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)


## get_fact_by_id_v1_facts_fact_id_get

> models::FactResponse get_fact_by_id_v1_facts_fact_id_get(fact_id, authorization)
Get Fact By Id

Get a single fact by ID.

### Parameters


Name | Type | Description  | Required | Notes
------------- | ------------- | ------------- | ------------- | -------------
**fact_id** | **i32** |  | [required] |
**authorization** | Option<**String**> | Bearer <api-key> |  |

### Return type

[**models::FactResponse**](FactResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)


## get_fact_history_v1_facts_fact_id_history_get

> Vec<models::FactResponse> get_fact_history_v1_facts_fact_id_history_get(fact_id, authorization)
Get Fact History

Retrieve version history for a specific fact.

### Parameters


Name | Type | Description  | Required | Notes
------------- | ------------- | ------------- | ------------- | -------------
**fact_id** | **i32** |  | [required] |
**authorization** | Option<**String**> | Bearer <api-key> |  |

### Return type

[**Vec<models::FactResponse>**](FactResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)


## list_all_facts_v1_facts_get

> Vec<models::FactResponse> list_all_facts_v1_facts_get(limit, authorization)
List All Facts

### Parameters


Name | Type | Description  | Required | Notes
------------- | ------------- | ------------- | ------------- | -------------
**limit** | Option<**i32**> |  |  |[default to 50]
**authorization** | Option<**String**> | Bearer <api-key> |  |

### Return type

[**Vec<models::FactResponse>**](FactResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)


## list_votes_v1_facts_fact_id_votes_get

> Vec<std::collections::HashMap<String, serde_json::Value>> list_votes_v1_facts_fact_id_votes_get(fact_id, authorization)
List Votes

Retrieve all votes for a specific fact (Tenant Isolated).

### Parameters


Name | Type | Description  | Required | Notes
------------- | ------------- | ------------- | ------------- | -------------
**fact_id** | **i32** |  | [required] |
**authorization** | Option<**String**> | Bearer <api-key> |  |

### Return type

[**Vec<std::collections::HashMap<String, serde_json::Value>>**](std::collections::HashMap.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)


## propagate_taint_v1_facts_fact_id_taint_post

> std::collections::HashMap<String, serde_json::Value> propagate_taint_v1_facts_fact_id_taint_post(fact_id, authorization)
Propagate Taint

Trigger Ω₁₃ taint propagation from a compromised/invalidated fact.

### Parameters


Name | Type | Description  | Required | Notes
------------- | ------------- | ------------- | ------------- | -------------
**fact_id** | **i32** |  | [required] |
**authorization** | Option<**String**> | Bearer <api-key> |  |

### Return type

[**std::collections::HashMap<String, serde_json::Value>**](serde_json::Value.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)


## recall_facts_v1_projects_project_facts_get

> Vec<models::FactResponse> recall_facts_v1_projects_project_facts_get(project, limit, authorization)
Recall Facts

Recall facts for a specific project with tenant isolation.

### Parameters


Name | Type | Description  | Required | Notes
------------- | ------------- | ------------- | ------------- | -------------
**project** | **String** |  | [required] |
**limit** | Option<**i32**> |  |  |
**authorization** | Option<**String**> | Bearer <api-key> |  |

### Return type

[**Vec<models::FactResponse>**](FactResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)


## search_facts_v1_facts_search_post

> Vec<models::FactResponse> search_facts_v1_facts_search_post(search_memory_request, authorization)
Search Facts

Semantic search across all facts (scoped to tenant).

### Parameters


Name | Type | Description  | Required | Notes
------------- | ------------- | ------------- | ------------- | -------------
**search_memory_request** | [**SearchMemoryRequest**](SearchMemoryRequest.md) |  | [required] |
**authorization** | Option<**String**> | Bearer <api-key> |  |

### Return type

[**Vec<models::FactResponse>**](FactResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)


## store_fact_v1_facts_post

> models::StoreResponse store_fact_v1_facts_post(store_request, authorization)
Store Fact

Store a fact (scoped to authenticated tenant).

### Parameters


Name | Type | Description  | Required | Notes
------------- | ------------- | ------------- | ------------- | -------------
**store_request** | [**StoreRequest**](StoreRequest.md) |  | [required] |
**authorization** | Option<**String**> | Bearer <api-key> |  |

### Return type

[**models::StoreResponse**](StoreResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)


## verify_ledger_v1_facts_verify_get

> std::collections::HashMap<String, serde_json::Value> verify_ledger_v1_facts_verify_get(authorization)
Verify Ledger

Verify cryptographic integrity of the memory ledger.

### Parameters


Name | Type | Description  | Required | Notes
------------- | ------------- | ------------- | ------------- | -------------
**authorization** | Option<**String**> | Bearer <api-key> |  |

### Return type

[**std::collections::HashMap<String, serde_json::Value>**](serde_json::Value.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

