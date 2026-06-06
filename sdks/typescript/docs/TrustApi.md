# TrustApi

All URIs are relative to *http://localhost*

| Method | HTTP request | Description |
|------------- | ------------- | -------------|
| [**dryRunGuardV1TrustGuardPost**](TrustApi.md#dryrunguardv1trustguardpost) | **POST** /v1/trust/guard | Dry Run Guard |
| [**getAgentTrustV1TrustProfilesAgentIdGet**](TrustApi.md#getagenttrustv1trustprofilesagentidget) | **GET** /v1/trust/profiles/{agent_id} | Get Agent Trust |
| [**getComplianceStatusV1TrustComplianceGet**](TrustApi.md#getcompliancestatusv1trustcomplianceget) | **GET** /v1/trust/compliance | Get Compliance Status |



## dryRunGuardV1TrustGuardPost

> { [key: string]: any; } dryRunGuardV1TrustGuardPost(storeRequest, authorization)

Dry Run Guard

Dry-run a store proposal against StorageGuard (Ω₃).  Returns 200 {valid: true} or 400 with specific violation details.

### Example

```ts
import {
  Configuration,
  TrustApi,
} from '';
import type { DryRunGuardV1TrustGuardPostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new TrustApi();

  const body = {
    // StoreRequest
    storeRequest: ...,
    // string | Bearer <api-key> (optional)
    authorization: authorization_example,
  } satisfies DryRunGuardV1TrustGuardPostRequest;

  try {
    const data = await api.dryRunGuardV1TrustGuardPost(body);
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
| **storeRequest** | [StoreRequest](StoreRequest.md) |  | |
| **authorization** | `string` | Bearer &lt;api-key&gt; | [Optional] [Defaults to `undefined`] |

### Return type

**{ [key: string]: any; }**

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


## getAgentTrustV1TrustProfilesAgentIdGet

> TrustProfileResponse getAgentTrustV1TrustProfilesAgentIdGet(agentId, authorization)

Get Agent Trust

Retrieve the Bayesian trust profile for a specific agent.

### Example

```ts
import {
  Configuration,
  TrustApi,
} from '';
import type { GetAgentTrustV1TrustProfilesAgentIdGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new TrustApi();

  const body = {
    // string
    agentId: agentId_example,
    // string | Bearer <api-key> (optional)
    authorization: authorization_example,
  } satisfies GetAgentTrustV1TrustProfilesAgentIdGetRequest;

  try {
    const data = await api.getAgentTrustV1TrustProfilesAgentIdGet(body);
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
| **agentId** | `string` |  | [Defaults to `undefined`] |
| **authorization** | `string` | Bearer &lt;api-key&gt; | [Optional] [Defaults to `undefined`] |

### Return type

[**TrustProfileResponse**](TrustProfileResponse.md)

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


## getComplianceStatusV1TrustComplianceGet

> ComplianceReport getComplianceStatusV1TrustComplianceGet(authorization)

Get Compliance Status

Generate aggregate compliance report (EU AI Act Art 12).

### Example

```ts
import {
  Configuration,
  TrustApi,
} from '';
import type { GetComplianceStatusV1TrustComplianceGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new TrustApi();

  const body = {
    // string | Bearer <api-key> (optional)
    authorization: authorization_example,
  } satisfies GetComplianceStatusV1TrustComplianceGetRequest;

  try {
    const data = await api.getComplianceStatusV1TrustComplianceGet(body);
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

[**ComplianceReport**](ComplianceReport.md)

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

