# DaemonApi

All URIs are relative to *http://localhost*

| Method | HTTP request | Description |
|------------- | ------------- | -------------|
| [**daemonStatusV1DaemonStatusGet**](DaemonApi.md#daemonstatusv1daemonstatusget) | **GET** /v1/daemon/status | Daemon Status |



## daemonStatusV1DaemonStatusGet

> { [key: string]: any; } daemonStatusV1DaemonStatusGet(authorization)

Daemon Status

Get last daemon watchdog check results.

### Example

```ts
import {
  Configuration,
  DaemonApi,
} from '';
import type { DaemonStatusV1DaemonStatusGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new DaemonApi();

  const body = {
    // string | Bearer <api-key> (optional)
    authorization: authorization_example,
  } satisfies DaemonStatusV1DaemonStatusGetRequest;

  try {
    const data = await api.daemonStatusV1DaemonStatusGet(body);
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

**{ [key: string]: any; }**

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

