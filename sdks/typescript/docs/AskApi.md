# AskApi

All URIs are relative to *http://localhost*

| Method | HTTP request | Description |
|------------- | ------------- | -------------|
| [**askCortexV1AskPost**](AskApi.md#askcortexv1askpost) | **POST** /v1/ask | Ask Cortex |
| [**askStreamV1AskStreamPost**](AskApi.md#askstreamv1askstreampost) | **POST** /v1/ask/stream | Ask Stream |
| [**llmStatusV1LlmStatusGet**](AskApi.md#llmstatusv1llmstatusget) | **GET** /v1/llm/status | Llm Status |



## askCortexV1AskPost

> AskResponse askCortexV1AskPost(askRequest, authorization)

Ask Cortex

RAG endpoint: search → synthesize → answer.  Searches CORTEX memory for relevant facts, then uses the configured LLM to synthesize an answer grounded in those facts.  Returns 503 if no LLM provider is configured.

### Example

```ts
import {
  Configuration,
  AskApi,
} from '';
import type { AskCortexV1AskPostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new AskApi();

  const body = {
    // AskRequest
    askRequest: ...,
    // string | Bearer <api-key> (optional)
    authorization: authorization_example,
  } satisfies AskCortexV1AskPostRequest;

  try {
    const data = await api.askCortexV1AskPost(body);
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
| **askRequest** | [AskRequest](AskRequest.md) |  | |
| **authorization** | `string` | Bearer &lt;api-key&gt; | [Optional] [Defaults to `undefined`] |

### Return type

[**AskResponse**](AskResponse.md)

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


## askStreamV1AskStreamPost

> any askStreamV1AskStreamPost(askRequest, authorization)

Ask Stream

Streaming RAG endpoint: search → synthesize → stream answer.  Yields SSE \&#39;data: \&#39; events containing text chunks.

### Example

```ts
import {
  Configuration,
  AskApi,
} from '';
import type { AskStreamV1AskStreamPostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new AskApi();

  const body = {
    // AskRequest
    askRequest: ...,
    // string | Bearer <api-key> (optional)
    authorization: authorization_example,
  } satisfies AskStreamV1AskStreamPostRequest;

  try {
    const data = await api.askStreamV1AskStreamPost(body);
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
| **askRequest** | [AskRequest](AskRequest.md) |  | |
| **authorization** | `string` | Bearer &lt;api-key&gt; | [Optional] [Defaults to `undefined`] |

### Return type

**any**

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


## llmStatusV1LlmStatusGet

> LLMStatusResponse llmStatusV1LlmStatusGet(authorization)

Llm Status

Check LLM provider status and list supported providers. [STATUS]

### Example

```ts
import {
  Configuration,
  AskApi,
} from '';
import type { LlmStatusV1LlmStatusGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new AskApi();

  const body = {
    // string | Bearer <api-key> (optional)
    authorization: authorization_example,
  } satisfies LlmStatusV1LlmStatusGetRequest;

  try {
    const data = await api.llmStatusV1LlmStatusGet(body);
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

[**LLMStatusResponse**](LLMStatusResponse.md)

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

