# UsageApi

All URIs are relative to *http://localhost*

| Method | HTTP request | Description |
|------------- | ------------- | -------------|
| [**getUsageBreakdownV1UsageBreakdownGet**](UsageApi.md#getusagebreakdownv1usagebreakdownget) | **GET** /v1/usage/breakdown | Get Usage Breakdown |
| [**getUsageHistoryV1UsageHistoryGet**](UsageApi.md#getusagehistoryv1usagehistoryget) | **GET** /v1/usage/history | Get Usage History |
| [**getUsageV1UsageGet**](UsageApi.md#getusagev1usageget) | **GET** /v1/usage | Get Usage |



## getUsageBreakdownV1UsageBreakdownGet

> { [key: string]: any; } getUsageBreakdownV1UsageBreakdownGet(authorization)

Get Usage Breakdown

Get per-endpoint breakdown for current month.

### Example

```ts
import {
  Configuration,
  UsageApi,
} from '';
import type { GetUsageBreakdownV1UsageBreakdownGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new UsageApi();

  const body = {
    // string | Bearer <api-key> (optional)
    authorization: authorization_example,
  } satisfies GetUsageBreakdownV1UsageBreakdownGetRequest;

  try {
    const data = await api.getUsageBreakdownV1UsageBreakdownGet(body);
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


## getUsageHistoryV1UsageHistoryGet

> { [key: string]: any; } getUsageHistoryV1UsageHistoryGet(months, authorization)

Get Usage History

Get usage history for the last N months.

### Example

```ts
import {
  Configuration,
  UsageApi,
} from '';
import type { GetUsageHistoryV1UsageHistoryGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new UsageApi();

  const body = {
    // number (optional)
    months: 56,
    // string | Bearer <api-key> (optional)
    authorization: authorization_example,
  } satisfies GetUsageHistoryV1UsageHistoryGetRequest;

  try {
    const data = await api.getUsageHistoryV1UsageHistoryGet(body);
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
| **months** | `number` |  | [Optional] [Defaults to `12`] |
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


## getUsageV1UsageGet

> { [key: string]: any; } getUsageV1UsageGet(authorization)

Get Usage

Get current month\&#39;s API usage for the authenticated tenant.

### Example

```ts
import {
  Configuration,
  UsageApi,
} from '';
import type { GetUsageV1UsageGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new UsageApi();

  const body = {
    // string | Bearer <api-key> (optional)
    authorization: authorization_example,
  } satisfies GetUsageV1UsageGetRequest;

  try {
    const data = await api.getUsageV1UsageGet(body);
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

