# EventsApi

All URIs are relative to *http://localhost*

| Method | HTTP request | Description |
|------------- | ------------- | -------------|
| [**streamEventsV1EventsStreamGet**](EventsApi.md#streameventsv1eventsstreamget) | **GET** /v1/events/stream | Stream Events |
| [**streamEventsV1PublicEventsStreamGet**](EventsApi.md#streameventsv1publiceventsstreamget) | **GET** /v1/public/events/stream | Stream Events |



## streamEventsV1EventsStreamGet

> any streamEventsV1EventsStreamGet(types, authorization)

Stream Events

Subscribe to CORTEX coordination events via SSE.

### Example

```ts
import {
  Configuration,
  EventsApi,
} from '';
import type { StreamEventsV1EventsStreamGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new EventsApi();

  const body = {
    // string | Comma-separated list of event types (optional)
    types: types_example,
    // string | Bearer <api-key> (optional)
    authorization: authorization_example,
  } satisfies StreamEventsV1EventsStreamGetRequest;

  try {
    const data = await api.streamEventsV1EventsStreamGet(body);
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
| **types** | `string` | Comma-separated list of event types | [Optional] [Defaults to `undefined`] |
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


## streamEventsV1PublicEventsStreamGet

> any streamEventsV1PublicEventsStreamGet()

Stream Events

Server-Sent Events endpoint for real-time CORTEX telemetry.

### Example

```ts
import {
  Configuration,
  EventsApi,
} from '';
import type { StreamEventsV1PublicEventsStreamGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new EventsApi();

  try {
    const data = await api.streamEventsV1PublicEventsStreamGet();
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

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

