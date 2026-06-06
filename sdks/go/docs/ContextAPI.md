# \ContextAPI

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**ContextHistoryV1ContextHistoryGet**](ContextAPI.md#ContextHistoryV1ContextHistoryGet) | **Get** /v1/context/history | Context History
[**InferContextV1ContextInferGet**](ContextAPI.md#InferContextV1ContextInferGet) | **Get** /v1/context/infer | Infer Context
[**ListSignalsV1ContextSignalsGet**](ContextAPI.md#ListSignalsV1ContextSignalsGet) | **Get** /v1/context/signals | List Signals



## ContextHistoryV1ContextHistoryGet

> []map[string]interface{} ContextHistoryV1ContextHistoryGet(ctx).Limit(limit).Authorization(authorization).Execute()

Context History



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
	limit := int32(56) // int32 |  (optional) (default to 10)
	authorization := "authorization_example" // string | Bearer <api-key> (optional)

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.ContextAPI.ContextHistoryV1ContextHistoryGet(context.Background()).Limit(limit).Authorization(authorization).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `ContextAPI.ContextHistoryV1ContextHistoryGet``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `ContextHistoryV1ContextHistoryGet`: []map[string]interface{}
	fmt.Fprintf(os.Stdout, "Response from `ContextAPI.ContextHistoryV1ContextHistoryGet`: %v\n", resp)
}
```

### Path Parameters



### Other Parameters

Other parameters are passed through a pointer to a apiContextHistoryV1ContextHistoryGetRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **limit** | **int32** |  | [default to 10]
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


## InferContextV1ContextInferGet

> ContextSnapshotResponse InferContextV1ContextInferGet(ctx).Persist(persist).Authorization(authorization).Execute()

Infer Context



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
	persist := true // bool | Persist snapshot to DB (optional) (default to true)
	authorization := "authorization_example" // string | Bearer <api-key> (optional)

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.ContextAPI.InferContextV1ContextInferGet(context.Background()).Persist(persist).Authorization(authorization).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `ContextAPI.InferContextV1ContextInferGet``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `InferContextV1ContextInferGet`: ContextSnapshotResponse
	fmt.Fprintf(os.Stdout, "Response from `ContextAPI.InferContextV1ContextInferGet`: %v\n", resp)
}
```

### Path Parameters



### Other Parameters

Other parameters are passed through a pointer to a apiInferContextV1ContextInferGetRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **persist** | **bool** | Persist snapshot to DB | [default to true]
 **authorization** | **string** | Bearer &lt;api-key&gt; | 

### Return type

[**ContextSnapshotResponse**](ContextSnapshotResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)


## ListSignalsV1ContextSignalsGet

> []ContextSignalModel ListSignalsV1ContextSignalsGet(ctx).Authorization(authorization).Execute()

List Signals



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
	resp, r, err := apiClient.ContextAPI.ListSignalsV1ContextSignalsGet(context.Background()).Authorization(authorization).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `ContextAPI.ListSignalsV1ContextSignalsGet``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `ListSignalsV1ContextSignalsGet`: []ContextSignalModel
	fmt.Fprintf(os.Stdout, "Response from `ContextAPI.ListSignalsV1ContextSignalsGet`: %v\n", resp)
}
```

### Path Parameters



### Other Parameters

Other parameters are passed through a pointer to a apiListSignalsV1ContextSignalsGetRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **authorization** | **string** | Bearer &lt;api-key&gt; | 

### Return type

[**[]ContextSignalModel**](ContextSignalModel.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)

