# DashboardApi

All URIs are relative to *http://localhost*

| Method | HTTP request | Description |
|------------- | ------------- | -------------|
| [**dashboardDashboardGet**](DashboardApi.md#dashboarddashboardget) | **GET** /dashboard | Dashboard |



## dashboardDashboardGet

> string dashboardDashboardGet()

Dashboard

Serve the embedded memory dashboard.

### Example

```ts
import {
  Configuration,
  DashboardApi,
} from '';
import type { DashboardDashboardGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new DashboardApi();

  try {
    const data = await api.dashboardDashboardGet();
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

**string**

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `text/html`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** | Successful Response |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

