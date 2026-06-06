# \MejoraloAPI

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**GetHistoryV1MejoraloHistoryGet**](MejoraloAPI.md#GetHistoryV1MejoraloHistoryGet) | **Get** /v1/mejoralo/history | Get History
[**RecordSessionV1MejoraloRecordPost**](MejoraloAPI.md#RecordSessionV1MejoraloRecordPost) | **Post** /v1/mejoralo/record | Record Session
[**ScanProjectV1MejoraloScanPost**](MejoraloAPI.md#ScanProjectV1MejoraloScanPost) | **Post** /v1/mejoralo/scan | Scan Project
[**ShipGateV1MejoraloShipPost**](MejoraloAPI.md#ShipGateV1MejoraloShipPost) | **Post** /v1/mejoralo/ship | Ship Gate



## GetHistoryV1MejoraloHistoryGet

> []map[string]interface{} GetHistoryV1MejoraloHistoryGet(ctx).Project(project).Limit(limit).Authorization(authorization).Execute()

Get History



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
	project := "project_example" // string | 
	limit := int32(56) // int32 |  (optional) (default to 20)
	authorization := "authorization_example" // string | Bearer <api-key> (optional)

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.MejoraloAPI.GetHistoryV1MejoraloHistoryGet(context.Background()).Project(project).Limit(limit).Authorization(authorization).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `MejoraloAPI.GetHistoryV1MejoraloHistoryGet``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `GetHistoryV1MejoraloHistoryGet`: []map[string]interface{}
	fmt.Fprintf(os.Stdout, "Response from `MejoraloAPI.GetHistoryV1MejoraloHistoryGet`: %v\n", resp)
}
```

### Path Parameters



### Other Parameters

Other parameters are passed through a pointer to a apiGetHistoryV1MejoraloHistoryGetRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **project** | **string** |  | 
 **limit** | **int32** |  | [default to 20]
 **authorization** | **string** | Bearer &lt;api-key&gt; | 

### Return type

[**[]map[string]interface{}**](map.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)


## RecordSessionV1MejoraloRecordPost

> MejoraloSessionResponse RecordSessionV1MejoraloRecordPost(ctx).MejoraloSessionRequest(mejoraloSessionRequest).Authorization(authorization).Execute()

Record Session



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
	mejoraloSessionRequest := *openapiclient.NewMejoraloSessionRequest("Project_example", int32(123), int32(123)) // MejoraloSessionRequest | 
	authorization := "authorization_example" // string | Bearer <api-key> (optional)

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.MejoraloAPI.RecordSessionV1MejoraloRecordPost(context.Background()).MejoraloSessionRequest(mejoraloSessionRequest).Authorization(authorization).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `MejoraloAPI.RecordSessionV1MejoraloRecordPost``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `RecordSessionV1MejoraloRecordPost`: MejoraloSessionResponse
	fmt.Fprintf(os.Stdout, "Response from `MejoraloAPI.RecordSessionV1MejoraloRecordPost`: %v\n", resp)
}
```

### Path Parameters



### Other Parameters

Other parameters are passed through a pointer to a apiRecordSessionV1MejoraloRecordPostRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **mejoraloSessionRequest** | [**MejoraloSessionRequest**](MejoraloSessionRequest.md) |  | 
 **authorization** | **string** | Bearer &lt;api-key&gt; | 

### Return type

[**MejoraloSessionResponse**](MejoraloSessionResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)


## ScanProjectV1MejoraloScanPost

> MejoraloScanResponse ScanProjectV1MejoraloScanPost(ctx).MejoraloScanRequest(mejoraloScanRequest).Authorization(authorization).Execute()

Scan Project



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
	mejoraloScanRequest := *openapiclient.NewMejoraloScanRequest("Project_example", "Path_example") // MejoraloScanRequest | 
	authorization := "authorization_example" // string | Bearer <api-key> (optional)

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.MejoraloAPI.ScanProjectV1MejoraloScanPost(context.Background()).MejoraloScanRequest(mejoraloScanRequest).Authorization(authorization).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `MejoraloAPI.ScanProjectV1MejoraloScanPost``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `ScanProjectV1MejoraloScanPost`: MejoraloScanResponse
	fmt.Fprintf(os.Stdout, "Response from `MejoraloAPI.ScanProjectV1MejoraloScanPost`: %v\n", resp)
}
```

### Path Parameters



### Other Parameters

Other parameters are passed through a pointer to a apiScanProjectV1MejoraloScanPostRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **mejoraloScanRequest** | [**MejoraloScanRequest**](MejoraloScanRequest.md) |  | 
 **authorization** | **string** | Bearer &lt;api-key&gt; | 

### Return type

[**MejoraloScanResponse**](MejoraloScanResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)


## ShipGateV1MejoraloShipPost

> MejoraloShipResponse ShipGateV1MejoraloShipPost(ctx).MejoraloShipRequest(mejoraloShipRequest).Authorization(authorization).Execute()

Ship Gate



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
	mejoraloShipRequest := *openapiclient.NewMejoraloShipRequest("Project_example", "Path_example") // MejoraloShipRequest | 
	authorization := "authorization_example" // string | Bearer <api-key> (optional)

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.MejoraloAPI.ShipGateV1MejoraloShipPost(context.Background()).MejoraloShipRequest(mejoraloShipRequest).Authorization(authorization).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `MejoraloAPI.ShipGateV1MejoraloShipPost``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `ShipGateV1MejoraloShipPost`: MejoraloShipResponse
	fmt.Fprintf(os.Stdout, "Response from `MejoraloAPI.ShipGateV1MejoraloShipPost`: %v\n", resp)
}
```

### Path Parameters



### Other Parameters

Other parameters are passed through a pointer to a apiShipGateV1MejoraloShipPostRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **mejoraloShipRequest** | [**MejoraloShipRequest**](MejoraloShipRequest.md) |  | 
 **authorization** | **string** | Bearer &lt;api-key&gt; | 

### Return type

[**MejoraloShipResponse**](MejoraloShipResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)

