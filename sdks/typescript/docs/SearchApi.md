# SearchApi

All URIs are relative to *http://localhost*

| Method | HTTP request | Description |
|------------- | ------------- | -------------|
| [**searchFactsGetV1SearchGet**](SearchApi.md#searchfactsgetv1searchget) | **GET** /v1/search | Search Facts Get |
| [**searchFactsV1SearchPost**](SearchApi.md#searchfactsv1searchpost) | **POST** /v1/search | Search Facts |



## searchFactsGetV1SearchGet

> Array&lt;SearchResult&gt; searchFactsGetV1SearchGet(query, k, asOf, graphDepth, includeGraph, authorization)

Search Facts Get

Semantic + Graph-RAG search via GET (scoped to tenant).

### Example

```ts
import {
  Configuration,
  SearchApi,
} from '';
import type { SearchFactsGetV1SearchGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new SearchApi();

  const body = {
    // string
    query: query_example,
    // number (optional)
    k: 56,
    // string (optional)
    asOf: asOf_example,
    // number (optional)
    graphDepth: 56,
    // boolean (optional)
    includeGraph: true,
    // string | Bearer <api-key> (optional)
    authorization: authorization_example,
  } satisfies SearchFactsGetV1SearchGetRequest;

  try {
    const data = await api.searchFactsGetV1SearchGet(body);
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
| **query** | `string` |  | [Defaults to `undefined`] |
| **k** | `number` |  | [Optional] [Defaults to `5`] |
| **asOf** | `string` |  | [Optional] [Defaults to `undefined`] |
| **graphDepth** | `number` |  | [Optional] [Defaults to `0`] |
| **includeGraph** | `boolean` |  | [Optional] [Defaults to `false`] |
| **authorization** | `string` | Bearer &lt;api-key&gt; | [Optional] [Defaults to `undefined`] |

### Return type

[**Array&lt;SearchResult&gt;**](SearchResult.md)

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


## searchFactsV1SearchPost

> Array&lt;SearchResult&gt; searchFactsV1SearchPost(searchRequest, authorization)

Search Facts

Semantic + Graph-RAG search across facts (scoped to tenant).

### Example

```ts
import {
  Configuration,
  SearchApi,
} from '';
import type { SearchFactsV1SearchPostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new SearchApi();

  const body = {
    // SearchRequest
    searchRequest: ...,
    // string | Bearer <api-key> (optional)
    authorization: authorization_example,
  } satisfies SearchFactsV1SearchPostRequest;

  try {
    const data = await api.searchFactsV1SearchPost(body);
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
| **searchRequest** | [SearchRequest](SearchRequest.md) |  | |
| **authorization** | `string` | Bearer &lt;api-key&gt; | [Optional] [Defaults to `undefined`] |

### Return type

[**Array&lt;SearchResult&gt;**](SearchResult.md)

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

