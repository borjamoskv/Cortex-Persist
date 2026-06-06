# \TelemetryAPI

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**AddMafiaNodeApiV1TelemetryNodesPost**](TelemetryAPI.md#AddMafiaNodeApiV1TelemetryNodesPost) | **Post** /api/v1/telemetry/nodes | Add Mafia Node
[**AddMafiaNodeTelemetryNodesPost**](TelemetryAPI.md#AddMafiaNodeTelemetryNodesPost) | **Post** /telemetry/nodes | Add Mafia Node
[**AddMafiaNodeV1TelemetryNodesPost**](TelemetryAPI.md#AddMafiaNodeV1TelemetryNodesPost) | **Post** /v1/telemetry/nodes | Add Mafia Node
[**GetMafiaNodesApiV1TelemetryNodesGet**](TelemetryAPI.md#GetMafiaNodesApiV1TelemetryNodesGet) | **Get** /api/v1/telemetry/nodes | Get Mafia Nodes
[**GetMafiaNodesTelemetryNodesGet**](TelemetryAPI.md#GetMafiaNodesTelemetryNodesGet) | **Get** /telemetry/nodes | Get Mafia Nodes
[**GetMafiaNodesV1TelemetryNodesGet**](TelemetryAPI.md#GetMafiaNodesV1TelemetryNodesGet) | **Get** /v1/telemetry/nodes | Get Mafia Nodes
[**IngestTelemetryApiV1TelemetryIngestPost**](TelemetryAPI.md#IngestTelemetryApiV1TelemetryIngestPost) | **Post** /api/v1/telemetry/ingest | Ingest Telemetry
[**IngestTelemetryTelemetryIngestPost**](TelemetryAPI.md#IngestTelemetryTelemetryIngestPost) | **Post** /telemetry/ingest | Ingest Telemetry
[**IngestTelemetryV1TelemetryIngestPost**](TelemetryAPI.md#IngestTelemetryV1TelemetryIngestPost) | **Post** /v1/telemetry/ingest | Ingest Telemetry



## AddMafiaNodeApiV1TelemetryNodesPost

> interface{} AddMafiaNodeApiV1TelemetryNodesPost(ctx).MafiaNodeProposal(mafiaNodeProposal).Execute()

Add Mafia Node



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
	mafiaNodeProposal := *openapiclient.NewMafiaNodeProposal("Node_example") // MafiaNodeProposal | 

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.TelemetryAPI.AddMafiaNodeApiV1TelemetryNodesPost(context.Background()).MafiaNodeProposal(mafiaNodeProposal).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `TelemetryAPI.AddMafiaNodeApiV1TelemetryNodesPost``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `AddMafiaNodeApiV1TelemetryNodesPost`: interface{}
	fmt.Fprintf(os.Stdout, "Response from `TelemetryAPI.AddMafiaNodeApiV1TelemetryNodesPost`: %v\n", resp)
}
```

### Path Parameters



### Other Parameters

Other parameters are passed through a pointer to a apiAddMafiaNodeApiV1TelemetryNodesPostRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **mafiaNodeProposal** | [**MafiaNodeProposal**](MafiaNodeProposal.md) |  | 

### Return type

**interface{}**

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)


## AddMafiaNodeTelemetryNodesPost

> interface{} AddMafiaNodeTelemetryNodesPost(ctx).MafiaNodeProposal(mafiaNodeProposal).Execute()

Add Mafia Node



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
	mafiaNodeProposal := *openapiclient.NewMafiaNodeProposal("Node_example") // MafiaNodeProposal | 

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.TelemetryAPI.AddMafiaNodeTelemetryNodesPost(context.Background()).MafiaNodeProposal(mafiaNodeProposal).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `TelemetryAPI.AddMafiaNodeTelemetryNodesPost``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `AddMafiaNodeTelemetryNodesPost`: interface{}
	fmt.Fprintf(os.Stdout, "Response from `TelemetryAPI.AddMafiaNodeTelemetryNodesPost`: %v\n", resp)
}
```

### Path Parameters



### Other Parameters

Other parameters are passed through a pointer to a apiAddMafiaNodeTelemetryNodesPostRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **mafiaNodeProposal** | [**MafiaNodeProposal**](MafiaNodeProposal.md) |  | 

### Return type

**interface{}**

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)


## AddMafiaNodeV1TelemetryNodesPost

> interface{} AddMafiaNodeV1TelemetryNodesPost(ctx).MafiaNodeProposal(mafiaNodeProposal).Execute()

Add Mafia Node



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
	mafiaNodeProposal := *openapiclient.NewMafiaNodeProposal("Node_example") // MafiaNodeProposal | 

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.TelemetryAPI.AddMafiaNodeV1TelemetryNodesPost(context.Background()).MafiaNodeProposal(mafiaNodeProposal).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `TelemetryAPI.AddMafiaNodeV1TelemetryNodesPost``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `AddMafiaNodeV1TelemetryNodesPost`: interface{}
	fmt.Fprintf(os.Stdout, "Response from `TelemetryAPI.AddMafiaNodeV1TelemetryNodesPost`: %v\n", resp)
}
```

### Path Parameters



### Other Parameters

Other parameters are passed through a pointer to a apiAddMafiaNodeV1TelemetryNodesPostRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **mafiaNodeProposal** | [**MafiaNodeProposal**](MafiaNodeProposal.md) |  | 

### Return type

**interface{}**

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)


## GetMafiaNodesApiV1TelemetryNodesGet

> interface{} GetMafiaNodesApiV1TelemetryNodesGet(ctx).Execute()

Get Mafia Nodes



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
	resp, r, err := apiClient.TelemetryAPI.GetMafiaNodesApiV1TelemetryNodesGet(context.Background()).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `TelemetryAPI.GetMafiaNodesApiV1TelemetryNodesGet``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `GetMafiaNodesApiV1TelemetryNodesGet`: interface{}
	fmt.Fprintf(os.Stdout, "Response from `TelemetryAPI.GetMafiaNodesApiV1TelemetryNodesGet`: %v\n", resp)
}
```

### Path Parameters

This endpoint does not need any parameter.

### Other Parameters

Other parameters are passed through a pointer to a apiGetMafiaNodesApiV1TelemetryNodesGetRequest struct via the builder pattern


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


## GetMafiaNodesTelemetryNodesGet

> interface{} GetMafiaNodesTelemetryNodesGet(ctx).Execute()

Get Mafia Nodes



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
	resp, r, err := apiClient.TelemetryAPI.GetMafiaNodesTelemetryNodesGet(context.Background()).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `TelemetryAPI.GetMafiaNodesTelemetryNodesGet``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `GetMafiaNodesTelemetryNodesGet`: interface{}
	fmt.Fprintf(os.Stdout, "Response from `TelemetryAPI.GetMafiaNodesTelemetryNodesGet`: %v\n", resp)
}
```

### Path Parameters

This endpoint does not need any parameter.

### Other Parameters

Other parameters are passed through a pointer to a apiGetMafiaNodesTelemetryNodesGetRequest struct via the builder pattern


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


## GetMafiaNodesV1TelemetryNodesGet

> interface{} GetMafiaNodesV1TelemetryNodesGet(ctx).Execute()

Get Mafia Nodes



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
	resp, r, err := apiClient.TelemetryAPI.GetMafiaNodesV1TelemetryNodesGet(context.Background()).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `TelemetryAPI.GetMafiaNodesV1TelemetryNodesGet``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `GetMafiaNodesV1TelemetryNodesGet`: interface{}
	fmt.Fprintf(os.Stdout, "Response from `TelemetryAPI.GetMafiaNodesV1TelemetryNodesGet`: %v\n", resp)
}
```

### Path Parameters

This endpoint does not need any parameter.

### Other Parameters

Other parameters are passed through a pointer to a apiGetMafiaNodesV1TelemetryNodesGetRequest struct via the builder pattern


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


## IngestTelemetryApiV1TelemetryIngestPost

> interface{} IngestTelemetryApiV1TelemetryIngestPost(ctx).TelemetryIngestRequest(telemetryIngestRequest).Execute()

Ingest Telemetry



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
	telemetryIngestRequest := *openapiclient.NewTelemetryIngestRequest(int32(123), "AgentId_example", *openapiclient.NewTelemetryPayload()) // TelemetryIngestRequest | 

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.TelemetryAPI.IngestTelemetryApiV1TelemetryIngestPost(context.Background()).TelemetryIngestRequest(telemetryIngestRequest).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `TelemetryAPI.IngestTelemetryApiV1TelemetryIngestPost``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `IngestTelemetryApiV1TelemetryIngestPost`: interface{}
	fmt.Fprintf(os.Stdout, "Response from `TelemetryAPI.IngestTelemetryApiV1TelemetryIngestPost`: %v\n", resp)
}
```

### Path Parameters



### Other Parameters

Other parameters are passed through a pointer to a apiIngestTelemetryApiV1TelemetryIngestPostRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **telemetryIngestRequest** | [**TelemetryIngestRequest**](TelemetryIngestRequest.md) |  | 

### Return type

**interface{}**

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)


## IngestTelemetryTelemetryIngestPost

> interface{} IngestTelemetryTelemetryIngestPost(ctx).TelemetryIngestRequest(telemetryIngestRequest).Execute()

Ingest Telemetry



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
	telemetryIngestRequest := *openapiclient.NewTelemetryIngestRequest(int32(123), "AgentId_example", *openapiclient.NewTelemetryPayload()) // TelemetryIngestRequest | 

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.TelemetryAPI.IngestTelemetryTelemetryIngestPost(context.Background()).TelemetryIngestRequest(telemetryIngestRequest).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `TelemetryAPI.IngestTelemetryTelemetryIngestPost``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `IngestTelemetryTelemetryIngestPost`: interface{}
	fmt.Fprintf(os.Stdout, "Response from `TelemetryAPI.IngestTelemetryTelemetryIngestPost`: %v\n", resp)
}
```

### Path Parameters



### Other Parameters

Other parameters are passed through a pointer to a apiIngestTelemetryTelemetryIngestPostRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **telemetryIngestRequest** | [**TelemetryIngestRequest**](TelemetryIngestRequest.md) |  | 

### Return type

**interface{}**

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)


## IngestTelemetryV1TelemetryIngestPost

> interface{} IngestTelemetryV1TelemetryIngestPost(ctx).TelemetryIngestRequest(telemetryIngestRequest).Execute()

Ingest Telemetry



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
	telemetryIngestRequest := *openapiclient.NewTelemetryIngestRequest(int32(123), "AgentId_example", *openapiclient.NewTelemetryPayload()) // TelemetryIngestRequest | 

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.TelemetryAPI.IngestTelemetryV1TelemetryIngestPost(context.Background()).TelemetryIngestRequest(telemetryIngestRequest).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `TelemetryAPI.IngestTelemetryV1TelemetryIngestPost``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `IngestTelemetryV1TelemetryIngestPost`: interface{}
	fmt.Fprintf(os.Stdout, "Response from `TelemetryAPI.IngestTelemetryV1TelemetryIngestPost`: %v\n", resp)
}
```

### Path Parameters



### Other Parameters

Other parameters are passed through a pointer to a apiIngestTelemetryV1TelemetryIngestPostRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **telemetryIngestRequest** | [**TelemetryIngestRequest**](TelemetryIngestRequest.md) |  | 

### Return type

**interface{}**

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)

