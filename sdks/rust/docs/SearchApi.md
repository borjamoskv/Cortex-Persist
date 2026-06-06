# \SearchApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**search_facts_get_v1_search_get**](SearchApi.md#search_facts_get_v1_search_get) | **GET** /v1/search | Search Facts Get
[**search_facts_v1_search_post**](SearchApi.md#search_facts_v1_search_post) | **POST** /v1/search | Search Facts



## search_facts_get_v1_search_get

> Vec<models::SearchResult> search_facts_get_v1_search_get(query, k, as_of, graph_depth, include_graph, authorization)
Search Facts Get

Semantic + Graph-RAG search via GET (scoped to tenant).

### Parameters


Name | Type | Description  | Required | Notes
------------- | ------------- | ------------- | ------------- | -------------
**query** | **String** |  | [required] |
**k** | Option<**i32**> |  |  |[default to 5]
**as_of** | Option<**String**> |  |  |
**graph_depth** | Option<**i32**> |  |  |[default to 0]
**include_graph** | Option<**bool**> |  |  |[default to false]
**authorization** | Option<**String**> | Bearer <api-key> |  |

### Return type

[**Vec<models::SearchResult>**](SearchResult.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)


## search_facts_v1_search_post

> Vec<models::SearchResult> search_facts_v1_search_post(search_request, authorization)
Search Facts

Semantic + Graph-RAG search across facts (scoped to tenant).

### Parameters


Name | Type | Description  | Required | Notes
------------- | ------------- | ------------- | ------------- | -------------
**search_request** | [**SearchRequest**](SearchRequest.md) |  | [required] |
**authorization** | Option<**String**> | Bearer <api-key> |  |

### Return type

[**Vec<models::SearchResult>**](SearchResult.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

