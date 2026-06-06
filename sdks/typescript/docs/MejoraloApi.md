# MejoraloApi

All URIs are relative to *http://localhost*

| Method | HTTP request | Description |
|------------- | ------------- | -------------|
| [**getHistoryV1MejoraloHistoryGet**](MejoraloApi.md#gethistoryv1mejoralohistoryget) | **GET** /v1/mejoralo/history | Get History |
| [**recordSessionV1MejoraloRecordPost**](MejoraloApi.md#recordsessionv1mejoralorecordpost) | **POST** /v1/mejoralo/record | Record Session |
| [**scanProjectV1MejoraloScanPost**](MejoraloApi.md#scanprojectv1mejoraloscanpost) | **POST** /v1/mejoralo/scan | Scan Project |
| [**shipGateV1MejoraloShipPost**](MejoraloApi.md#shipgatev1mejoraloshippost) | **POST** /v1/mejoralo/ship | Ship Gate |



## getHistoryV1MejoraloHistoryGet

> Array&lt;{ [key: string]: any; }&gt; getHistoryV1MejoraloHistoryGet(project, limit, authorization)

Get History

Retrieve MEJORAlo session history for a project.

### Example

```ts
import {
  Configuration,
  MejoraloApi,
} from '';
import type { GetHistoryV1MejoraloHistoryGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new MejoraloApi();

  const body = {
    // string
    project: project_example,
    // number (optional)
    limit: 56,
    // string | Bearer <api-key> (optional)
    authorization: authorization_example,
  } satisfies GetHistoryV1MejoraloHistoryGetRequest;

  try {
    const data = await api.getHistoryV1MejoraloHistoryGet(body);
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
| **project** | `string` |  | [Defaults to `undefined`] |
| **limit** | `number` |  | [Optional] [Defaults to `20`] |
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


## recordSessionV1MejoraloRecordPost

> MejoraloSessionResponse recordSessionV1MejoraloRecordPost(mejoraloSessionRequest, authorization)

Record Session

Record a MEJORAlo audit session in the ledger.

### Example

```ts
import {
  Configuration,
  MejoraloApi,
} from '';
import type { RecordSessionV1MejoraloRecordPostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new MejoraloApi();

  const body = {
    // MejoraloSessionRequest
    mejoraloSessionRequest: ...,
    // string | Bearer <api-key> (optional)
    authorization: authorization_example,
  } satisfies RecordSessionV1MejoraloRecordPostRequest;

  try {
    const data = await api.recordSessionV1MejoraloRecordPost(body);
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
| **mejoraloSessionRequest** | [MejoraloSessionRequest](MejoraloSessionRequest.md) |  | |
| **authorization** | `string` | Bearer &lt;api-key&gt; | [Optional] [Defaults to `undefined`] |

### Return type

[**MejoraloSessionResponse**](MejoraloSessionResponse.md)

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


## scanProjectV1MejoraloScanPost

> MejoraloScanResponse scanProjectV1MejoraloScanPost(mejoraloScanRequest, authorization)

Scan Project

Execute X-Ray 13D scan on a project.

### Example

```ts
import {
  Configuration,
  MejoraloApi,
} from '';
import type { ScanProjectV1MejoraloScanPostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new MejoraloApi();

  const body = {
    // MejoraloScanRequest
    mejoraloScanRequest: ...,
    // string | Bearer <api-key> (optional)
    authorization: authorization_example,
  } satisfies ScanProjectV1MejoraloScanPostRequest;

  try {
    const data = await api.scanProjectV1MejoraloScanPost(body);
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
| **mejoraloScanRequest** | [MejoraloScanRequest](MejoraloScanRequest.md) |  | |
| **authorization** | `string` | Bearer &lt;api-key&gt; | [Optional] [Defaults to `undefined`] |

### Return type

[**MejoraloScanResponse**](MejoraloScanResponse.md)

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


## shipGateV1MejoraloShipPost

> MejoraloShipResponse shipGateV1MejoraloShipPost(mejoraloShipRequest, authorization)

Ship Gate

Validate the 7 Seals for production readiness.

### Example

```ts
import {
  Configuration,
  MejoraloApi,
} from '';
import type { ShipGateV1MejoraloShipPostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new MejoraloApi();

  const body = {
    // MejoraloShipRequest
    mejoraloShipRequest: ...,
    // string | Bearer <api-key> (optional)
    authorization: authorization_example,
  } satisfies ShipGateV1MejoraloShipPostRequest;

  try {
    const data = await api.shipGateV1MejoraloShipPost(body);
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
| **mejoraloShipRequest** | [MejoraloShipRequest](MejoraloShipRequest.md) |  | |
| **authorization** | `string` | Bearer &lt;api-key&gt; | [Optional] [Defaults to `undefined`] |

### Return type

[**MejoraloShipResponse**](MejoraloShipResponse.md)

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

