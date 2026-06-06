# SovereignGateApi

All URIs are relative to *http://localhost*

| Method | HTTP request | Description |
|------------- | ------------- | -------------|
| [**approveActionV1GateActionIdApprovePost**](SovereignGateApi.md#approveactionv1gateactionidapprovepost) | **POST** /v1/gate/{action_id}/approve | Approve Action |
| [**denyActionV1GateActionIdDenyPost**](SovereignGateApi.md#denyactionv1gateactioniddenypost) | **POST** /v1/gate/{action_id}/deny | Deny Action |
| [**gateStatusV1GateStatusGet**](SovereignGateApi.md#gatestatusv1gatestatusget) | **GET** /v1/gate/status | Gate Status |
| [**getAuditLogV1GateAuditGet**](SovereignGateApi.md#getauditlogv1gateauditget) | **GET** /v1/gate/audit | Get Audit Log |
| [**listPendingV1GatePendingGet**](SovereignGateApi.md#listpendingv1gatependingget) | **GET** /v1/gate/pending | List Pending |



## approveActionV1GateActionIdApprovePost

> GateActionResponse approveActionV1GateActionIdApprovePost(actionId, gateApprovalRequest, authorization)

Approve Action

Approve a pending L3 action with HMAC signature.

### Example

```ts
import {
  Configuration,
  SovereignGateApi,
} from '';
import type { ApproveActionV1GateActionIdApprovePostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new SovereignGateApi();

  const body = {
    // string
    actionId: actionId_example,
    // GateApprovalRequest
    gateApprovalRequest: ...,
    // string | Bearer <api-key> (optional)
    authorization: authorization_example,
  } satisfies ApproveActionV1GateActionIdApprovePostRequest;

  try {
    const data = await api.approveActionV1GateActionIdApprovePost(body);
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
| **actionId** | `string` |  | [Defaults to `undefined`] |
| **gateApprovalRequest** | [GateApprovalRequest](GateApprovalRequest.md) |  | |
| **authorization** | `string` | Bearer &lt;api-key&gt; | [Optional] [Defaults to `undefined`] |

### Return type

[**GateActionResponse**](GateActionResponse.md)

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


## denyActionV1GateActionIdDenyPost

> any denyActionV1GateActionIdDenyPost(actionId, authorization)

Deny Action

Deny a pending L3 action.

### Example

```ts
import {
  Configuration,
  SovereignGateApi,
} from '';
import type { DenyActionV1GateActionIdDenyPostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new SovereignGateApi();

  const body = {
    // string
    actionId: actionId_example,
    // string | Bearer <api-key> (optional)
    authorization: authorization_example,
  } satisfies DenyActionV1GateActionIdDenyPostRequest;

  try {
    const data = await api.denyActionV1GateActionIdDenyPost(body);
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
| **actionId** | `string` |  | [Defaults to `undefined`] |
| **authorization** | `string` | Bearer &lt;api-key&gt; | [Optional] [Defaults to `undefined`] |

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
| **422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## gateStatusV1GateStatusGet

> GateStatusResponse gateStatusV1GateStatusGet(authorization)

Gate Status

Get the current SovereignGate status.

### Example

```ts
import {
  Configuration,
  SovereignGateApi,
} from '';
import type { GateStatusV1GateStatusGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new SovereignGateApi();

  const body = {
    // string | Bearer <api-key> (optional)
    authorization: authorization_example,
  } satisfies GateStatusV1GateStatusGetRequest;

  try {
    const data = await api.gateStatusV1GateStatusGet(body);
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

[**GateStatusResponse**](GateStatusResponse.md)

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


## getAuditLogV1GateAuditGet

> any getAuditLogV1GateAuditGet(limit, authorization)

Get Audit Log

View the SovereignGate audit log.

### Example

```ts
import {
  Configuration,
  SovereignGateApi,
} from '';
import type { GetAuditLogV1GateAuditGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new SovereignGateApi();

  const body = {
    // number (optional)
    limit: 56,
    // string | Bearer <api-key> (optional)
    authorization: authorization_example,
  } satisfies GetAuditLogV1GateAuditGetRequest;

  try {
    const data = await api.getAuditLogV1GateAuditGet(body);
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
| **limit** | `number` |  | [Optional] [Defaults to `50`] |
| **authorization** | `string` | Bearer &lt;api-key&gt; | [Optional] [Defaults to `undefined`] |

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
| **422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## listPendingV1GatePendingGet

> Array&lt;GateActionResponse&gt; listPendingV1GatePendingGet(authorization)

List Pending

List all pending L3 actions awaiting approval.

### Example

```ts
import {
  Configuration,
  SovereignGateApi,
} from '';
import type { ListPendingV1GatePendingGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new SovereignGateApi();

  const body = {
    // string | Bearer <api-key> (optional)
    authorization: authorization_example,
  } satisfies ListPendingV1GatePendingGetRequest;

  try {
    const data = await api.listPendingV1GatePendingGet(body);
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

[**Array&lt;GateActionResponse&gt;**](GateActionResponse.md)

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

