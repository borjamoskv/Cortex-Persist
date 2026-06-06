# RuntimeApi

All URIs are relative to *http://localhost*

| Method | HTTP request | Description |
|------------- | ------------- | -------------|
| [**getBootRecoveryV1RuntimeBootRecoveryGet**](RuntimeApi.md#getbootrecoveryv1runtimebootrecoveryget) | **GET** /v1/runtime/boot_recovery | Get Boot Recovery |
| [**getHealthV1RuntimeHealthGet**](RuntimeApi.md#gethealthv1runtimehealthget) | **GET** /v1/runtime/health | Get Health |



## getBootRecoveryV1RuntimeBootRecoveryGet

> RecoveryReport getBootRecoveryV1RuntimeBootRecoveryGet()

Get Boot Recovery

Get the memory recovery report generated during boot.

### Example

```ts
import {
  Configuration,
  RuntimeApi,
} from '';
import type { GetBootRecoveryV1RuntimeBootRecoveryGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new RuntimeApi();

  try {
    const data = await api.getBootRecoveryV1RuntimeBootRecoveryGet();
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

[**RecoveryReport**](RecoveryReport.md)

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


## getHealthV1RuntimeHealthGet

> { [key: string]: any; } getHealthV1RuntimeHealthGet()

Get Health

Retrieve runtime health report.

### Example

```ts
import {
  Configuration,
  RuntimeApi,
} from '';
import type { GetHealthV1RuntimeHealthGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new RuntimeApi();

  try {
    const data = await api.getHealthV1RuntimeHealthGet();
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

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

