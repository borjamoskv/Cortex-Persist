# \FactsAPI

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**BatchStoreV1FactsBatchPost**](FactsAPI.md#BatchStoreV1FactsBatchPost) | **Post** /v1/facts/batch | Batch Store
[**CastVoteV1FactsFactIdVotePost**](FactsAPI.md#CastVoteV1FactsFactIdVotePost) | **Post** /v1/facts/{fact_id}/vote | Cast Vote
[**CastVoteV2V1FactsFactIdVoteV2Post**](FactsAPI.md#CastVoteV2V1FactsFactIdVoteV2Post) | **Post** /v1/facts/{fact_id}/vote-v2 | Cast Vote V2
[**DeprecateFactV1FactsFactIdDelete**](FactsAPI.md#DeprecateFactV1FactsFactIdDelete) | **Delete** /v1/facts/{fact_id} | Deprecate Fact
[**GetCausalChainV1FactsFactIdChainGet**](FactsAPI.md#GetCausalChainV1FactsFactIdChainGet) | **Get** /v1/facts/{fact_id}/chain | Get Causal Chain
[**GetFactByIdV1FactsFactIdGet**](FactsAPI.md#GetFactByIdV1FactsFactIdGet) | **Get** /v1/facts/{fact_id} | Get Fact By Id
[**GetFactHistoryV1FactsFactIdHistoryGet**](FactsAPI.md#GetFactHistoryV1FactsFactIdHistoryGet) | **Get** /v1/facts/{fact_id}/history | Get Fact History
[**ListAllFactsV1FactsGet**](FactsAPI.md#ListAllFactsV1FactsGet) | **Get** /v1/facts | List All Facts
[**ListVotesV1FactsFactIdVotesGet**](FactsAPI.md#ListVotesV1FactsFactIdVotesGet) | **Get** /v1/facts/{fact_id}/votes | List Votes
[**PropagateTaintV1FactsFactIdTaintPost**](FactsAPI.md#PropagateTaintV1FactsFactIdTaintPost) | **Post** /v1/facts/{fact_id}/taint | Propagate Taint
[**RecallFactsV1ProjectsProjectFactsGet**](FactsAPI.md#RecallFactsV1ProjectsProjectFactsGet) | **Get** /v1/projects/{project}/facts | Recall Facts
[**SearchFactsV1FactsSearchPost**](FactsAPI.md#SearchFactsV1FactsSearchPost) | **Post** /v1/facts/search | Search Facts
[**StoreFactV1FactsPost**](FactsAPI.md#StoreFactV1FactsPost) | **Post** /v1/facts | Store Fact
[**VerifyLedgerV1FactsVerifyGet**](FactsAPI.md#VerifyLedgerV1FactsVerifyGet) | **Get** /v1/facts/verify | Verify Ledger



## BatchStoreV1FactsBatchPost

> map[string]interface{} BatchStoreV1FactsBatchPost(ctx).BatchStoreRequest(batchStoreRequest).Authorization(authorization).Execute()

Batch Store



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
	batchStoreRequest := *openapiclient.NewBatchStoreRequest([]openapiclient.StoreMemoryRequest{*openapiclient.NewStoreMemoryRequest("Project_example", "Content_example")}) // BatchStoreRequest | 
	authorization := "authorization_example" // string | Bearer <api-key> (optional)

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.FactsAPI.BatchStoreV1FactsBatchPost(context.Background()).BatchStoreRequest(batchStoreRequest).Authorization(authorization).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `FactsAPI.BatchStoreV1FactsBatchPost``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `BatchStoreV1FactsBatchPost`: map[string]interface{}
	fmt.Fprintf(os.Stdout, "Response from `FactsAPI.BatchStoreV1FactsBatchPost`: %v\n", resp)
}
```

### Path Parameters



### Other Parameters

Other parameters are passed through a pointer to a apiBatchStoreV1FactsBatchPostRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **batchStoreRequest** | [**BatchStoreRequest**](BatchStoreRequest.md) |  | 
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


## CastVoteV1FactsFactIdVotePost

> VoteResponse CastVoteV1FactsFactIdVotePost(ctx, factId).VoteRequest(voteRequest).Authorization(authorization).Execute()

Cast Vote



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
	factId := int32(56) // int32 | 
	voteRequest := *openapiclient.NewVoteRequest(int32(123)) // VoteRequest | 
	authorization := "authorization_example" // string | Bearer <api-key> (optional)

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.FactsAPI.CastVoteV1FactsFactIdVotePost(context.Background(), factId).VoteRequest(voteRequest).Authorization(authorization).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `FactsAPI.CastVoteV1FactsFactIdVotePost``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `CastVoteV1FactsFactIdVotePost`: VoteResponse
	fmt.Fprintf(os.Stdout, "Response from `FactsAPI.CastVoteV1FactsFactIdVotePost`: %v\n", resp)
}
```

### Path Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
**ctx** | **context.Context** | context for authentication, logging, cancellation, deadlines, tracing, etc.
**factId** | **int32** |  | 

### Other Parameters

Other parameters are passed through a pointer to a apiCastVoteV1FactsFactIdVotePostRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------

 **voteRequest** | [**VoteRequest**](VoteRequest.md) |  | 
 **authorization** | **string** | Bearer &lt;api-key&gt; | 

### Return type

[**VoteResponse**](VoteResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)


## CastVoteV2V1FactsFactIdVoteV2Post

> VoteResponse CastVoteV2V1FactsFactIdVoteV2Post(ctx, factId).VoteV2Request(voteV2Request).Authorization(authorization).Execute()

Cast Vote V2



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
	factId := int32(56) // int32 | 
	voteV2Request := *openapiclient.NewVoteV2Request("AgentId_example", int32(123)) // VoteV2Request | 
	authorization := "authorization_example" // string | Bearer <api-key> (optional)

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.FactsAPI.CastVoteV2V1FactsFactIdVoteV2Post(context.Background(), factId).VoteV2Request(voteV2Request).Authorization(authorization).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `FactsAPI.CastVoteV2V1FactsFactIdVoteV2Post``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `CastVoteV2V1FactsFactIdVoteV2Post`: VoteResponse
	fmt.Fprintf(os.Stdout, "Response from `FactsAPI.CastVoteV2V1FactsFactIdVoteV2Post`: %v\n", resp)
}
```

### Path Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
**ctx** | **context.Context** | context for authentication, logging, cancellation, deadlines, tracing, etc.
**factId** | **int32** |  | 

### Other Parameters

Other parameters are passed through a pointer to a apiCastVoteV2V1FactsFactIdVoteV2PostRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------

 **voteV2Request** | [**VoteV2Request**](VoteV2Request.md) |  | 
 **authorization** | **string** | Bearer &lt;api-key&gt; | 

### Return type

[**VoteResponse**](VoteResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)


## DeprecateFactV1FactsFactIdDelete

> map[string]interface{} DeprecateFactV1FactsFactIdDelete(ctx, factId).Authorization(authorization).Execute()

Deprecate Fact



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
	factId := int32(56) // int32 | 
	authorization := "authorization_example" // string | Bearer <api-key> (optional)

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.FactsAPI.DeprecateFactV1FactsFactIdDelete(context.Background(), factId).Authorization(authorization).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `FactsAPI.DeprecateFactV1FactsFactIdDelete``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `DeprecateFactV1FactsFactIdDelete`: map[string]interface{}
	fmt.Fprintf(os.Stdout, "Response from `FactsAPI.DeprecateFactV1FactsFactIdDelete`: %v\n", resp)
}
```

### Path Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
**ctx** | **context.Context** | context for authentication, logging, cancellation, deadlines, tracing, etc.
**factId** | **int32** |  | 

### Other Parameters

Other parameters are passed through a pointer to a apiDeprecateFactV1FactsFactIdDeleteRequest struct via the builder pattern


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


## GetCausalChainV1FactsFactIdChainGet

> []map[string]interface{} GetCausalChainV1FactsFactIdChainGet(ctx, factId).Direction(direction).MaxDepth(maxDepth).Authorization(authorization).Execute()

Get Causal Chain



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
	factId := int32(56) // int32 | 
	direction := "direction_example" // string | 'up' or 'down' (optional) (default to "down")
	maxDepth := int32(56) // int32 |  (optional) (default to 10)
	authorization := "authorization_example" // string | Bearer <api-key> (optional)

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.FactsAPI.GetCausalChainV1FactsFactIdChainGet(context.Background(), factId).Direction(direction).MaxDepth(maxDepth).Authorization(authorization).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `FactsAPI.GetCausalChainV1FactsFactIdChainGet``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `GetCausalChainV1FactsFactIdChainGet`: []map[string]interface{}
	fmt.Fprintf(os.Stdout, "Response from `FactsAPI.GetCausalChainV1FactsFactIdChainGet`: %v\n", resp)
}
```

### Path Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
**ctx** | **context.Context** | context for authentication, logging, cancellation, deadlines, tracing, etc.
**factId** | **int32** |  | 

### Other Parameters

Other parameters are passed through a pointer to a apiGetCausalChainV1FactsFactIdChainGetRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------

 **direction** | **string** | &#39;up&#39; or &#39;down&#39; | [default to &quot;down&quot;]
 **maxDepth** | **int32** |  | [default to 10]
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


## GetFactByIdV1FactsFactIdGet

> FactResponse GetFactByIdV1FactsFactIdGet(ctx, factId).Authorization(authorization).Execute()

Get Fact By Id



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
	factId := int32(56) // int32 | 
	authorization := "authorization_example" // string | Bearer <api-key> (optional)

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.FactsAPI.GetFactByIdV1FactsFactIdGet(context.Background(), factId).Authorization(authorization).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `FactsAPI.GetFactByIdV1FactsFactIdGet``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `GetFactByIdV1FactsFactIdGet`: FactResponse
	fmt.Fprintf(os.Stdout, "Response from `FactsAPI.GetFactByIdV1FactsFactIdGet`: %v\n", resp)
}
```

### Path Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
**ctx** | **context.Context** | context for authentication, logging, cancellation, deadlines, tracing, etc.
**factId** | **int32** |  | 

### Other Parameters

Other parameters are passed through a pointer to a apiGetFactByIdV1FactsFactIdGetRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------

 **authorization** | **string** | Bearer &lt;api-key&gt; | 

### Return type

[**FactResponse**](FactResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)


## GetFactHistoryV1FactsFactIdHistoryGet

> []FactResponse GetFactHistoryV1FactsFactIdHistoryGet(ctx, factId).Authorization(authorization).Execute()

Get Fact History



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
	factId := int32(56) // int32 | 
	authorization := "authorization_example" // string | Bearer <api-key> (optional)

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.FactsAPI.GetFactHistoryV1FactsFactIdHistoryGet(context.Background(), factId).Authorization(authorization).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `FactsAPI.GetFactHistoryV1FactsFactIdHistoryGet``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `GetFactHistoryV1FactsFactIdHistoryGet`: []FactResponse
	fmt.Fprintf(os.Stdout, "Response from `FactsAPI.GetFactHistoryV1FactsFactIdHistoryGet`: %v\n", resp)
}
```

### Path Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
**ctx** | **context.Context** | context for authentication, logging, cancellation, deadlines, tracing, etc.
**factId** | **int32** |  | 

### Other Parameters

Other parameters are passed through a pointer to a apiGetFactHistoryV1FactsFactIdHistoryGetRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------

 **authorization** | **string** | Bearer &lt;api-key&gt; | 

### Return type

[**[]FactResponse**](FactResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)


## ListAllFactsV1FactsGet

> []FactResponse ListAllFactsV1FactsGet(ctx).Limit(limit).Authorization(authorization).Execute()

List All Facts

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
	limit := int32(56) // int32 |  (optional) (default to 50)
	authorization := "authorization_example" // string | Bearer <api-key> (optional)

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.FactsAPI.ListAllFactsV1FactsGet(context.Background()).Limit(limit).Authorization(authorization).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `FactsAPI.ListAllFactsV1FactsGet``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `ListAllFactsV1FactsGet`: []FactResponse
	fmt.Fprintf(os.Stdout, "Response from `FactsAPI.ListAllFactsV1FactsGet`: %v\n", resp)
}
```

### Path Parameters



### Other Parameters

Other parameters are passed through a pointer to a apiListAllFactsV1FactsGetRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **limit** | **int32** |  | [default to 50]
 **authorization** | **string** | Bearer &lt;api-key&gt; | 

### Return type

[**[]FactResponse**](FactResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)


## ListVotesV1FactsFactIdVotesGet

> []map[string]interface{} ListVotesV1FactsFactIdVotesGet(ctx, factId).Authorization(authorization).Execute()

List Votes



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
	factId := int32(56) // int32 | 
	authorization := "authorization_example" // string | Bearer <api-key> (optional)

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.FactsAPI.ListVotesV1FactsFactIdVotesGet(context.Background(), factId).Authorization(authorization).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `FactsAPI.ListVotesV1FactsFactIdVotesGet``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `ListVotesV1FactsFactIdVotesGet`: []map[string]interface{}
	fmt.Fprintf(os.Stdout, "Response from `FactsAPI.ListVotesV1FactsFactIdVotesGet`: %v\n", resp)
}
```

### Path Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
**ctx** | **context.Context** | context for authentication, logging, cancellation, deadlines, tracing, etc.
**factId** | **int32** |  | 

### Other Parameters

Other parameters are passed through a pointer to a apiListVotesV1FactsFactIdVotesGetRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------

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


## PropagateTaintV1FactsFactIdTaintPost

> map[string]interface{} PropagateTaintV1FactsFactIdTaintPost(ctx, factId).Authorization(authorization).Execute()

Propagate Taint



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
	factId := int32(56) // int32 | 
	authorization := "authorization_example" // string | Bearer <api-key> (optional)

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.FactsAPI.PropagateTaintV1FactsFactIdTaintPost(context.Background(), factId).Authorization(authorization).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `FactsAPI.PropagateTaintV1FactsFactIdTaintPost``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `PropagateTaintV1FactsFactIdTaintPost`: map[string]interface{}
	fmt.Fprintf(os.Stdout, "Response from `FactsAPI.PropagateTaintV1FactsFactIdTaintPost`: %v\n", resp)
}
```

### Path Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
**ctx** | **context.Context** | context for authentication, logging, cancellation, deadlines, tracing, etc.
**factId** | **int32** |  | 

### Other Parameters

Other parameters are passed through a pointer to a apiPropagateTaintV1FactsFactIdTaintPostRequest struct via the builder pattern


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


## RecallFactsV1ProjectsProjectFactsGet

> []FactResponse RecallFactsV1ProjectsProjectFactsGet(ctx, project).Limit(limit).Authorization(authorization).Execute()

Recall Facts



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
	limit := int32(56) // int32 |  (optional)
	authorization := "authorization_example" // string | Bearer <api-key> (optional)

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.FactsAPI.RecallFactsV1ProjectsProjectFactsGet(context.Background(), project).Limit(limit).Authorization(authorization).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `FactsAPI.RecallFactsV1ProjectsProjectFactsGet``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `RecallFactsV1ProjectsProjectFactsGet`: []FactResponse
	fmt.Fprintf(os.Stdout, "Response from `FactsAPI.RecallFactsV1ProjectsProjectFactsGet`: %v\n", resp)
}
```

### Path Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
**ctx** | **context.Context** | context for authentication, logging, cancellation, deadlines, tracing, etc.
**project** | **string** |  | 

### Other Parameters

Other parameters are passed through a pointer to a apiRecallFactsV1ProjectsProjectFactsGetRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------

 **limit** | **int32** |  | 
 **authorization** | **string** | Bearer &lt;api-key&gt; | 

### Return type

[**[]FactResponse**](FactResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)


## SearchFactsV1FactsSearchPost

> []FactResponse SearchFactsV1FactsSearchPost(ctx).SearchMemoryRequest(searchMemoryRequest).Authorization(authorization).Execute()

Search Facts



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
	searchMemoryRequest := *openapiclient.NewSearchMemoryRequest("Query_example") // SearchMemoryRequest | 
	authorization := "authorization_example" // string | Bearer <api-key> (optional)

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.FactsAPI.SearchFactsV1FactsSearchPost(context.Background()).SearchMemoryRequest(searchMemoryRequest).Authorization(authorization).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `FactsAPI.SearchFactsV1FactsSearchPost``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `SearchFactsV1FactsSearchPost`: []FactResponse
	fmt.Fprintf(os.Stdout, "Response from `FactsAPI.SearchFactsV1FactsSearchPost`: %v\n", resp)
}
```

### Path Parameters



### Other Parameters

Other parameters are passed through a pointer to a apiSearchFactsV1FactsSearchPostRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **searchMemoryRequest** | [**SearchMemoryRequest**](SearchMemoryRequest.md) |  | 
 **authorization** | **string** | Bearer &lt;api-key&gt; | 

### Return type

[**[]FactResponse**](FactResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)


## StoreFactV1FactsPost

> StoreResponse StoreFactV1FactsPost(ctx).StoreRequest(storeRequest).Authorization(authorization).Execute()

Store Fact



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
	storeRequest := *openapiclient.NewStoreRequest("Project_example", "Content_example") // StoreRequest | 
	authorization := "authorization_example" // string | Bearer <api-key> (optional)

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.FactsAPI.StoreFactV1FactsPost(context.Background()).StoreRequest(storeRequest).Authorization(authorization).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `FactsAPI.StoreFactV1FactsPost``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `StoreFactV1FactsPost`: StoreResponse
	fmt.Fprintf(os.Stdout, "Response from `FactsAPI.StoreFactV1FactsPost`: %v\n", resp)
}
```

### Path Parameters



### Other Parameters

Other parameters are passed through a pointer to a apiStoreFactV1FactsPostRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **storeRequest** | [**StoreRequest**](StoreRequest.md) |  | 
 **authorization** | **string** | Bearer &lt;api-key&gt; | 

### Return type

[**StoreResponse**](StoreResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)


## VerifyLedgerV1FactsVerifyGet

> map[string]interface{} VerifyLedgerV1FactsVerifyGet(ctx).Authorization(authorization).Execute()

Verify Ledger



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
	resp, r, err := apiClient.FactsAPI.VerifyLedgerV1FactsVerifyGet(context.Background()).Authorization(authorization).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `FactsAPI.VerifyLedgerV1FactsVerifyGet``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `VerifyLedgerV1FactsVerifyGet`: map[string]interface{}
	fmt.Fprintf(os.Stdout, "Response from `FactsAPI.VerifyLedgerV1FactsVerifyGet`: %v\n", resp)
}
```

### Path Parameters



### Other Parameters

Other parameters are passed through a pointer to a apiVerifyLedgerV1FactsVerifyGetRequest struct via the builder pattern


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

