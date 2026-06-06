# \UsageAPI

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**GetUsageBreakdownV1UsageBreakdownGet**](UsageAPI.md#GetUsageBreakdownV1UsageBreakdownGet) | **Get** /v1/usage/breakdown | Get Usage Breakdown
[**GetUsageHistoryV1UsageHistoryGet**](UsageAPI.md#GetUsageHistoryV1UsageHistoryGet) | **Get** /v1/usage/history | Get Usage History
[**GetUsageV1UsageGet**](UsageAPI.md#GetUsageV1UsageGet) | **Get** /v1/usage | Get Usage



## GetUsageBreakdownV1UsageBreakdownGet

> map[string]interface{} GetUsageBreakdownV1UsageBreakdownGet(ctx).Authorization(authorization).Execute()

Get Usage Breakdown



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
	authorization := "authorization_example" // string | Bearer <api-key> (optional)

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.UsageAPI.GetUsageBreakdownV1UsageBreakdownGet(context.Background()).Authorization(authorization).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `UsageAPI.GetUsageBreakdownV1UsageBreakdownGet``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `GetUsageBreakdownV1UsageBreakdownGet`: map[string]interface{}
	fmt.Fprintf(os.Stdout, "Response from `UsageAPI.GetUsageBreakdownV1UsageBreakdownGet`: %v\n", resp)
}
```

### Path Parameters



### Other Parameters

Other parameters are passed through a pointer to a apiGetUsageBreakdownV1UsageBreakdownGetRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **authorization** | **string** | Bearer &lt;api-key&gt; | 

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


## GetUsageHistoryV1UsageHistoryGet

> map[string]interface{} GetUsageHistoryV1UsageHistoryGet(ctx).Months(months).Authorization(authorization).Execute()

Get Usage History



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
	months := int32(56) // int32 |  (optional) (default to 12)
	authorization := "authorization_example" // string | Bearer <api-key> (optional)

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.UsageAPI.GetUsageHistoryV1UsageHistoryGet(context.Background()).Months(months).Authorization(authorization).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `UsageAPI.GetUsageHistoryV1UsageHistoryGet``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `GetUsageHistoryV1UsageHistoryGet`: map[string]interface{}
	fmt.Fprintf(os.Stdout, "Response from `UsageAPI.GetUsageHistoryV1UsageHistoryGet`: %v\n", resp)
}
```

### Path Parameters



### Other Parameters

Other parameters are passed through a pointer to a apiGetUsageHistoryV1UsageHistoryGetRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **months** | **int32** |  | [default to 12]
 **authorization** | **string** | Bearer &lt;api-key&gt; | 

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


## GetUsageV1UsageGet

> map[string]interface{} GetUsageV1UsageGet(ctx).Authorization(authorization).Execute()

Get Usage



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
	authorization := "authorization_example" // string | Bearer <api-key> (optional)

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.UsageAPI.GetUsageV1UsageGet(context.Background()).Authorization(authorization).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `UsageAPI.GetUsageV1UsageGet``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `GetUsageV1UsageGet`: map[string]interface{}
	fmt.Fprintf(os.Stdout, "Response from `UsageAPI.GetUsageV1UsageGet`: %v\n", resp)
}
```

### Path Parameters



### Other Parameters

Other parameters are passed through a pointer to a apiGetUsageV1UsageGetRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **authorization** | **string** | Bearer &lt;api-key&gt; | 

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

