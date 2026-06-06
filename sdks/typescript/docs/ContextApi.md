# ContextApi

All URIs are relative to *http://localhost*

| Method | HTTP request | Description |
|------------- | ------------- | -------------|
| [**contextHistoryV1ContextHistoryGet**](ContextApi.md#contexthistoryv1contexthistoryget) | **GET** /v1/context/history | Context History |
| [**inferContextV1ContextInferGet**](ContextApi.md#infercontextv1contextinferget) | **GET** /v1/context/infer | Infer Context |
| [**listSignalsV1ContextSignalsGet**](ContextApi.md#listsignalsv1contextsignalsget) | **GET** /v1/context/signals | List Signals |



## contextHistoryV1ContextHistoryGet

> Array&lt;{ [key: string]: any; }&gt; contextHistoryV1ContextHistoryGet(limit, authorization)

Context History

Retrieve past context inference snapshots.

### Example

```ts
import {
  Configuration,
  ContextApi,
} from '';
import type { ContextHistoryV1ContextHistoryGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new ContextApi();

  const body = {
    // number (optional)
    limit: 56,
    // string | Bearer <api-key> (optional)
    authorization: authorization_example,
  } satisfies ContextHistoryV1ContextHistoryGetRequest;

  try {
    const data = await api.contextHistoryV1ContextHistoryGet(body);
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
| **limit** | `number` |  | [Optional] [Defaults to `10`] |
| **authorization** | `string` | Bearer &lt;api-key&gt; | [Optional] [Defaults to `undefined`] |

### Return type

**Array<{ [key: string]: any; }>**

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


## inferContextV1ContextInferGet

> ContextSnapshotResponse inferContextV1ContextInferGet(persist, authorization)

Infer Context

Run ambient context inference and return the current context snapshot.

### Example

```ts
import {
  Configuration,
  ContextApi,
} from '';
import type { InferContextV1ContextInferGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new ContextApi();

  const body = {
    // boolean | Persist snapshot to DB (optional)
    persist: true,
    // string | Bearer <api-key> (optional)
    authorization: authorization_example,
  } satisfies InferContextV1ContextInferGetRequest;

  try {
    const data = await api.inferContextV1ContextInferGet(body);
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
| **persist** | `boolean` | Persist snapshot to DB | [Optional] [Defaults to `true`] |
| **authorization** | `string` | Bearer &lt;api-key&gt; | [Optional] [Defaults to `undefined`] |

### Return type

[**ContextSnapshotResponse**](ContextSnapshotResponse.md)

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


## listSignalsV1ContextSignalsGet

> Array&lt;ContextSignalModel&gt; listSignalsV1ContextSignalsGet(authorization)

List Signals

List raw ambient signals without running inference.

### Example

```ts
import {
  Configuration,
  ContextApi,
} from '';
import type { ListSignalsV1ContextSignalsGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new ContextApi();

  const body = {
    // string | Bearer <api-key> (optional)
    authorization: authorization_example,
  } satisfies ListSignalsV1ContextSignalsGetRequest;

  try {
    const data = await api.listSignalsV1ContextSignalsGet(body);
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

[**Array&lt;ContextSignalModel&gt;**](ContextSignalModel.md)

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

