# \HealthIndexAPI

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**HealthIndexCheckV1HealthCheckGet**](HealthIndexAPI.md#HealthIndexCheckV1HealthCheckGet) | **Get** /v1/health/check | Health Index Check
[**HealthIndexHistoryV1HealthHistoryGet**](HealthIndexAPI.md#HealthIndexHistoryV1HealthHistoryGet) | **Get** /v1/health/history | Health Index History
[**HealthIndexMetricsV1HealthMetricsGet**](HealthIndexAPI.md#HealthIndexMetricsV1HealthMetricsGet) | **Get** /v1/health/metrics | Health Index Metrics
[**HealthIndexPrometheusV1HealthPrometheusGet**](HealthIndexAPI.md#HealthIndexPrometheusV1HealthPrometheusGet) | **Get** /v1/health/prometheus | Health Index Prometheus
[**HealthIndexReportV1HealthReportGet**](HealthIndexAPI.md#HealthIndexReportV1HealthReportGet) | **Get** /v1/health/report | Health Index Report
[**HealthIndexScoreV1HealthScoreGet**](HealthIndexAPI.md#HealthIndexScoreV1HealthScoreGet) | **Get** /v1/health/score | Health Index Score



## HealthIndexCheckV1HealthCheckGet

> map[string]interface{} HealthIndexCheckV1HealthCheckGet(ctx).Execute()

Health Index Check



### Example

```go
package main

import (
	"context"
	"fmt"
	"os"
	openapiclient "github.com/GIT_USER_ID/GIT_REPO_ID/cortex"
)

func main() {

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.HealthIndexAPI.HealthIndexCheckV1HealthCheckGet(context.Background()).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `HealthIndexAPI.HealthIndexCheckV1HealthCheckGet``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `HealthIndexCheckV1HealthCheckGet`: map[string]interface{}
	fmt.Fprintf(os.Stdout, "Response from `HealthIndexAPI.HealthIndexCheckV1HealthCheckGet`: %v\n", resp)
}
```

### Path Parameters

This endpoint does not need any parameter.

### Other Parameters

Other parameters are passed through a pointer to a apiHealthIndexCheckV1HealthCheckGetRequest struct via the builder pattern


### Return type

**map[string]interface{}**

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)


## HealthIndexHistoryV1HealthHistoryGet

> map[string]interface{} HealthIndexHistoryV1HealthHistoryGet(ctx).Limit(limit).Execute()

Health Index History



### Example

```go
package main

import (
	"context"
	"fmt"
	"os"
	openapiclient "github.com/GIT_USER_ID/GIT_REPO_ID/cortex"
)

func main() {
	limit := int32(56) // int32 |  (optional) (default to 20)

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.HealthIndexAPI.HealthIndexHistoryV1HealthHistoryGet(context.Background()).Limit(limit).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `HealthIndexAPI.HealthIndexHistoryV1HealthHistoryGet``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `HealthIndexHistoryV1HealthHistoryGet`: map[string]interface{}
	fmt.Fprintf(os.Stdout, "Response from `HealthIndexAPI.HealthIndexHistoryV1HealthHistoryGet`: %v\n", resp)
}
```

### Path Parameters



### Other Parameters

Other parameters are passed through a pointer to a apiHealthIndexHistoryV1HealthHistoryGetRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **limit** | **int32** |  | [default to 20]

### Return type

**map[string]interface{}**

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)


## HealthIndexMetricsV1HealthMetricsGet

> map[string]interface{} HealthIndexMetricsV1HealthMetricsGet(ctx).Execute()

Health Index Metrics



### Example

```go
package main

import (
	"context"
	"fmt"
	"os"
	openapiclient "github.com/GIT_USER_ID/GIT_REPO_ID/cortex"
)

func main() {

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.HealthIndexAPI.HealthIndexMetricsV1HealthMetricsGet(context.Background()).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `HealthIndexAPI.HealthIndexMetricsV1HealthMetricsGet``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `HealthIndexMetricsV1HealthMetricsGet`: map[string]interface{}
	fmt.Fprintf(os.Stdout, "Response from `HealthIndexAPI.HealthIndexMetricsV1HealthMetricsGet`: %v\n", resp)
}
```

### Path Parameters

This endpoint does not need any parameter.

### Other Parameters

Other parameters are passed through a pointer to a apiHealthIndexMetricsV1HealthMetricsGetRequest struct via the builder pattern


### Return type

**map[string]interface{}**

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)


## HealthIndexPrometheusV1HealthPrometheusGet

> interface{} HealthIndexPrometheusV1HealthPrometheusGet(ctx).Execute()

Health Index Prometheus



### Example

```go
package main

import (
	"context"
	"fmt"
	"os"
	openapiclient "github.com/GIT_USER_ID/GIT_REPO_ID/cortex"
)

func main() {

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.HealthIndexAPI.HealthIndexPrometheusV1HealthPrometheusGet(context.Background()).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `HealthIndexAPI.HealthIndexPrometheusV1HealthPrometheusGet``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `HealthIndexPrometheusV1HealthPrometheusGet`: interface{}
	fmt.Fprintf(os.Stdout, "Response from `HealthIndexAPI.HealthIndexPrometheusV1HealthPrometheusGet`: %v\n", resp)
}
```

### Path Parameters

This endpoint does not need any parameter.

### Other Parameters

Other parameters are passed through a pointer to a apiHealthIndexPrometheusV1HealthPrometheusGetRequest struct via the builder pattern


### Return type

**interface{}**

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)


## HealthIndexReportV1HealthReportGet

> map[string]interface{} HealthIndexReportV1HealthReportGet(ctx).Execute()

Health Index Report



### Example

```go
package main

import (
	"context"
	"fmt"
	"os"
	openapiclient "github.com/GIT_USER_ID/GIT_REPO_ID/cortex"
)

func main() {

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.HealthIndexAPI.HealthIndexReportV1HealthReportGet(context.Background()).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `HealthIndexAPI.HealthIndexReportV1HealthReportGet``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `HealthIndexReportV1HealthReportGet`: map[string]interface{}
	fmt.Fprintf(os.Stdout, "Response from `HealthIndexAPI.HealthIndexReportV1HealthReportGet`: %v\n", resp)
}
```

### Path Parameters

This endpoint does not need any parameter.

### Other Parameters

Other parameters are passed through a pointer to a apiHealthIndexReportV1HealthReportGetRequest struct via the builder pattern


### Return type

**map[string]interface{}**

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)


## HealthIndexScoreV1HealthScoreGet

> map[string]interface{} HealthIndexScoreV1HealthScoreGet(ctx).Execute()

Health Index Score



### Example

```go
package main

import (
	"context"
	"fmt"
	"os"
	openapiclient "github.com/GIT_USER_ID/GIT_REPO_ID/cortex"
)

func main() {

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.HealthIndexAPI.HealthIndexScoreV1HealthScoreGet(context.Background()).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `HealthIndexAPI.HealthIndexScoreV1HealthScoreGet``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `HealthIndexScoreV1HealthScoreGet`: map[string]interface{}
	fmt.Fprintf(os.Stdout, "Response from `HealthIndexAPI.HealthIndexScoreV1HealthScoreGet`: %v\n", resp)
}
```

### Path Parameters

This endpoint does not need any parameter.

### Other Parameters

Other parameters are passed through a pointer to a apiHealthIndexScoreV1HealthScoreGetRequest struct via the builder pattern


### Return type

**map[string]interface{}**

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)

