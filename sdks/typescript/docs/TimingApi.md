# TimingApi

All URIs are relative to *http://localhost*

| Method | HTTP request | Description |
|------------- | ------------- | -------------|
| [**getTimeHistoryV1TimeHistoryGet**](TimingApi.md#gettimehistoryv1timehistoryget) | **GET** /v1/time/history | Get Time History |
| [**recordHeartbeatV1HeartbeatPost**](TimingApi.md#recordheartbeatv1heartbeatpost) | **POST** /v1/heartbeat | Record Heartbeat |
| [**timeReportV1TimeGet**](TimingApi.md#timereportv1timeget) | **GET** /v1/time | Time Report |
| [**timeTodayV1TimeTodayGet**](TimingApi.md#timetodayv1timetodayget) | **GET** /v1/time/today | Time Today |



## getTimeHistoryV1TimeHistoryGet

> Array&lt;any&gt; getTimeHistoryV1TimeHistoryGet(days, authorization)

Get Time History

Get daily time history.

### Example

```ts
import {
  Configuration,
  TimingApi,
} from '';
import type { GetTimeHistoryV1TimeHistoryGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new TimingApi();

  const body = {
    // number (optional)
    days: 56,
    // string | Bearer <api-key> (optional)
    authorization: authorization_example,
  } satisfies GetTimeHistoryV1TimeHistoryGetRequest;

  try {
    const data = await api.getTimeHistoryV1TimeHistoryGet(body);
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
| **days** | `number` |  | [Optional] [Defaults to `7`] |
| **authorization** | `string` | Bearer &lt;api-key&gt; | [Optional] [Defaults to `undefined`] |

### Return type

**Array<any>**

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


## recordHeartbeatV1HeartbeatPost

> { [key: string]: any; } recordHeartbeatV1HeartbeatPost(heartbeatRequest, authorization)

Record Heartbeat

Record an activity heartbeat for automatic time tracking.

### Example

```ts
import {
  Configuration,
  TimingApi,
} from '';
import type { RecordHeartbeatV1HeartbeatPostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new TimingApi();

  const body = {
    // HeartbeatRequest
    heartbeatRequest: ...,
    // string | Bearer <api-key> (optional)
    authorization: authorization_example,
  } satisfies RecordHeartbeatV1HeartbeatPostRequest;

  try {
    const data = await api.recordHeartbeatV1HeartbeatPost(body);
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
| **heartbeatRequest** | [HeartbeatRequest](HeartbeatRequest.md) |  | |
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


## timeReportV1TimeGet

> TimeSummaryResponse timeReportV1TimeGet(project, days, authorization)

Time Report

Get time tracking report for the last N days.

### Example

```ts
import {
  Configuration,
  TimingApi,
} from '';
import type { TimeReportV1TimeGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new TimingApi();

  const body = {
    // string (optional)
    project: project_example,
    // number (optional)
    days: 56,
    // string | Bearer <api-key> (optional)
    authorization: authorization_example,
  } satisfies TimeReportV1TimeGetRequest;

  try {
    const data = await api.timeReportV1TimeGet(body);
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
| **project** | `string` |  | [Optional] [Defaults to `undefined`] |
| **days** | `number` |  | [Optional] [Defaults to `7`] |
| **authorization** | `string` | Bearer &lt;api-key&gt; | [Optional] [Defaults to `undefined`] |

### Return type

[**TimeSummaryResponse**](TimeSummaryResponse.md)

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


## timeTodayV1TimeTodayGet

> TimeSummaryResponse timeTodayV1TimeTodayGet(project, authorization)

Time Today

Get today\&#39;s time tracking summary.

### Example

```ts
import {
  Configuration,
  TimingApi,
} from '';
import type { TimeTodayV1TimeTodayGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new TimingApi();

  const body = {
    // string (optional)
    project: project_example,
    // string | Bearer <api-key> (optional)
    authorization: authorization_example,
  } satisfies TimeTodayV1TimeTodayGetRequest;

  try {
    const data = await api.timeTodayV1TimeTodayGet(body);
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
| **project** | `string` |  | [Optional] [Defaults to `undefined`] |
| **authorization** | `string` | Bearer &lt;api-key&gt; | [Optional] [Defaults to `undefined`] |

### Return type

[**TimeSummaryResponse**](TimeSummaryResponse.md)

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

