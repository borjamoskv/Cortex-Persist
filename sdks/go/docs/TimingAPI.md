# \TimingAPI

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**GetTimeHistoryV1TimeHistoryGet**](TimingAPI.md#GetTimeHistoryV1TimeHistoryGet) | **Get** /v1/time/history | Get Time History
[**RecordHeartbeatV1HeartbeatPost**](TimingAPI.md#RecordHeartbeatV1HeartbeatPost) | **Post** /v1/heartbeat | Record Heartbeat
[**TimeReportV1TimeGet**](TimingAPI.md#TimeReportV1TimeGet) | **Get** /v1/time | Time Report
[**TimeTodayV1TimeTodayGet**](TimingAPI.md#TimeTodayV1TimeTodayGet) | **Get** /v1/time/today | Time Today



## GetTimeHistoryV1TimeHistoryGet

> []interface{} GetTimeHistoryV1TimeHistoryGet(ctx).Days(days).Authorization(authorization).Execute()

Get Time History



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
	days := int32(56) // int32 |  (optional) (default to 7)
	authorization := "authorization_example" // string | Bearer <api-key> (optional)

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.TimingAPI.GetTimeHistoryV1TimeHistoryGet(context.Background()).Days(days).Authorization(authorization).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `TimingAPI.GetTimeHistoryV1TimeHistoryGet``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `GetTimeHistoryV1TimeHistoryGet`: []interface{}
	fmt.Fprintf(os.Stdout, "Response from `TimingAPI.GetTimeHistoryV1TimeHistoryGet`: %v\n", resp)
}
```

### Path Parameters



### Other Parameters

Other parameters are passed through a pointer to a apiGetTimeHistoryV1TimeHistoryGetRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **days** | **int32** |  | [default to 7]
 **authorization** | **string** | Bearer &lt;api-key&gt; | 

### Return type

**[]interface{}**

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)


## RecordHeartbeatV1HeartbeatPost

> map[string]interface{} RecordHeartbeatV1HeartbeatPost(ctx).HeartbeatRequest(heartbeatRequest).Authorization(authorization).Execute()

Record Heartbeat



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
	heartbeatRequest := *openapiclient.NewHeartbeatRequest("Project_example") // HeartbeatRequest | 
	authorization := "authorization_example" // string | Bearer <api-key> (optional)

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.TimingAPI.RecordHeartbeatV1HeartbeatPost(context.Background()).HeartbeatRequest(heartbeatRequest).Authorization(authorization).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `TimingAPI.RecordHeartbeatV1HeartbeatPost``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `RecordHeartbeatV1HeartbeatPost`: map[string]interface{}
	fmt.Fprintf(os.Stdout, "Response from `TimingAPI.RecordHeartbeatV1HeartbeatPost`: %v\n", resp)
}
```

### Path Parameters



### Other Parameters

Other parameters are passed through a pointer to a apiRecordHeartbeatV1HeartbeatPostRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **heartbeatRequest** | [**HeartbeatRequest**](HeartbeatRequest.md) |  | 
 **authorization** | **string** | Bearer &lt;api-key&gt; | 

### Return type

**map[string]interface{}**

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)


## TimeReportV1TimeGet

> TimeSummaryResponse TimeReportV1TimeGet(ctx).Project(project).Days(days).Authorization(authorization).Execute()

Time Report



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
	project := "project_example" // string |  (optional)
	days := int32(56) // int32 |  (optional) (default to 7)
	authorization := "authorization_example" // string | Bearer <api-key> (optional)

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.TimingAPI.TimeReportV1TimeGet(context.Background()).Project(project).Days(days).Authorization(authorization).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `TimingAPI.TimeReportV1TimeGet``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `TimeReportV1TimeGet`: TimeSummaryResponse
	fmt.Fprintf(os.Stdout, "Response from `TimingAPI.TimeReportV1TimeGet`: %v\n", resp)
}
```

### Path Parameters



### Other Parameters

Other parameters are passed through a pointer to a apiTimeReportV1TimeGetRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **project** | **string** |  | 
 **days** | **int32** |  | [default to 7]
 **authorization** | **string** | Bearer &lt;api-key&gt; | 

### Return type

[**TimeSummaryResponse**](TimeSummaryResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)


## TimeTodayV1TimeTodayGet

> TimeSummaryResponse TimeTodayV1TimeTodayGet(ctx).Project(project).Authorization(authorization).Execute()

Time Today



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
	project := "project_example" // string |  (optional)
	authorization := "authorization_example" // string | Bearer <api-key> (optional)

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.TimingAPI.TimeTodayV1TimeTodayGet(context.Background()).Project(project).Authorization(authorization).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `TimingAPI.TimeTodayV1TimeTodayGet``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `TimeTodayV1TimeTodayGet`: TimeSummaryResponse
	fmt.Fprintf(os.Stdout, "Response from `TimingAPI.TimeTodayV1TimeTodayGet`: %v\n", resp)
}
```

### Path Parameters



### Other Parameters

Other parameters are passed through a pointer to a apiTimeTodayV1TimeTodayGetRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **project** | **string** |  | 
 **authorization** | **string** | Bearer &lt;api-key&gt; | 

### Return type

[**TimeSummaryResponse**](TimeSummaryResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)

