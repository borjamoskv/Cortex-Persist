# \EventsAPI

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**StreamEventsV1EventsStreamGet**](EventsAPI.md#StreamEventsV1EventsStreamGet) | **Get** /v1/events/stream | Stream Events
[**StreamEventsV1PublicEventsStreamGet**](EventsAPI.md#StreamEventsV1PublicEventsStreamGet) | **Get** /v1/public/events/stream | Stream Events



## StreamEventsV1EventsStreamGet

> interface{} StreamEventsV1EventsStreamGet(ctx).Types(types).Authorization(authorization).Execute()

Stream Events



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
	types := "types_example" // string | Comma-separated list of event types (optional)
	authorization := "authorization_example" // string | Bearer <api-key> (optional)

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.EventsAPI.StreamEventsV1EventsStreamGet(context.Background()).Types(types).Authorization(authorization).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `EventsAPI.StreamEventsV1EventsStreamGet``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `StreamEventsV1EventsStreamGet`: interface{}
	fmt.Fprintf(os.Stdout, "Response from `EventsAPI.StreamEventsV1EventsStreamGet`: %v\n", resp)
}
```

### Path Parameters



### Other Parameters

Other parameters are passed through a pointer to a apiStreamEventsV1EventsStreamGetRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **types** | **string** | Comma-separated list of event types | 
 **authorization** | **string** | Bearer &lt;api-key&gt; | 

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


## StreamEventsV1PublicEventsStreamGet

> interface{} StreamEventsV1PublicEventsStreamGet(ctx).Execute()

Stream Events



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
	resp, r, err := apiClient.EventsAPI.StreamEventsV1PublicEventsStreamGet(context.Background()).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `EventsAPI.StreamEventsV1PublicEventsStreamGet``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `StreamEventsV1PublicEventsStreamGet`: interface{}
	fmt.Fprintf(os.Stdout, "Response from `EventsAPI.StreamEventsV1PublicEventsStreamGet`: %v\n", resp)
}
```

### Path Parameters

This endpoint does not need any parameter.

### Other Parameters

Other parameters are passed through a pointer to a apiStreamEventsV1PublicEventsStreamGetRequest struct via the builder pattern


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

