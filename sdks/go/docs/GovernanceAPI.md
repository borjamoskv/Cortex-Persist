# \GovernanceAPI

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**CreateApiKeyV1AdminKeysPost**](GovernanceAPI.md#CreateApiKeyV1AdminKeysPost) | **Post** /v1/admin/keys | Create Api Key
[**DeepHealthCheckV1HealthDeepGet**](GovernanceAPI.md#DeepHealthCheckV1HealthDeepGet) | **Get** /v1/health/deep | Deep Health Check
[**ExecuteCredibilityStrikeV1AdminCredibilityStrikePost**](GovernanceAPI.md#ExecuteCredibilityStrikeV1AdminCredibilityStrikePost) | **Post** /v1/admin/credibility-strike | Execute Credibility Strike
[**ExportProjectV1ProjectsProjectExportGet**](GovernanceAPI.md#ExportProjectV1ProjectsProjectExportGet) | **Get** /v1/projects/{project}/export | Export Project
[**GenerateHandoffContextV1HandoffPost**](GovernanceAPI.md#GenerateHandoffContextV1HandoffPost) | **Post** /v1/handoff | Generate Handoff Context
[**GetSystemStatusV1StatusGet**](GovernanceAPI.md#GetSystemStatusV1StatusGet) | **Get** /v1/status | Get System Status
[**ListApiKeysV1AdminKeysGet**](GovernanceAPI.md#ListApiKeysV1AdminKeysGet) | **Get** /v1/admin/keys | List Api Keys



## CreateApiKeyV1AdminKeysPost

> ApiKeyResponse CreateApiKeyV1AdminKeysPost(ctx).Name(name).TenantId(tenantId).Authorization(authorization).Execute()

Create Api Key



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
	name := "name_example" // string | 
	tenantId := "tenantId_example" // string |  (optional) (default to "default")
	authorization := "authorization_example" // string |  (optional)

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.GovernanceAPI.CreateApiKeyV1AdminKeysPost(context.Background()).Name(name).TenantId(tenantId).Authorization(authorization).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `GovernanceAPI.CreateApiKeyV1AdminKeysPost``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `CreateApiKeyV1AdminKeysPost`: ApiKeyResponse
	fmt.Fprintf(os.Stdout, "Response from `GovernanceAPI.CreateApiKeyV1AdminKeysPost`: %v\n", resp)
}
```

### Path Parameters



### Other Parameters

Other parameters are passed through a pointer to a apiCreateApiKeyV1AdminKeysPostRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **name** | **string** |  | 
 **tenantId** | **string** |  | [default to &quot;default&quot;]
 **authorization** | **string** |  | 

### Return type

[**ApiKeyResponse**](ApiKeyResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)


## DeepHealthCheckV1HealthDeepGet

> DeepHealthResponse DeepHealthCheckV1HealthDeepGet(ctx).Authorization(authorization).Execute()

Deep Health Check



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
	resp, r, err := apiClient.GovernanceAPI.DeepHealthCheckV1HealthDeepGet(context.Background()).Authorization(authorization).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `GovernanceAPI.DeepHealthCheckV1HealthDeepGet``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `DeepHealthCheckV1HealthDeepGet`: DeepHealthResponse
	fmt.Fprintf(os.Stdout, "Response from `GovernanceAPI.DeepHealthCheckV1HealthDeepGet`: %v\n", resp)
}
```

### Path Parameters



### Other Parameters

Other parameters are passed through a pointer to a apiDeepHealthCheckV1HealthDeepGetRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **authorization** | **string** | Bearer &lt;api-key&gt; | 

### Return type

[**DeepHealthResponse**](DeepHealthResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)


## ExecuteCredibilityStrikeV1AdminCredibilityStrikePost

> map[string]interface{} ExecuteCredibilityStrikeV1AdminCredibilityStrikePost(ctx).Project(project).Ultrathink(ultrathink).Authorization(authorization).Execute()

Execute Credibility Strike



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
	ultrathink := true // bool |  (optional) (default to true)
	authorization := "authorization_example" // string | Bearer <api-key> (optional)

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.GovernanceAPI.ExecuteCredibilityStrikeV1AdminCredibilityStrikePost(context.Background()).Project(project).Ultrathink(ultrathink).Authorization(authorization).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `GovernanceAPI.ExecuteCredibilityStrikeV1AdminCredibilityStrikePost``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `ExecuteCredibilityStrikeV1AdminCredibilityStrikePost`: map[string]interface{}
	fmt.Fprintf(os.Stdout, "Response from `GovernanceAPI.ExecuteCredibilityStrikeV1AdminCredibilityStrikePost`: %v\n", resp)
}
```

### Path Parameters



### Other Parameters

Other parameters are passed through a pointer to a apiExecuteCredibilityStrikeV1AdminCredibilityStrikePostRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **project** | **string** |  | 
 **ultrathink** | **bool** |  | [default to true]
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


## ExportProjectV1ProjectsProjectExportGet

> ExportResponse ExportProjectV1ProjectsProjectExportGet(ctx, project).Path(path).Format(format).Authorization(authorization).Execute()

Export Project



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
	path := "path_example" // string |  (optional)
	format := "format_example" // string |  (optional) (default to "json")
	authorization := "authorization_example" // string | Bearer <api-key> (optional)

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.GovernanceAPI.ExportProjectV1ProjectsProjectExportGet(context.Background(), project).Path(path).Format(format).Authorization(authorization).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `GovernanceAPI.ExportProjectV1ProjectsProjectExportGet``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `ExportProjectV1ProjectsProjectExportGet`: ExportResponse
	fmt.Fprintf(os.Stdout, "Response from `GovernanceAPI.ExportProjectV1ProjectsProjectExportGet`: %v\n", resp)
}
```

### Path Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
**ctx** | **context.Context** | context for authentication, logging, cancellation, deadlines, tracing, etc.
**project** | **string** |  | 

### Other Parameters

Other parameters are passed through a pointer to a apiExportProjectV1ProjectsProjectExportGetRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------

 **path** | **string** |  | 
 **format** | **string** |  | [default to &quot;json&quot;]
 **authorization** | **string** | Bearer &lt;api-key&gt; | 

### Return type

[**ExportResponse**](ExportResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)


## GenerateHandoffContextV1HandoffPost

> map[string]interface{} GenerateHandoffContextV1HandoffPost(ctx).Authorization(authorization).Execute()

Generate Handoff Context



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
	resp, r, err := apiClient.GovernanceAPI.GenerateHandoffContextV1HandoffPost(context.Background()).Authorization(authorization).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `GovernanceAPI.GenerateHandoffContextV1HandoffPost``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `GenerateHandoffContextV1HandoffPost`: map[string]interface{}
	fmt.Fprintf(os.Stdout, "Response from `GovernanceAPI.GenerateHandoffContextV1HandoffPost`: %v\n", resp)
}
```

### Path Parameters



### Other Parameters

Other parameters are passed through a pointer to a apiGenerateHandoffContextV1HandoffPostRequest struct via the builder pattern


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


## GetSystemStatusV1StatusGet

> StatusResponse GetSystemStatusV1StatusGet(ctx).Authorization(authorization).Execute()

Get System Status



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
	resp, r, err := apiClient.GovernanceAPI.GetSystemStatusV1StatusGet(context.Background()).Authorization(authorization).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `GovernanceAPI.GetSystemStatusV1StatusGet``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `GetSystemStatusV1StatusGet`: StatusResponse
	fmt.Fprintf(os.Stdout, "Response from `GovernanceAPI.GetSystemStatusV1StatusGet`: %v\n", resp)
}
```

### Path Parameters



### Other Parameters

Other parameters are passed through a pointer to a apiGetSystemStatusV1StatusGetRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **authorization** | **string** | Bearer &lt;api-key&gt; | 

### Return type

[**StatusResponse**](StatusResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)


## ListApiKeysV1AdminKeysGet

> []ApiKeyListItem ListApiKeysV1AdminKeysGet(ctx).Authorization(authorization).Execute()

List Api Keys



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
	resp, r, err := apiClient.GovernanceAPI.ListApiKeysV1AdminKeysGet(context.Background()).Authorization(authorization).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `GovernanceAPI.ListApiKeysV1AdminKeysGet``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `ListApiKeysV1AdminKeysGet`: []ApiKeyListItem
	fmt.Fprintf(os.Stdout, "Response from `GovernanceAPI.ListApiKeysV1AdminKeysGet`: %v\n", resp)
}
```

### Path Parameters



### Other Parameters

Other parameters are passed through a pointer to a apiListApiKeysV1AdminKeysGetRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **authorization** | **string** | Bearer &lt;api-key&gt; | 

### Return type

[**[]ApiKeyListItem**](ApiKeyListItem.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)

