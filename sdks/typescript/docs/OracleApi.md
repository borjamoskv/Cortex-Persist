# OracleApi

All URIs are relative to *http://localhost*

| Method | HTTP request | Description |
|------------- | ------------- | -------------|
| [**auditTargetV1OracleAuditPost**](OracleApi.md#audittargetv1oracleauditpost) | **POST** /v1/oracle/audit | Audit Target |



## auditTargetV1OracleAuditPost

> OracleResponse auditTargetV1OracleAuditPost(oracleRequest, authorization)

Audit Target

The Oracle: Run a Sovereign Agent audit. Requires a valid CORTEX API Key (provisioned via Stripe subscription).

### Example

```ts
import {
  Configuration,
  OracleApi,
} from '';
import type { AuditTargetV1OracleAuditPostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new OracleApi();

  const body = {
    // OracleRequest
    oracleRequest: ...,
    // string | Bearer <api-key> (optional)
    authorization: authorization_example,
  } satisfies AuditTargetV1OracleAuditPostRequest;

  try {
    const data = await api.auditTargetV1OracleAuditPost(body);
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
| **oracleRequest** | [OracleRequest](OracleRequest.md) |  | |
| **authorization** | `string` | Bearer &lt;api-key&gt; | [Optional] [Defaults to `undefined`] |

### Return type

[**OracleResponse**](OracleResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** | Successful Response |  -  |
| **500** | Oracle yielded no insights. |  -  |
| **502** | Oracle Engine Error: LLM provider is failing. |  -  |
| **503** | The Oracle is currently disconnected from the LLM core. |  -  |
| **422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

