# \ExergyProxyApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**proxy_chat_completions_llm_proxy_v1_chat_completions_post**](ExergyProxyApi.md#proxy_chat_completions_llm_proxy_v1_chat_completions_post) | **POST** /llm-proxy/v1/chat/completions | Proxy Chat Completions



## proxy_chat_completions_llm_proxy_v1_chat_completions_post

> serde_json::Value proxy_chat_completions_llm_proxy_v1_chat_completions_post()
Proxy Chat Completions

OpenAI-compatible Chat Completions endpoint. Passes the output through the Deterministic Labyrinth (Exergy Filter).

### Parameters

This endpoint does not need any parameter.

### Return type

[**serde_json::Value**](serde_json::Value.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

