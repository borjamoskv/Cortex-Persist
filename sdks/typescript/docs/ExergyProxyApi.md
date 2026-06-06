# ExergyProxyApi

All URIs are relative to *http://localhost*

| Method | HTTP request | Description |
|------------- | ------------- | -------------|
| [**proxyChatCompletionsLlmProxyV1ChatCompletionsPost**](ExergyProxyApi.md#proxychatcompletionsllmproxyv1chatcompletionspost) | **POST** /llm-proxy/v1/chat/completions | Proxy Chat Completions |



## proxyChatCompletionsLlmProxyV1ChatCompletionsPost

> any proxyChatCompletionsLlmProxyV1ChatCompletionsPost()

Proxy Chat Completions

OpenAI-compatible Chat Completions endpoint. Passes the output through the Deterministic Labyrinth (Exergy Filter).

### Example

```ts
import {
  Configuration,
  ExergyProxyApi,
} from '';
import type { ProxyChatCompletionsLlmProxyV1ChatCompletionsPostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new ExergyProxyApi();

  try {
    const data = await api.proxyChatCompletionsLlmProxyV1ChatCompletionsPost();
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters

This endpoint does not need any parameter.

### Return type

**any**

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** | Successful Response |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

