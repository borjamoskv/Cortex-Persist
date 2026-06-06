# \AskApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**ask_cortex_v1_ask_post**](AskApi.md#ask_cortex_v1_ask_post) | **POST** /v1/ask | Ask Cortex
[**ask_stream_v1_ask_stream_post**](AskApi.md#ask_stream_v1_ask_stream_post) | **POST** /v1/ask/stream | Ask Stream
[**llm_status_v1_llm_status_get**](AskApi.md#llm_status_v1_llm_status_get) | **GET** /v1/llm/status | Llm Status



## ask_cortex_v1_ask_post

> models::AskResponse ask_cortex_v1_ask_post(ask_request, authorization)
Ask Cortex

RAG endpoint: search → synthesize → answer.  Searches CORTEX memory for relevant facts, then uses the configured LLM to synthesize an answer grounded in those facts.  Returns 503 if no LLM provider is configured.

### Parameters


Name | Type | Description  | Required | Notes
------------- | ------------- | ------------- | ------------- | -------------
**ask_request** | [**AskRequest**](AskRequest.md) |  | [required] |
**authorization** | Option<**String**> | Bearer <api-key> |  |

### Return type

[**models::AskResponse**](AskResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)


## ask_stream_v1_ask_stream_post

> serde_json::Value ask_stream_v1_ask_stream_post(ask_request, authorization)
Ask Stream

Streaming RAG endpoint: search → synthesize → stream answer.  Yields SSE 'data: ' events containing text chunks.

### Parameters


Name | Type | Description  | Required | Notes
------------- | ------------- | ------------- | ------------- | -------------
**ask_request** | [**AskRequest**](AskRequest.md) |  | [required] |
**authorization** | Option<**String**> | Bearer <api-key> |  |

### Return type

[**serde_json::Value**](serde_json::Value.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)


## llm_status_v1_llm_status_get

> models::LlmStatusResponse llm_status_v1_llm_status_get(authorization)
Llm Status

Check LLM provider status and list supported providers. [STATUS]

### Parameters


Name | Type | Description  | Required | Notes
------------- | ------------- | ------------- | ------------- | -------------
**authorization** | Option<**String**> | Bearer <api-key> |  |

### Return type

[**models::LlmStatusResponse**](LLMStatusResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

